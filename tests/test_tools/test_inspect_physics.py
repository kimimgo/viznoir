"""Tests for inspect_physics MCP tool."""

from __future__ import annotations

import json

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk


def _make_cavity_dataset(n: int = 15):
    """Create a 2D cavity-like dataset with velocity and pressure."""
    grid = vtk.vtkImageData()
    grid.SetDimensions(n + 1, n + 1, 2)
    grid.SetOrigin(0, 0, 0)
    grid.SetSpacing(1.0 / n, 1.0 / n, 1.0 / n)

    n_points = grid.GetNumberOfPoints()

    # Velocity field (vortex pattern)
    vel = np.zeros((n_points, 3), dtype=np.float64)
    for i in range(n_points):
        x, y, _ = grid.GetPoint(i)
        vel[i, 0] = np.sin(np.pi * x) * np.cos(np.pi * y)
        vel[i, 1] = -np.cos(np.pi * x) * np.sin(np.pi * y)
    vtk_vel = numpy_to_vtk(vel)
    vtk_vel.SetName("U")
    vtk_vel.SetNumberOfComponents(3)
    grid.GetPointData().AddArray(vtk_vel)

    # Pressure field
    pressure = np.zeros(n_points, dtype=np.float64)
    for i in range(n_points):
        x, y, _ = grid.GetPoint(i)
        pressure[i] = -(x * x + y * y)
    vtk_p = numpy_to_vtk(pressure)
    vtk_p.SetName("p")
    grid.GetPointData().AddArray(vtk_p)

    return grid


def _write_vti(dataset, path: str):
    """Write VTK ImageData to a .vti file."""
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetFileName(path)
    writer.SetInputData(dataset)
    writer.Write()


class TestInspectPhysicsImpl:
    async def test_returns_field_topologies(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath)
        assert "field_topologies" in result
        assert len(result["field_topologies"]) >= 2  # U and p

    async def test_field_topology_has_range(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath)
        topo = result["field_topologies"][0]
        assert "field_range" in topo
        assert "min" in topo["field_range"]
        assert "max" in topo["field_range"]

    async def test_case_context_without_case_dir(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath)
        assert "case_context" in result
        assert result["case_context"]["mesh_quality"]["cell_count"] > 0

    async def test_case_context_hint_without_case_dir(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath)
        assert result["case_context_hint"] is not None
        assert "case_dir" in result["case_context_hint"]

    async def test_case_context_with_case_dir(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        # Use the OpenFOAM fixture
        import os
        fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "cavity_case")
        if os.path.isdir(fixture_dir):
            result = await inspect_physics_impl(file_path=fpath, case_dir=fixture_dir)
            assert result["case_context_hint"] is None
            assert result["case_context"]["solver"] is not None

    async def test_extraction_time(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath)
        assert "extraction_time_ms" in result
        assert result["extraction_time_ms"] > 0

    async def test_field_filter(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath, fields=["p"])
        assert len(result["field_topologies"]) == 1
        assert result["field_topologies"][0]["field_name"] == "p"

    async def test_json_serializable(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert len(parsed["field_topologies"]) >= 2

    async def test_velocity_has_vortices(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset(n=25)
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath, fields=["U"])
        u_topo = result["field_topologies"][0]
        assert u_topo["field_name"] == "U"
        assert len(u_topo["vortices"]) >= 1

    async def test_pressure_has_no_vortices(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath, fields=["p"])
        p_topo = result["field_topologies"][0]
        assert p_topo["vortices"] == []

    async def test_centerline_profiles_present(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl

        ds = _make_cavity_dataset()
        fpath = str(tmp_path / "cavity.vti")
        _write_vti(ds, fpath)

        result = await inspect_physics_impl(file_path=fpath, fields=["U"], probe_lines=2)
        u_topo = result["field_topologies"][0]
        assert len(u_topo["centerline_profiles"]) >= 1
