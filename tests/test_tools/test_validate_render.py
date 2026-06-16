"""Tests for the validate_render tool — physics guard on a render spec.

Uses small in-memory VTK datasets written to temp .vti files (no GPU render),
so these run in CI.
"""

from __future__ import annotations

import numpy as np
import pytest
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from viznoir.engine.readers import read_dataset
from viznoir.errors import FieldNotFoundError
from viznoir.tools.validate_render import (
    _field_stats,
    build_guard_context,
    validate_render_impl,
)


def _make_vti(tmp_path) -> str:
    """A 5^3 ImageData with a signed 'pressure' scalar and a 'velocity' vector (|v|=5)."""
    n = 5
    npts = n * n * n
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, n)

    pressure = np.linspace(-50.0, 80.0, npts).astype(np.float64)
    parr = numpy_to_vtk(pressure, deep=True)
    parr.SetName("pressure")
    img.GetPointData().AddArray(parr)

    velocity = np.tile(np.array([3.0, 4.0, 0.0]), (npts, 1)).astype(np.float64)  # |v| = 5
    varr = numpy_to_vtk(velocity, deep=True)
    varr.SetNumberOfComponents(3)
    varr.SetName("velocity")
    img.GetPointData().AddArray(varr)

    path = tmp_path / "data.vti"
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(img)
    writer.Write()
    return str(path)


class TestFieldStats:
    def test_signed_scalar(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        fmin, fmax, is_mag, assoc = _field_stats(ds, "pressure")
        assert fmin == pytest.approx(-50.0)
        assert fmax == pytest.approx(80.0)
        assert is_mag is False
        assert assoc == "POINTS"

    def test_vector_reduced_to_magnitude(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        fmin, fmax, is_mag, _ = _field_stats(ds, "velocity")
        assert is_mag is True
        assert fmin == pytest.approx(5.0)
        assert fmax == pytest.approx(5.0)

    def test_missing_field_raises(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        with pytest.raises(FieldNotFoundError):
            _field_stats(ds, "does_not_exist")


class TestBuildGuardContext:
    def test_carries_field_stats_and_bounds(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        ctx = build_guard_context(ds, "pressure", colormap="viridis")
        assert ctx.field_min < 0.0 < ctx.field_max
        assert ctx.data_bounds is not None and len(ctx.data_bounds) == 6

    def test_isovalue_out_of_range_is_empty(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        ctx = build_guard_context(ds, "pressure", filter_type="contour", isovalue=1000.0)
        assert ctx.isosurface_cell_count == 0

    def test_isovalue_in_range_is_nonempty(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        ctx = build_guard_context(ds, "pressure", filter_type="contour", isovalue=0.0)
        assert ctx.isosurface_cell_count == 1

    def test_no_filter_leaves_iso_none(self, tmp_path):
        ds = read_dataset(_make_vti(tmp_path))
        ctx = build_guard_context(ds, "pressure")
        assert ctx.isosurface_cell_count is None


class TestValidateRenderImpl:
    async def test_bad_pressure_colormap_warns(self, tmp_path):
        res = await validate_render_impl(
            _make_vti(tmp_path), "pressure", colormap="viridis", scalar_range=[-50.0, 80.0]
        )
        assert res["verdict"] in ("warn", "fail")
        assert res["field"]["min"] == pytest.approx(-50.0)
        assert res["field"]["is_magnitude"] is False
        assert any(r["rule"] == "pressure_diverging_colormap" for r in res["results"])

    async def test_good_magnitude_config_passes(self, tmp_path):
        res = await validate_render_impl(_make_vti(tmp_path), "velocity", colormap="viridis", scalar_range=[0.0, 5.0])
        assert res["verdict"] == "pass"
        assert res["field"]["is_magnitude"] is True

    async def test_empty_isosurface_fails(self, tmp_path):
        res = await validate_render_impl(
            _make_vti(tmp_path),
            "pressure",
            colormap="coolwarm",
            scalar_range=[-80.0, 80.0],
            filter_type="contour",
            isovalue=9999.0,
        )
        assert res["verdict"] == "fail"
        assert "summary" in res and res["summary"].startswith("FAIL")

    async def test_result_shape(self, tmp_path):
        res = await validate_render_impl(_make_vti(tmp_path), "pressure", colormap="coolwarm")
        assert {"verdict", "results", "field", "summary"} <= set(res)
        assert {"name", "min", "max", "is_magnitude", "association"} <= set(res["field"])
