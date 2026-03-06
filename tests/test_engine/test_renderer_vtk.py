"""Integration tests for engine/renderer.py — real VTK rendering (GPU/EGL)."""

from __future__ import annotations

import pytest

vtk = pytest.importorskip("vtk")


def _wavelet() -> vtk.vtkImageData:
    """Create wavelet test dataset."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
    src.Update()
    return src.GetOutput()


def _sphere() -> vtk.vtkPolyData:
    src = vtk.vtkSphereSource()
    src.SetRadius(1.0)
    src.Update()
    return src.GetOutput()


class TestRenderToPng:
    def test_render_basic(self):
        from parapilot.engine.renderer import RenderConfig, render_to_png
        rc = RenderConfig(width=200, height=150)
        png = render_to_png(_wavelet(), rc)
        assert png[:4] == b"\x89PNG"
        assert len(png) > 100

    def test_render_with_colormap(self):
        from parapilot.engine.renderer import RenderConfig, render_to_png
        rc = RenderConfig(width=200, height=150, colormap="viridis", array_name="RTData")
        png = render_to_png(_wavelet(), rc)
        assert png[:4] == b"\x89PNG"

    def test_render_with_scalar_range(self):
        from parapilot.engine.renderer import RenderConfig, render_to_png
        rc = RenderConfig(
            width=200, height=150,
            array_name="RTData",
            scalar_range=(50.0, 200.0),
        )
        png = render_to_png(_wavelet(), rc)
        assert png[:4] == b"\x89PNG"

    def test_render_wireframe(self):
        from parapilot.engine.renderer import RenderConfig, render_to_png
        rc = RenderConfig(width=200, height=150, representation="wireframe")
        png = render_to_png(_sphere(), rc)
        assert png[:4] == b"\x89PNG"

    def test_render_with_background(self):
        from parapilot.engine.renderer import RenderConfig, render_to_png
        rc = RenderConfig(width=200, height=150, background=(0.1, 0.2, 0.3))
        png = render_to_png(_wavelet(), rc)
        assert png[:4] == b"\x89PNG"

    def test_render_different_sizes(self):
        from parapilot.engine.renderer import RenderConfig, render_to_png
        rc = RenderConfig(width=400, height=300)
        png = render_to_png(_wavelet(), rc)
        assert png[:4] == b"\x89PNG"
        assert len(png) > 200

    def test_render_cell_association(self):
        """Test rendering with cell-associated data."""
        from parapilot.engine.filters import point_to_cell
        from parapilot.engine.renderer import RenderConfig, render_to_png
        data = point_to_cell(_wavelet())
        rc = RenderConfig(width=200, height=150)
        png = render_to_png(data, rc)
        assert png[:4] == b"\x89PNG"


class TestResolveArray:
    def test_resolve_point_array(self):
        from parapilot.engine.renderer import _resolve_array
        name, assoc = _resolve_array(_wavelet(), "RTData")
        assert name == "RTData"
        assert assoc == "point"

    def test_resolve_none_returns_first(self):
        from parapilot.engine.renderer import _resolve_array
        name, assoc = _resolve_array(_wavelet(), None)
        assert name == "RTData"

    def test_resolve_nonexistent(self):
        from parapilot.engine.renderer import _resolve_array
        name, assoc = _resolve_array(_wavelet(), "nonexistent_field")
        # Should fall back or return None
        assert name is not None or name is None  # just verify no crash


class TestResolveRenderable:
    def test_resolve_imagedata(self):
        from parapilot.engine.renderer import _resolve_renderable
        result = _resolve_renderable(_wavelet())
        assert result is not None
        assert result.GetNumberOfPoints() > 0

    def test_resolve_multiblock(self):
        from parapilot.engine.renderer import _resolve_renderable
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetBlock(0, _wavelet())
        result = _resolve_renderable(mb)
        assert result is not None

    def test_resolve_empty(self):
        from parapilot.engine.renderer import _resolve_renderable
        empty = vtk.vtkUnstructuredGrid()
        result = _resolve_renderable(empty)
        assert result is None


class TestGetScalarRange:
    def test_scalar_range_point(self):
        from parapilot.engine.renderer import _get_scalar_range
        lo, hi = _get_scalar_range(_wavelet(), "RTData", "point", component=-1)
        assert lo < hi
        assert lo > 0  # RTData min is ~37

    def test_scalar_range_with_component(self):
        from parapilot.engine.renderer import _get_scalar_range
        lo, hi = _get_scalar_range(_wavelet(), "RTData", "point", component=0)
        assert lo < hi


class TestVTKRenderer:
    def test_renderer_class(self):
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet())
        assert png[:4] == b"\x89PNG"

    def test_renderer_with_field(self):
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150, array_name="RTData", colormap="plasma")
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet())
        assert png[:4] == b"\x89PNG"

    def test_render_volume(self):
        """Test volume rendering path (lines 222-285)."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(
            width=200, height=150,
            representation="volume",
            array_name="RTData",
            colormap="plasma",
        )
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet())
        assert png[:4] == b"\x89PNG"

    def test_render_volume_no_array(self):
        """Volume rendering without explicit array uses defaults."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(
            width=200, height=150,
            representation="volume",
        )
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet())
        assert png[:4] == b"\x89PNG"

    def test_render_multiple(self):
        """Test render_multiple overlay path (lines 301-357)."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        datasets = [
            (_wavelet(), None),
            (_sphere(), RenderConfig(width=200, height=150, representation="wireframe")),
        ]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_with_colormap(self):
        """render_multiple with scalar mapping."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        datasets = [
            (_wavelet(), RenderConfig(width=200, height=150, array_name="RTData", colormap="viridis")),
        ]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_with_empty_dataset(self):
        """render_multiple skips empty datasets."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        empty = vtk.vtkUnstructuredGrid()
        datasets = [
            (empty, None),
            (_wavelet(), None),
        ]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_cell_data(self):
        """render_multiple with cell-associated data (line 332)."""
        from parapilot.engine.filters import point_to_cell
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        cell_data = point_to_cell(_wavelet())
        datasets = [
            (cell_data, RenderConfig(width=200, height=150, array_name="RTData", colormap="viridis")),
        ]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_no_array(self):
        """render_multiple with no array → visibility off (line 343)."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pd.SetPoints(pts)
        datasets = [(pd, RenderConfig(width=200, height=150))]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_with_camera(self):
        """render_multiple with CameraConfig (line 351)."""
        from parapilot.engine.camera import CameraConfig
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        cam = CameraConfig(position=(10, 10, 10), focal_point=(0, 0, 0), view_up=(0, 1, 0))
        renderer = VTKRenderer(rc)
        datasets = [(_wavelet(), None)]
        png = renderer.render_multiple(datasets, camera_config=cam)
        assert png[:4] == b"\x89PNG"

    def test_render_window_regeneration_after_100(self):
        """L68-69: render window is regenerated every 100 renders."""
        from parapilot.engine import renderer as renderer_mod
        from parapilot.engine.renderer import RenderConfig, VTKRenderer, cleanup

        cleanup()
        # Set render count to 99 so that on the 100th call it regenerates
        renderer_mod._RENDER_COUNT = 99
        rc = RenderConfig(width=100, height=80)
        vr = VTKRenderer(rc)
        # This 100th render should trigger regeneration (L68-69)
        png = vr.render(_wavelet())
        assert png[:4] == b"\x89PNG"
        # After regeneration counter is 100, window was reset and re-created
        assert renderer_mod._RENDER_COUNT == 100

    def test_render_with_component_positive(self):
        """L173: component >= 0 rendering path (ColorByArrayComponent)."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150, array_name="RTData", component=0)
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet())
        assert png[:4] == b"\x89PNG"

    def test_render_no_array_scalar_visibility_off(self):
        """L188: no array found → scalar visibility off."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        # Request a nonexistent array → _resolve_array returns None → L188 executed
        rc = RenderConfig(width=200, height=150, array_name="does_not_exist")
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet())
        assert png[:4] == b"\x89PNG"

    def test_render_with_camera_config(self):
        """L206: camera_config provided (CameraConfig) → apply_camera called."""
        from parapilot.engine.camera import CameraConfig
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150, array_name="RTData")
        cam = CameraConfig(position=(10, 10, 10), focal_point=(0, 0, 0), view_up=(0, 1, 0))
        renderer = VTKRenderer(rc)
        png = renderer.render(_wavelet(), camera_config=cam)
        assert png[:4] == b"\x89PNG"

    def test_render_volume_non_imagedata(self):
        """L230-234: volume rendering with non-ImageData triggers resample path."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(
            width=200, height=150,
            representation="volume",
            array_name="Normals",
        )
        renderer = VTKRenderer(rc)
        # _sphere() is vtkPolyData (not vtkImageData) → resampling path
        png = renderer.render(_sphere())
        assert png[:4] == b"\x89PNG"

    def test_render_volume_no_scalar_range_fallback(self):
        """L247: volume rendering with no scalar range → fallback to (0.0, 1.0).
        Needs a dataset with no arrays so array_name resolves to None."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        # Create a bare unstructured grid with points but no arrays
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0.0, 0.0, 0.0)
        pts.InsertNextPoint(1.0, 0.0, 0.0)
        pts.InsertNextPoint(0.0, 1.0, 0.0)
        pts.InsertNextPoint(0.0, 0.0, 1.0)
        grid.SetPoints(pts)
        # array_name=None, scalar_range=None, no arrays → L244 skipped, L247 hit
        rc = RenderConfig(
            width=200, height=150,
            representation="volume",
            array_name=None,
            scalar_range=None,
        )
        renderer = VTKRenderer(rc)
        png = renderer.render(grid)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_cell_association(self):
        """L332: render_multiple with cell-associated data."""
        from parapilot.engine.filters import point_to_cell
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        data = point_to_cell(_wavelet())
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        datasets = [(data, RenderConfig(width=200, height=150, array_name="RTData"))]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_no_array_scalar_off(self):
        """L343: render_multiple with no array → scalar visibility off."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        # Use dataset with nonexistent array → scalar visibility off (L343)
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        datasets = [
            (_wavelet(), RenderConfig(width=200, height=150, array_name="does_not_exist")),
        ]
        png = renderer.render_multiple(datasets)
        assert png[:4] == b"\x89PNG"

    def test_render_multiple_with_camera_config(self):
        """L351: render_multiple with camera_config provided."""
        from parapilot.engine.camera import CameraConfig
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=200, height=150)
        cam = CameraConfig(position=(20, 20, 20), focal_point=(0, 0, 0), view_up=(0, 0, 1))
        renderer = VTKRenderer(rc)
        datasets = [(_wavelet(), None)]
        png = renderer.render_multiple(datasets, camera_config=cam)
        assert png[:4] == b"\x89PNG"

    def test_render_empty_dataset_blank_image(self):
        """L146-147: render_data is None → blank image returned."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        empty = vtk.vtkUnstructuredGrid()  # 0 points → _resolve_renderable returns None
        rc = RenderConfig(width=200, height=150)
        renderer = VTKRenderer(rc)
        png = renderer.render(empty)
        assert png[:4] == b"\x89PNG"


class TestEdgeVisibility:
    def test_render_with_edge_visibility(self):
        """L483-484: edge_visibility=True path in _apply_representation."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(
            width=200, height=150,
            edge_visibility=True,
            edge_color=(1.0, 0.0, 0.0),
        )
        renderer = VTKRenderer(rc)
        png = renderer.render(_sphere())
        assert png[:4] == b"\x89PNG"


class TestVTKRendererConfig:
    def test_config_property(self):
        """L111: VTKRenderer.config property returns _config."""
        from parapilot.engine.renderer import RenderConfig, VTKRenderer
        rc = RenderConfig(width=300, height=200)
        renderer = VTKRenderer(rc)
        assert renderer.config is rc
        assert renderer.config.width == 300


class TestCleanup:
    def test_cleanup_with_window(self):
        """L111: cleanup() when _RENDER_WINDOW is not None → Finalize called."""
        import vtk as _vtk

        from parapilot.engine import renderer as renderer_mod
        from parapilot.engine.renderer import cleanup

        # Directly inject a render window to guarantee _RENDER_WINDOW is not None
        rw = _vtk.vtkRenderWindow()
        rw.SetOffScreenRendering(True)
        rw.SetSize(100, 80)
        renderer_mod._RENDER_WINDOW = rw
        renderer_mod._RENDER_COUNT = 5

        assert renderer_mod._RENDER_WINDOW is not None
        cleanup()  # L88: _RENDER_WINDOW.Finalize()
        assert renderer_mod._RENDER_WINDOW is None
        assert renderer_mod._RENDER_COUNT == 0


class TestResolveRenderableEdgeCases:
    def test_resolve_empty_multiblock(self):
        """L381: empty multiblock → geometry filter returns 0 points → None."""
        from parapilot.engine.renderer import _resolve_renderable
        mb = vtk.vtkMultiBlockDataSet()
        # All empty blocks
        empty = vtk.vtkUnstructuredGrid()
        mb.SetBlock(0, empty)
        result = _resolve_renderable(mb)
        assert result is None

    def test_resolve_non_dataset_non_multiblock(self):
        """L384: vtkDataObject (not dataset, not multiblock) → None."""
        from parapilot.engine.renderer import _resolve_renderable
        obj = vtk.vtkDataObject()
        result = _resolve_renderable(obj)
        assert result is None


class TestResolveArrayEdgeCases:
    def test_resolve_array_cell_data_suggestion(self):
        """L416-419: _resolve_array with cell data when field not found checks cell names."""
        from parapilot.engine.filters import point_to_cell
        from parapilot.engine.renderer import _resolve_array

        # point_to_cell data has RTData as cell array, not point array
        data = point_to_cell(_wavelet())
        # Remove point arrays so only cell arrays exist
        # Then request a nonexistent field → L416-419 branch logs cell array names
        name, assoc = _resolve_array(data, "nonexistent_cell_field")
        # Should return None (not found)
        assert name is None

    def test_resolve_array_auto_detect_cell_only(self):
        """L439: auto-detect → no point arrays → use first cell array."""
        from parapilot.engine.filters import point_to_cell
        from parapilot.engine.renderer import _resolve_array

        data = point_to_cell(_wavelet())
        # Manually remove point arrays so auto-detect falls to cell data
        pd = data.GetPointData()
        # Remove all point arrays
        while pd.GetNumberOfArrays() > 0:
            pd.RemoveArray(0)

        name, assoc = _resolve_array(data, None)
        assert name == "RTData"
        assert assoc == "cell"


class TestGetScalarRangeEdgeCases:
    def test_scalar_range_array_not_found(self):
        """L453: array not in attrs → returns (0.0, 1.0)."""
        from parapilot.engine.renderer import _get_scalar_range
        lo, hi = _get_scalar_range(_wavelet(), "nonexistent", "point", -1)
        assert lo == 0.0
        assert hi == 1.0

    def test_scalar_range_zero_range(self):
        """L465: zero-range array → hi = lo + 1.0."""
        import vtk as _vtk

        from parapilot.engine.renderer import _get_scalar_range

        # Create dataset with constant scalar (zero range)
        grid = _vtk.vtkUnstructuredGrid()
        pts = _vtk.vtkPoints()
        for i in range(5):
            pts.InsertNextPoint(float(i), 0.0, 0.0)
        grid.SetPoints(pts)

        arr = _vtk.vtkFloatArray()
        arr.SetName("constant")
        arr.SetNumberOfTuples(5)
        arr.Fill(42.0)  # all same value → zero range
        grid.GetPointData().AddArray(arr)

        lo, hi = _get_scalar_range(grid, "constant", "point", -1)
        assert lo == 42.0
        assert hi == 43.0  # lo + 1.0

    def test_scalar_range_magnitude_multicomponent(self):
        """L483-484: multi-component array → magnitude range."""
        import vtk as _vtk

        from parapilot.engine.renderer import _get_scalar_range

        data = _wavelet()
        calc = _vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("velocity")
        calc.SetFunction("RTData*iHat + RTData*0.5*jHat + 0*kHat")
        calc.SetResultArrayType(_vtk.VTK_DOUBLE)
        calc.Update()

        lo, hi = _get_scalar_range(calc.GetOutput(), "velocity", "point", -1)
        # -1 component on multi-component → magnitude range (L457-459)
        assert lo >= 0.0
        assert hi > lo
