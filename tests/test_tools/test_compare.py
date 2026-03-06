"""Tests for the compare tool — side-by-side and diff comparison."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import vtk

from parapilot.tools.compare import _compose_side_by_side

_skip_rendering = pytest.mark.skipif(
    bool(os.environ.get("CI")),
    reason="VTK offscreen rendering requires GPU (not available in CI)",
)


def _write_test_vtk(path: Path, radius: float = 1.0) -> None:
    """Write a simple sphere VTK file."""
    src = vtk.vtkSphereSource()
    src.SetRadius(radius)
    src.SetThetaResolution(16)
    src.SetPhiResolution(16)
    src.Update()

    # Add elevation scalar
    elev = vtk.vtkElevationFilter()
    elev.SetInputData(src.GetOutput())
    elev.SetLowPoint(0, 0, -radius)
    elev.SetHighPoint(0, 0, radius)
    elev.Update()

    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(elev.GetOutput())
    writer.Write()


@_skip_rendering
class TestComposeSideBySide:
    def test_produces_png(self):
        """Test that side-by-side composition produces valid PNG."""
        # Generate two simple PNG images using VTK
        src = vtk.vtkSphereSource()
        src.Update()

        from parapilot.engine.renderer import RenderConfig, render_to_png

        config = RenderConfig(width=200, height=150)
        png_a = render_to_png(src.GetOutput(), config)
        png_b = render_to_png(src.GetOutput(), config)

        result = _compose_side_by_side(png_a, png_b, "Case A", "Case B", 200, 150)
        assert result[:4] == b"\x89PNG"
        assert len(result) > 1000

    def test_labels_in_output(self):
        """Test that labels don't crash the composition."""
        src = vtk.vtkSphereSource()
        src.Update()

        from parapilot.engine.renderer import RenderConfig, render_to_png

        config = RenderConfig(width=100, height=75)
        png = render_to_png(src.GetOutput(), config)

        result = _compose_side_by_side(png, png, "Coarse Mesh", "Fine Mesh", 100, 75)
        assert result[:4] == b"\x89PNG"


@pytest.fixture
def two_test_files(tmp_path):
    """Create two test VTK files for comparison."""
    file_a = tmp_path / "sphere_a.vtp"
    file_b = tmp_path / "sphere_b.vtp"
    _write_test_vtk(file_a, radius=1.0)
    _write_test_vtk(file_b, radius=1.5)
    return str(file_a), str(file_b)


@_skip_rendering
class TestCompareImpl:
    def test_side_by_side_sync(self, two_test_files):
        """Integration test: compare two files side by side (sync path)."""
        from parapilot.engine.readers import read_dataset
        from parapilot.engine.renderer import RenderConfig, render_to_png

        file_a, file_b = two_test_files
        data_a = read_dataset(file_a)
        data_b = read_dataset(file_b)

        config = RenderConfig(width=200, height=150, array_name="Elevation")
        png_a = render_to_png(data_a, config)
        png_b = render_to_png(data_b, config)

        result = _compose_side_by_side(png_a, png_b, "r=1.0", "r=1.5", 200, 150)
        assert result[:4] == b"\x89PNG"
        assert len(result) > 1000
