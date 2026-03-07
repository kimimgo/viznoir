"""Integration tests for engine/renderer_cine.py — real VTK cinematic rendering."""

from __future__ import annotations

import pytest

vtk = pytest.importorskip("vtk")


def _wavelet() -> vtk.vtkImageData:
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
    src.Update()
    return src.GetOutput()


def _sphere() -> vtk.vtkPolyData:
    src = vtk.vtkSphereSource()
    src.SetRadius(1.0)
    src.Update()
    return src.GetOutput()


class TestCinematicRender:
    def test_basic(self):
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render
        rc = RenderConfig(width=200, height=150, array_name="RTData")
        config = CinematicConfig(render=rc, quality="draft")
        png = cinematic_render(_wavelet(), config)
        assert png[:4] == b"\x89PNG"

    def test_cell_association(self):
        """Cinematic render with cell-associated scalars (line 177)."""
        from viznoir.engine.filters import point_to_cell
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render
        data = point_to_cell(_wavelet())
        # RTData is now in cell data
        rc = RenderConfig(width=200, height=150)
        config = CinematicConfig(render=rc, quality="draft")
        png = cinematic_render(data, config)
        assert png[:4] == b"\x89PNG"

    def test_no_scalar_visibility(self):
        """Cinematic render with no array (line 192)."""
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render
        # Create polydata with points but NO arrays at all
        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(1, 0, 0)
        pts.InsertNextPoint(0, 1, 0)
        pd.SetPoints(pts)
        rc = RenderConfig(width=200, height=150)
        config = CinematicConfig(render=rc, quality="draft")
        png = cinematic_render(pd, config)
        assert png[:4] == b"\x89PNG"

    def test_empty_dataset(self):
        """Cinematic render with empty data (lines 156-157)."""
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render
        empty = vtk.vtkUnstructuredGrid()
        rc = RenderConfig(width=200, height=150)
        config = CinematicConfig(render=rc, quality="draft")
        png = cinematic_render(empty, config)
        assert png[:4] == b"\x89PNG"

    def test_with_component(self):
        """Cinematic render with component >= 0 (line 183)."""
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render
        rc = RenderConfig(width=200, height=150, array_name="RTData", component=0)
        config = CinematicConfig(render=rc, quality="draft")
        png = cinematic_render(_wavelet(), config)
        assert png[:4] == b"\x89PNG"

    def test_volume_representation(self):
        """Cinematic render with volume representation (lines 163-165)."""
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render
        rc = RenderConfig(
            width=200, height=150,
            representation="volume",
            array_name="RTData",
        )
        config = CinematicConfig(render=rc, quality="draft")
        png = cinematic_render(_wavelet(), config)
        assert png[:4] == b"\x89PNG"
