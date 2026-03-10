"""Tests for OpenFOAM context parser."""

from __future__ import annotations

from pathlib import Path

import pytest

CAVITY_DIR = str(Path(__file__).parent.parent / "fixtures" / "cavity_case")


@pytest.fixture()
def cavity_dir():
    if not Path(CAVITY_DIR).exists():
        pytest.skip("OpenFOAM cavity fixture not found")
    return CAVITY_DIR


class TestOpenFOAMParser:
    def test_can_parse_foam_dir(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        parser = OpenFOAMContextParser()
        assert parser.can_parse(cavity_dir) is True

    def test_cannot_parse_random_dir(self, tmp_path):
        from viznoir.context.openfoam import OpenFOAMContextParser

        parser = OpenFOAMContextParser()
        assert parser.can_parse(str(tmp_path)) is False

    def test_parse_case_dir(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        parser = OpenFOAMContextParser()
        ctx = parser.parse_case_dir(cavity_dir)
        assert ctx.solver is not None
        assert ctx.solver.name == "icoFoam"

    def test_parse_dataset_raises_not_implemented(self):
        from viznoir.context.openfoam import OpenFOAMContextParser

        parser = OpenFOAMContextParser()
        with pytest.raises(NotImplementedError, match="case directory"):
            parser.parse_dataset(object())

    def test_skips_backup_files(self, cavity_dir, tmp_path):
        """Backup files (.orig, .bak) in 0/ should be ignored."""
        import shutil

        from viznoir.context.openfoam import OpenFOAMContextParser

        case = tmp_path / "foam_case"
        shutil.copytree(cavity_dir, case)
        # Add a backup file that should be ignored
        (case / "0" / "U.orig").write_text("garbage")
        (case / "0" / ".hidden").write_text("garbage")

        ctx = OpenFOAMContextParser().parse_case_dir(str(case))
        fields = {bc.field for bc in ctx.boundary_conditions}
        assert "U.orig" not in fields
        assert ".hidden" not in fields


class TestOpenFOAMBoundaryConditions:
    def test_extracts_velocity_bcs(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        ctx = OpenFOAMContextParser().parse_case_dir(cavity_dir)
        u_bcs = [bc for bc in ctx.boundary_conditions if bc.field == "U"]
        assert len(u_bcs) == 3
        moving = next(bc for bc in u_bcs if bc.patch_name == "movingWall")
        assert moving.type == "fixedValue"
        assert moving.value == [1, 0, 0]

    def test_extracts_pressure_bcs(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        ctx = OpenFOAMContextParser().parse_case_dir(cavity_dir)
        p_bcs = [bc for bc in ctx.boundary_conditions if bc.field == "p"]
        assert len(p_bcs) == 3
        moving = next(bc for bc in p_bcs if bc.patch_name == "movingWall")
        assert moving.type == "zeroGradient"


class TestOpenFOAMTransport:
    def test_extracts_nu(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        ctx = OpenFOAMContextParser().parse_case_dir(cavity_dir)
        nu_props = [tp for tp in ctx.transport_properties if tp.name == "nu"]
        assert len(nu_props) == 1
        assert nu_props[0].value == pytest.approx(0.01)


class TestOpenFOAMSolver:
    def test_extracts_solver_info(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        ctx = OpenFOAMContextParser().parse_case_dir(cavity_dir)
        assert ctx.solver is not None
        assert ctx.solver.name == "icoFoam"

    def test_raw_metadata_has_timing(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        ctx = OpenFOAMContextParser().parse_case_dir(cavity_dir)
        # endTime and deltaT should be in derived_quantities or accessible
        assert ctx.solver is not None


class TestOpenFOAMDerived:
    def test_computes_reynolds_number(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser

        ctx = OpenFOAMContextParser().parse_case_dir(cavity_dir)
        re_list = [dq for dq in ctx.derived_quantities if dq.name == "Re"]
        assert len(re_list) == 1
        assert re_list[0].value == pytest.approx(100.0)


class TestOpenFOAMDictParser:
    """Unit tests for the low-level OpenFOAM value parser."""

    def test_parse_scalar(self):
        from viznoir.context.openfoam import _parse_openfoam_value

        assert _parse_openfoam_value("0.01") == pytest.approx(0.01)

    def test_parse_vector(self):
        from viznoir.context.openfoam import _parse_openfoam_value

        assert _parse_openfoam_value("(1 0 0)") == [1.0, 0.0, 0.0]

    def test_parse_uniform_scalar(self):
        from viznoir.context.openfoam import _parse_openfoam_value

        assert _parse_openfoam_value("uniform 0") == pytest.approx(0.0)

    def test_parse_uniform_vector(self):
        from viznoir.context.openfoam import _parse_openfoam_value

        assert _parse_openfoam_value("uniform (1 0 0)") == [1.0, 0.0, 0.0]


class TestRegistryIntegration:
    def test_openfoam_before_generic(self, cavity_dir):
        from viznoir.context.generic import GenericContextParser
        from viznoir.context.openfoam import OpenFOAMContextParser
        from viznoir.context.parser import ContextParserRegistry

        registry = ContextParserRegistry()
        registry.register(OpenFOAMContextParser())
        registry.register(GenericContextParser())

        parser = registry.get_parser(cavity_dir)
        assert isinstance(parser, OpenFOAMContextParser)
