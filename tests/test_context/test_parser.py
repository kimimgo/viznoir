"""Tests for ContextParser protocol, GenericParser, and Registry."""

from __future__ import annotations


def _make_vtk_dataset():
    """Create a minimal VTK dataset for testing."""
    import vtkmodules.vtkCommonCore as vtk_core  # noqa: N813
    import vtkmodules.vtkCommonDataModel as vtk_dm  # noqa: N813

    grid = vtk_dm.vtkImageData()
    grid.SetDimensions(11, 11, 2)
    grid.SetOrigin(0, 0, 0)
    grid.SetSpacing(0.01, 0.01, 0.00005)

    n_points = grid.GetNumberOfPoints()

    # Add a scalar field
    pressure = vtk_core.vtkFloatArray()
    pressure.SetName("p")
    pressure.SetNumberOfTuples(n_points)
    for i in range(n_points):
        pressure.SetValue(i, float(i) * 0.1)
    grid.GetPointData().AddArray(pressure)

    return grid


class TestGenericContextParser:
    def test_can_parse_any_dataset(self):
        from viznoir.context.generic import GenericContextParser

        parser = GenericContextParser()
        assert parser.can_parse("any/path.vtu") is True

    def test_parse_returns_mesh_quality(self):
        from viznoir.context.generic import GenericContextParser

        parser = GenericContextParser()
        ds = _make_vtk_dataset()
        ctx = parser.parse_dataset(ds)
        assert ctx.mesh_quality.cell_count == ds.GetNumberOfCells()
        assert ctx.mesh_quality.point_count == ds.GetNumberOfPoints()
        assert ctx.mesh_quality.dimensions == 2  # thin z

    def test_parse_has_empty_bc(self):
        from viznoir.context.generic import GenericContextParser

        parser = GenericContextParser()
        ds = _make_vtk_dataset()
        ctx = parser.parse_dataset(ds)
        assert ctx.boundary_conditions == []
        assert ctx.solver is None

    def test_parse_cell_types(self):
        from viznoir.context.generic import GenericContextParser

        parser = GenericContextParser()
        ds = _make_vtk_dataset()
        ctx = parser.parse_dataset(ds)
        total = sum(ctx.mesh_quality.cell_types.values())
        assert total == ctx.mesh_quality.cell_count

    def test_parse_bounding_box(self):
        from viznoir.context.generic import GenericContextParser

        parser = GenericContextParser()
        ds = _make_vtk_dataset()
        ctx = parser.parse_dataset(ds)
        bb = ctx.mesh_quality.bounding_box
        assert len(bb) == 2
        assert len(bb[0]) == 3
        assert bb[1][0] > bb[0][0]  # xmax > xmin


class TestContextParserRegistry:
    def test_register_and_get(self):
        from viznoir.context.generic import GenericContextParser
        from viznoir.context.parser import ContextParserRegistry

        registry = ContextParserRegistry()
        registry.register(GenericContextParser())
        parser = registry.get_parser("anything.vtu")
        assert parser is not None

    def test_generic_is_fallback(self):
        from viznoir.context.parser import get_default_registry

        registry = get_default_registry()
        parser = registry.get_parser("unknown_file.xyz")
        assert parser is not None  # GenericParser as fallback

    def test_priority_order(self):
        """First registered parser that matches wins."""
        from viznoir.context.generic import GenericContextParser
        from viznoir.context.parser import ContextParserRegistry

        class SpecialParser:
            def can_parse(self, path: str) -> bool:
                return path.endswith(".special")

            def parse_dataset(self, dataset: object):
                pass  # pragma: no cover

        registry = ContextParserRegistry()
        special = SpecialParser()
        registry.register(special)
        registry.register(GenericContextParser())

        assert registry.get_parser("file.special") is special
        assert registry.get_parser("file.vtu") is not special

    def test_no_match_returns_none(self):
        from viznoir.context.parser import ContextParserRegistry

        class NeverParser:
            def can_parse(self, path: str) -> bool:
                return False

            def parse_dataset(self, dataset: object):
                pass  # pragma: no cover

        registry = ContextParserRegistry()
        registry.register(NeverParser())
        assert registry.get_parser("anything") is None
