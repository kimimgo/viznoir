"""Tests for CGNS context parser."""

from __future__ import annotations

from pathlib import Path

import pytest

CGNS_FIXTURE = str(Path(__file__).parent.parent / "fixtures" / "cgns" / "multi.cgns")


def _make_vtk_unstructured_grid():
    """Create a minimal VTK unstructured grid (e.g., hexahedra) for testing."""
    import vtkmodules.vtkCommonCore as vtk_core  # noqa: N813
    import vtkmodules.vtkCommonDataModel as vtk_dm  # noqa: N813

    ugrid = vtk_dm.vtkUnstructuredGrid()

    # 8 points forming a unit cube
    points = vtk_core.vtkPoints()
    coords = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (1.0, 1.0, 1.0),
        (0.0, 1.0, 1.0),
    ]
    for c in coords:
        points.InsertNextPoint(*c)
    ugrid.SetPoints(points)

    # One hexahedron cell
    hex_cell = vtk_dm.vtkHexahedron()
    for i in range(8):
        hex_cell.GetPointIds().SetId(i, i)
    ugrid.InsertNextCell(hex_cell.GetCellType(), hex_cell.GetPointIds())

    return ugrid


def _make_vtk_multiblock():
    """Create a minimal VTK multi-block dataset with named blocks for testing."""
    import vtkmodules.vtkCommonDataModel as vtk_dm  # noqa: N813

    mb = vtk_dm.vtkMultiBlockDataSet()
    mb.SetNumberOfBlocks(2)

    block0 = _make_vtk_unstructured_grid()
    block1 = _make_vtk_unstructured_grid()

    mb.SetBlock(0, block0)
    mb.SetBlock(1, block1)
    mb.GetMetaData(0).Set(vtk_dm.vtkCompositeDataSet.NAME(), "Inlet")
    mb.GetMetaData(1).Set(vtk_dm.vtkCompositeDataSet.NAME(), "Outlet")

    return mb


class TestCGNSContextParserCanParse:
    """Tests for CGNSContextParser.can_parse()."""

    def test_cgns_extension_returns_true(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse("simulation.cgns") is True

    def test_cgns_extension_with_path_returns_true(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse("/data/results/multi.cgns") is True

    def test_uppercase_cgns_extension_returns_false(self):
        """Extension matching is case-sensitive per convention."""
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        # Lowercase only — consistent with how readers.py handles extensions
        assert parser.can_parse("simulation.CGNS") is False

    def test_non_cgns_extension_returns_false(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse("simulation.vtu") is False

    def test_hdf5_extension_returns_false(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse("data.hdf5") is False

    def test_empty_string_returns_false(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse("") is False

    def test_cgns_in_dirname_not_extension_returns_false(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse("/cgns/data/result.vtp") is False


class TestCGNSContextParserParseDataset:
    """Tests for CGNSContextParser.parse_dataset() with mock VTK datasets."""

    def test_parse_unstructured_grid_returns_context(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx is not None
        assert ctx.mesh_quality is not None

    def test_parse_unstructured_grid_cell_count(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx.mesh_quality.cell_count == ds.GetNumberOfCells()

    def test_parse_unstructured_grid_point_count(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx.mesh_quality.point_count == ds.GetNumberOfPoints()

    def test_parse_unstructured_grid_bounding_box(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        bb = ctx.mesh_quality.bounding_box
        assert len(bb) == 2
        assert len(bb[0]) == 3
        assert bb[1][0] > bb[0][0]  # xmax > xmin

    def test_parse_unstructured_grid_solver_info(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx.solver is not None
        assert ctx.solver.name == "CGNS"

    def test_parse_unstructured_grid_has_no_transport_properties(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx.transport_properties == []

    def test_parse_unstructured_grid_has_no_derived_quantities(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx.derived_quantities == []

    def test_parse_unstructured_detects_unstructured_topology(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        assert ctx.solver is not None
        assert ctx.solver.algorithm == "unstructured"

    def test_parse_unstructured_grid_cell_types_populated(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        ds = _make_vtk_unstructured_grid()
        ctx = parser.parse_dataset(ds)
        total = sum(ctx.mesh_quality.cell_types.values())
        assert total == ctx.mesh_quality.cell_count

    def test_parse_multiblock_extracts_block_names_as_bcs(self):
        """Multi-block datasets: block names become BoundaryCondition entries."""
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        mb = _make_vtk_multiblock()
        ctx = parser.parse_dataset(mb)
        patch_names = {bc.patch_name for bc in ctx.boundary_conditions}
        assert "Inlet" in patch_names
        assert "Outlet" in patch_names

    def test_parse_multiblock_bc_field_is_block(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        mb = _make_vtk_multiblock()
        ctx = parser.parse_dataset(mb)
        for bc in ctx.boundary_conditions:
            assert bc.field == "block"

    def test_parse_multiblock_bc_type_is_zone(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        mb = _make_vtk_multiblock()
        ctx = parser.parse_dataset(mb)
        for bc in ctx.boundary_conditions:
            assert bc.type == "zone"

    def test_parse_multiblock_cell_count_is_sum_of_blocks(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        mb = _make_vtk_multiblock()
        ctx = parser.parse_dataset(mb)
        # Each block has 1 hex cell → 2 total
        assert ctx.mesh_quality.cell_count == 2

    def test_parse_structured_grid_detects_structured_topology(self):
        """vtkStructuredGrid should report 'structured' algorithm."""
        import vtkmodules.vtkCommonDataModel as vtk_dm  # noqa: N813

        from viznoir.context.cgns import CGNSContextParser

        sg = vtk_dm.vtkStructuredGrid()
        sg.SetDimensions(3, 3, 3)
        ctx = CGNSContextParser().parse_dataset(sg)
        assert ctx.solver is not None
        assert ctx.solver.algorithm == "structured"


class TestCGNSRegistryIntegration:
    """Tests for CGNS parser registration in the default registry."""

    def test_cgns_registered_before_generic(self):
        from viznoir.context.cgns import CGNSContextParser
        from viznoir.context.parser import get_default_registry

        registry = get_default_registry()
        parser = registry.get_parser("simulation.cgns")
        assert isinstance(parser, CGNSContextParser)

    def test_non_cgns_falls_back_to_other_parsers(self):
        from viznoir.context.cgns import CGNSContextParser
        from viznoir.context.parser import get_default_registry

        registry = get_default_registry()
        parser = registry.get_parser("simulation.vtu")
        assert not isinstance(parser, CGNSContextParser)

    def test_openfoam_still_takes_priority_over_cgns(self, tmp_path):
        """OpenFOAM case dirs must still be matched by OpenFOAMContextParser."""
        from viznoir.context.openfoam import OpenFOAMContextParser
        from viznoir.context.parser import get_default_registry

        # Create a fake OpenFOAM case structure
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("application icoFoam;")

        registry = get_default_registry()
        parser = registry.get_parser(str(tmp_path))
        assert isinstance(parser, OpenFOAMContextParser)


class TestCGNSFixtureIntegration:
    """Integration test using the real CGNS fixture (skipped if VTK CGNS reader unavailable)."""

    @pytest.fixture(autouse=True)
    def require_cgns_fixture(self):
        if not Path(CGNS_FIXTURE).exists():
            pytest.skip("CGNS fixture not found")

    def test_fixture_file_exists(self):
        assert Path(CGNS_FIXTURE).exists()

    def test_can_parse_fixture(self):
        from viznoir.context.cgns import CGNSContextParser

        parser = CGNSContextParser()
        assert parser.can_parse(CGNS_FIXTURE) is True
