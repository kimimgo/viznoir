"""Tests for L3 CaseContext data models."""
from __future__ import annotations


class TestBoundaryCondition:
    def test_create_fixed_value(self):
        from viznoir.context.models import BoundaryCondition
        bc = BoundaryCondition(
            patch_name="movingWall", field="U",
            type="fixedValue", value=[1, 0, 0],
        )
        assert bc.patch_name == "movingWall"
        assert bc.value == [1, 0, 0]

    def test_create_noslip(self):
        from viznoir.context.models import BoundaryCondition
        bc = BoundaryCondition(
            patch_name="fixedWalls", field="U",
            type="noSlip", value=None,
        )
        assert bc.value is None


class TestTransportProperty:
    def test_create_with_unit(self):
        from viznoir.context.models import TransportProperty
        tp = TransportProperty(name="nu", value=1e-6, unit="m^2/s")
        assert tp.name == "nu"
        assert tp.value == 1e-6
        assert tp.unit == "m^2/s"

    def test_create_without_unit(self):
        from viznoir.context.models import TransportProperty
        tp = TransportProperty(name="rho", value=1.225)
        assert tp.unit is None


class TestSolverInfo:
    def test_create(self):
        from viznoir.context.models import SolverInfo
        si = SolverInfo(
            name="icoFoam", algorithm="PISO",
            turbulence_model=None, steady=False,
        )
        assert si.name == "icoFoam"
        assert si.steady is False


class TestMeshQuality:
    def test_create(self):
        from viznoir.context.models import MeshQuality
        mq = MeshQuality(
            cell_count=400, point_count=441,
            cell_types={"quad": 400},
            bounding_box=[[0, 0, 0], [0.1, 0.1, 0.005]],
        )
        assert mq.cell_count == 400

    def test_dimensions_2d(self):
        from viznoir.context.models import MeshQuality
        mq = MeshQuality(
            cell_count=400, point_count=441,
            cell_types={"quad": 400},
            bounding_box=[[0, 0, 0], [0.1, 0.1, 0.0005]],
        )
        assert mq.dimensions == 2  # thin z-axis (ratio 0.005 < 0.01) → 2D

    def test_dimensions_3d(self):
        from viznoir.context.models import MeshQuality
        mq = MeshQuality(
            cell_count=1000, point_count=1331,
            cell_types={"hexahedron": 1000},
            bounding_box=[[0, 0, 0], [1, 1, 1]],
        )
        assert mq.dimensions == 3

    def test_dimensions_zero_extent(self):
        from viznoir.context.models import MeshQuality
        mq = MeshQuality(
            cell_count=1, point_count=2,
            cell_types={"vertex": 1},
            bounding_box=[[0, 0, 0], [0, 0, 0]],
        )
        assert mq.dimensions == 3  # degenerate case fallback


class TestDerivedQuantity:
    def test_create(self):
        from viznoir.context.models import DerivedQuantity
        dq = DerivedQuantity(
            name="Re", value=100.0,
            formula="U_ref * L_ref / nu",
            inputs={"U_ref": 1.0, "L_ref": 0.1, "nu": 1e-3},
        )
        assert dq.value == 100.0


class TestCaseContext:
    def test_create_minimal(self):
        from viznoir.context.models import CaseContext, MeshQuality
        cc = CaseContext(
            mesh_quality=MeshQuality(
                cell_count=100, point_count=121,
                cell_types={"quad": 100},
                bounding_box=[[0, 0, 0], [1, 1, 0.1]],
            ),
        )
        assert cc.mesh_quality.cell_count == 100
        assert cc.boundary_conditions == []

    def test_to_dict(self):
        from viznoir.context.models import CaseContext, MeshQuality
        cc = CaseContext(
            mesh_quality=MeshQuality(
                cell_count=100, point_count=121,
                cell_types={"quad": 100},
                bounding_box=[[0, 0, 0], [1, 1, 0.1]],
            ),
        )
        d = cc.to_dict()
        assert isinstance(d, dict)
        assert d["mesh_quality"]["cell_count"] == 100

    def test_to_dict_json_serializable(self):
        import json

        from viznoir.context.models import CaseContext, MeshQuality
        cc = CaseContext(
            mesh_quality=MeshQuality(
                cell_count=100, point_count=121,
                cell_types={"quad": 100},
                bounding_box=[[0, 0, 0], [1, 1, 0.1]],
            ),
        )
        json_str = json.dumps(cc.to_dict())
        assert "cell_count" in json_str

    def test_to_dict_with_all_fields(self):
        from viznoir.context.models import (
            BoundaryCondition,
            CaseContext,
            DerivedQuantity,
            MeshQuality,
            SolverInfo,
            TransportProperty,
        )
        cc = CaseContext(
            mesh_quality=MeshQuality(
                cell_count=400, point_count=441,
                cell_types={"quad": 400},
                bounding_box=[[0, 0, 0], [0.1, 0.1, 0.005]],
            ),
            boundary_conditions=[
                BoundaryCondition(
                    patch_name="movingWall", field="U",
                    type="fixedValue", value=[1, 0, 0],
                ),
            ],
            transport_properties=[
                TransportProperty(name="nu", value=1e-3, unit="m^2/s"),
            ],
            solver=SolverInfo(
                name="icoFoam", algorithm="PISO",
                turbulence_model=None, steady=False,
            ),
            derived_quantities=[
                DerivedQuantity(
                    name="Re", value=100.0,
                    formula="U_ref * L_ref / nu",
                    inputs={"U_ref": 1.0, "L_ref": 0.1, "nu": 1e-3},
                ),
            ],
        )
        d = cc.to_dict()
        assert len(d["boundary_conditions"]) == 1
        assert d["solver"]["name"] == "icoFoam"
        assert d["derived_quantities"][0]["name"] == "Re"
