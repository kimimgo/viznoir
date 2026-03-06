"""Tests for engine/renderer.py internal helpers and rendering pipeline."""

from __future__ import annotations

import vtk

from parapilot.engine.renderer import (
    RenderConfig,
    VTKRenderer,
    _apply_representation,
    _build_scalar_bar,
    _get_scalar_range,
    _resolve_array,
    _resolve_renderable,
    cleanup,
    render_to_png,
)


def _make_grid_with_data():
    """Create a simple unstructured grid with point and cell data."""
    grid = vtk.vtkUnstructuredGrid()
    pts = vtk.vtkPoints()
    pts.InsertNextPoint(0, 0, 0)
    pts.InsertNextPoint(1, 0, 0)
    pts.InsertNextPoint(0, 1, 0)
    pts.InsertNextPoint(0, 0, 1)
    grid.SetPoints(pts)

    cell = vtk.vtkTetra()
    for i in range(4):
        cell.GetPointIds().SetId(i, i)
    grid.InsertNextCell(cell.GetCellType(), cell.GetPointIds())

    # Point array
    pressure = vtk.vtkFloatArray()
    pressure.SetName("pressure")
    pressure.SetNumberOfTuples(4)
    for i in range(4):
        pressure.SetValue(i, float(i) * 10.0)
    grid.GetPointData().AddArray(pressure)

    # Cell array
    region = vtk.vtkIntArray()
    region.SetName("region")
    region.SetNumberOfTuples(1)
    region.SetValue(0, 5)
    grid.GetCellData().AddArray(region)

    return grid


class TestResolveRenderable:
    def test_regular_dataset(self):
        grid = _make_grid_with_data()
        result = _resolve_renderable(grid)
        assert result is not None
        assert result.GetNumberOfPoints() == 4

    def test_empty_dataset_returns_none(self):
        grid = vtk.vtkUnstructuredGrid()
        result = _resolve_renderable(grid)
        assert result is None

    def test_multiblock(self):
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetNumberOfBlocks(1)
        grid = _make_grid_with_data()
        mb.SetBlock(0, grid)
        result = _resolve_renderable(mb)
        assert result is not None
        assert result.GetNumberOfPoints() > 0

    def test_empty_multiblock_returns_none(self):
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetNumberOfBlocks(0)
        result = _resolve_renderable(mb)
        assert result is None

    def test_unsupported_type(self):
        table = vtk.vtkTable()
        result = _resolve_renderable(table)
        assert result is None


class TestResolveArray:
    def test_find_point_array(self):
        grid = _make_grid_with_data()
        name, assoc = _resolve_array(grid, "pressure")
        assert name == "pressure"
        assert assoc == "point"

    def test_find_cell_array(self):
        grid = _make_grid_with_data()
        name, assoc = _resolve_array(grid, "region")
        assert name == "region"
        assert assoc == "cell"

    def test_not_found_returns_none(self):
        grid = _make_grid_with_data()
        name, assoc = _resolve_array(grid, "nonexistent")
        assert name is None

    def test_auto_detect_first_point_array(self):
        grid = _make_grid_with_data()
        name, assoc = _resolve_array(grid, None)
        assert name == "pressure"
        assert assoc == "point"

    def test_auto_detect_no_arrays(self):
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        grid.SetPoints(pts)
        name, assoc = _resolve_array(grid, None)
        assert name is None


class TestGetScalarRange:
    def test_point_array_range(self):
        grid = _make_grid_with_data()
        lo, hi = _get_scalar_range(grid, "pressure", "point", -1)
        assert lo == 0.0
        assert hi == 30.0

    def test_cell_array_range(self):
        grid = _make_grid_with_data()
        lo, hi = _get_scalar_range(grid, "region", "cell", -1)
        assert lo == 5.0
        # Single value → hi adjusted to avoid zero-range
        assert hi >= 5.0

    def test_missing_array_returns_default(self):
        grid = _make_grid_with_data()
        lo, hi = _get_scalar_range(grid, "missing", "point", -1)
        assert lo == 0.0
        assert hi == 1.0


class TestApplyRepresentation:
    def test_surface(self):
        prop = vtk.vtkProperty()
        config = RenderConfig(representation="surface")
        _apply_representation(prop, config)
        assert prop.GetRepresentation() == 2

    def test_wireframe(self):
        prop = vtk.vtkProperty()
        config = RenderConfig(representation="wireframe")
        _apply_representation(prop, config)
        assert prop.GetRepresentation() == 1

    def test_points(self):
        prop = vtk.vtkProperty()
        config = RenderConfig(representation="points")
        _apply_representation(prop, config)
        assert prop.GetRepresentation() == 0

    def test_opacity(self):
        prop = vtk.vtkProperty()
        config = RenderConfig(opacity=0.5)
        _apply_representation(prop, config)
        assert prop.GetOpacity() == 0.5

    def test_edge_visibility(self):
        prop = vtk.vtkProperty()
        config = RenderConfig(edge_visibility=True, edge_color=(1, 0, 0))
        _apply_representation(prop, config)
        assert prop.GetEdgeVisibility() == 1


class TestBuildScalarBar:
    def test_creates_bar(self):
        mapper = vtk.vtkPolyDataMapper()
        lut = vtk.vtkLookupTable()
        mapper.SetLookupTable(lut)
        config = RenderConfig()
        bar = _build_scalar_bar(mapper, config, "pressure")
        assert bar is not None
        assert bar.GetTitle() == "pressure"

    def test_custom_title(self):
        mapper = vtk.vtkPolyDataMapper()
        lut = vtk.vtkLookupTable()
        mapper.SetLookupTable(lut)
        config = RenderConfig(scalar_bar_title="Custom Title")
        bar = _build_scalar_bar(mapper, config, "pressure")
        assert bar.GetTitle() == "Custom Title"


class TestRenderConfig:
    def test_defaults(self):
        config = RenderConfig()
        assert config.width == 1920
        assert config.height == 1080
        assert config.colormap == "cool to warm"
        assert config.show_scalar_bar is True
        assert config.representation == "surface"


class TestVTKRendererAndRenderToPng:
    def test_render_simple_data(self):
        grid = _make_grid_with_data()
        config = RenderConfig(width=200, height=150, array_name="pressure")
        png = render_to_png(grid, config)
        assert isinstance(png, bytes)
        assert len(png) > 100
        # PNG magic bytes
        assert png[:4] == b"\x89PNG"

    def test_render_no_field(self):
        grid = _make_grid_with_data()
        config = RenderConfig(width=200, height=150, array_name=None, show_scalar_bar=False)
        png = render_to_png(grid, config)
        assert png[:4] == b"\x89PNG"

    def test_render_empty_dataset(self):
        grid = vtk.vtkUnstructuredGrid()
        config = RenderConfig(width=100, height=100)
        png = render_to_png(grid, config)
        assert png[:4] == b"\x89PNG"

    def test_cleanup(self):
        # Should not raise
        cleanup()


class TestVTKRendererInstance:
    def test_config_property(self):
        config = RenderConfig(width=800)
        renderer = VTKRenderer(config)
        assert renderer.config.width == 800

    def test_default_config(self):
        renderer = VTKRenderer()
        assert renderer.config.width == 1920
