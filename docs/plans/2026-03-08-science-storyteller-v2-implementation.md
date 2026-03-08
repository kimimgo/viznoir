# Science Storyteller v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace broken `analyze_dataset()` with physics-aware `inspect_physics` pipeline — L2 FieldTopology (universal VTK) + L3 CaseContext (OpenFOAM, extensible).

**Architecture:** viznoir extracts structured quantitative data (vortex detection, critical points, line probes, BC, transport properties, mesh quality). LLM does the physics reasoning. New `context/` module with `ContextParser` protocol for solver extensibility. New `engine/topology.py` for universal VTK field topology analysis.

**Tech Stack:** VTK 9.4 (vtkGradientFilter, vtkProbeFilter, vtkConnectivityFilter), Python 3.10+ dataclasses, Pydantic for MCP tool schemas.

---

### Task 1: L3 CaseContext Data Models

**Files:**
- Create: `src/viznoir/context/__init__.py`
- Create: `src/viznoir/context/models.py`
- Test: `tests/test_context/test_models.py`

**Step 1: Write failing tests**

```python
# tests/test_context/__init__.py
# (empty)

# tests/test_context/test_models.py
"""Tests for context/models.py — CaseContext data models."""
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
        tp = TransportProperty(name="nu", value=0.01, unit="m^2/s")
        assert tp.value == 0.01

    def test_create_without_unit(self):
        from viznoir.context.models import TransportProperty
        tp = TransportProperty(name="rho", value=1.0, unit=None)
        assert tp.unit is None


class TestSolverInfo:
    def test_create_icofoam(self):
        from viznoir.context.models import SolverInfo
        si = SolverInfo(name="icoFoam", algorithm="PISO",
                        turbulence_model="laminar", steady=False)
        assert si.steady is False


class TestMeshQuality:
    def test_create(self):
        from viznoir.context.models import MeshQuality
        mq = MeshQuality(
            cell_count=40000, point_count=40401,
            cell_types={"hexahedron": 40000},
            bounding_box=([0, 0, 0], [1, 1, 0.1]),
            max_aspect_ratio=1.0,
            max_non_orthogonality=0.0,
            max_skewness=0.0,
        )
        assert mq.cell_count == 40000


class TestDerivedQuantity:
    def test_reynolds_number(self):
        from viznoir.context.models import DerivedQuantity
        dq = DerivedQuantity(
            name="Re", value=100.0, formula="U_ref * L_ref / nu",
            inputs={"U_ref": 1.0, "L_ref": 1.0, "nu": 0.01},
        )
        assert dq.value == 100.0


class TestCaseContext:
    def test_create_full(self):
        from viznoir.context.models import (
            BoundaryCondition, CaseContext, DerivedQuantity,
            MeshQuality, SolverInfo, TransportProperty,
        )
        ctx = CaseContext(
            solver=SolverInfo(name="icoFoam", algorithm="PISO",
                              turbulence_model="laminar", steady=False),
            boundary_conditions=[
                BoundaryCondition(patch_name="movingWall", field="U",
                                  type="fixedValue", value=[1, 0, 0]),
            ],
            transport_properties=[
                TransportProperty(name="nu", value=0.01, unit="m^2/s"),
            ],
            mesh_quality=MeshQuality(
                cell_count=400, point_count=441,
                cell_types={"hexahedron": 400},
                bounding_box=([0, 0, 0], [1, 1, 0.1]),
                max_aspect_ratio=None, max_non_orthogonality=None,
                max_skewness=None,
            ),
            derived_quantities=[
                DerivedQuantity(name="Re", value=100.0,
                                formula="U_ref * L_ref / nu",
                                inputs={"U_ref": 1.0, "L_ref": 1.0, "nu": 0.01}),
            ],
            dimensions=2,
            time_steps=[0.0, 0.5],
            raw_metadata={"endTime": 0.5},
        )
        assert ctx.dimensions == 2
        assert len(ctx.boundary_conditions) == 1

    def test_create_minimal(self):
        from viznoir.context.models import CaseContext, MeshQuality
        ctx = CaseContext(
            solver=None,
            boundary_conditions=[],
            transport_properties=[],
            mesh_quality=MeshQuality(
                cell_count=100, point_count=121,
                cell_types={"hexahedron": 100},
                bounding_box=([0, 0, 0], [1, 1, 1]),
                max_aspect_ratio=None, max_non_orthogonality=None,
                max_skewness=None,
            ),
            derived_quantities=[],
            dimensions=3,
            time_steps=None,
            raw_metadata={},
        )
        assert ctx.solver is None

    def test_to_dict(self):
        """CaseContext must be JSON-serializable for MCP transport."""
        import json
        from viznoir.context.models import CaseContext, MeshQuality
        ctx = CaseContext(
            solver=None, boundary_conditions=[], transport_properties=[],
            mesh_quality=MeshQuality(
                cell_count=100, point_count=121,
                cell_types={"hexahedron": 100},
                bounding_box=([0, 0, 0], [1, 1, 1]),
                max_aspect_ratio=None, max_non_orthogonality=None,
                max_skewness=None,
            ),
            derived_quantities=[], dimensions=3,
            time_steps=None, raw_metadata={},
        )
        d = ctx.to_dict()
        json_str = json.dumps(d)
        assert "cell_count" in json_str
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'viznoir.context'`

**Step 3: Implement models**

```python
# src/viznoir/context/__init__.py
"""Case context extraction — solver-specific metadata for LLM reasoning."""

# src/viznoir/context/models.py
"""Data models for simulation case context (L3)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BoundaryCondition:
    """Single boundary condition on a patch for a field."""
    patch_name: str
    field: str
    type: str       # "fixedValue", "noSlip", "zeroGradient", etc.
    value: Any      # [1, 0, 0], 0, None (for derived types)


@dataclass
class TransportProperty:
    """A physical transport property."""
    name: str       # "nu", "mu", "rho", "Cp", "k"
    value: float
    unit: str | None = None


@dataclass
class SolverInfo:
    """Solver identification and settings."""
    name: str                        # "icoFoam", "simpleFoam"
    algorithm: str | None = None     # "SIMPLE", "PISO", "PIMPLE"
    turbulence_model: str | None = None
    steady: bool | None = None


@dataclass
class MeshQuality:
    """Mesh quality metrics."""
    cell_count: int
    point_count: int
    cell_types: dict[str, int]
    bounding_box: tuple[list[float], list[float]]
    max_aspect_ratio: float | None = None
    max_non_orthogonality: float | None = None
    max_skewness: float | None = None


@dataclass
class DerivedQuantity:
    """A derived dimensionless number or quantity."""
    name: str                     # "Re", "Ma", "Pr"
    value: float
    formula: str                  # "U_ref * L_ref / nu"
    inputs: dict[str, float] = field(default_factory=dict)


@dataclass
class CaseContext:
    """Full case context — the L3 contract for solver parsers.

    New solver parsers MUST populate at least:
    - boundary_conditions (required)
    - mesh_quality (required)
    - dimensions (required)
    """
    solver: SolverInfo | None
    boundary_conditions: list[BoundaryCondition]
    transport_properties: list[TransportProperty]
    mesh_quality: MeshQuality
    derived_quantities: list[DerivedQuantity]
    dimensions: int
    time_steps: list[float] | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for MCP transport."""
        return asdict(self)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context/test_models.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/viznoir/context/ tests/test_context/
git commit -m "feat: add L3 CaseContext data models (context/models.py)

Dataclasses: BoundaryCondition, TransportProperty, SolverInfo,
MeshQuality, DerivedQuantity, CaseContext with to_dict() for MCP.
Contract for new solver parser integrations."
```

---

### Task 2: ContextParser Protocol + GenericParser + Registry

**Files:**
- Create: `src/viznoir/context/parser.py`
- Create: `src/viznoir/context/generic.py`
- Test: `tests/test_context/test_parser.py`

**Step 1: Write failing tests**

```python
# tests/test_context/test_parser.py
"""Tests for ContextParser protocol and registry."""
from __future__ import annotations

import vtk


def _make_wavelet_file(tmp_path):
    """Create a .vti file for testing."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
    src.Update()
    path = str(tmp_path / "test.vti")
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetFileName(path)
    writer.SetInputData(src.GetOutput())
    writer.Write()
    return path


class TestContextParserRegistry:
    def test_get_parser_returns_generic_for_vti(self, tmp_path):
        from viznoir.context.parser import get_parser
        path = _make_wavelet_file(tmp_path)
        parser = get_parser(path)
        assert parser is not None

    def test_get_parser_returns_generic_for_unknown(self):
        from viznoir.context.parser import get_parser
        parser = get_parser("/fake/file.xyz")
        assert parser is not None  # GenericParser as fallback


class TestGenericParser:
    def test_can_parse_any_path(self):
        from viznoir.context.generic import GenericContextParser
        p = GenericContextParser()
        assert p.can_parse("/any/file.vtu") is True

    def test_parse_vti_returns_case_context(self, tmp_path):
        from viznoir.context.generic import GenericContextParser
        from viznoir.context.models import CaseContext
        path = _make_wavelet_file(tmp_path)
        p = GenericContextParser()
        ctx = p.parse(path)
        assert isinstance(ctx, CaseContext)
        assert ctx.mesh_quality.cell_count > 0
        assert ctx.mesh_quality.point_count > 0
        assert ctx.dimensions in (2, 3)

    def test_parse_extracts_bounding_box(self, tmp_path):
        from viznoir.context.generic import GenericContextParser
        path = _make_wavelet_file(tmp_path)
        ctx = GenericContextParser().parse(path)
        bb = ctx.mesh_quality.bounding_box
        assert len(bb) == 2  # (min, max)
        assert len(bb[0]) == 3

    def test_parse_extracts_cell_types(self, tmp_path):
        from viznoir.context.generic import GenericContextParser
        path = _make_wavelet_file(tmp_path)
        ctx = GenericContextParser().parse(path)
        assert sum(ctx.mesh_quality.cell_types.values()) == ctx.mesh_quality.cell_count
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement parser protocol and generic parser**

```python
# src/viznoir/context/parser.py
"""ContextParser protocol and registry."""
from __future__ import annotations

from typing import Protocol

from viznoir.context.models import CaseContext


class ContextParser(Protocol):
    """Protocol for solver-specific case context parsers.

    To add a new solver:
    1. Implement this protocol
    2. Register in _PARSER_REGISTRY
    3. Implement can_parse() to detect your solver's file structure
    4. Implement parse() to extract CaseContext
    """

    def can_parse(self, path: str) -> bool:
        """Return True if this parser can handle the given path."""
        ...

    def parse(self, path: str) -> CaseContext:
        """Extract CaseContext from the given path."""
        ...


# Registry: ordered by priority (most specific first)
_PARSER_REGISTRY: list[ContextParser] = []


def register_parser(parser: ContextParser) -> None:
    """Register a context parser. First registered = highest priority."""
    _PARSER_REGISTRY.insert(0, parser)


def get_parser(path: str) -> ContextParser:
    """Find the best parser for a given path. Falls back to GenericParser."""
    for parser in _PARSER_REGISTRY:
        if parser.can_parse(path):
            return parser
    # Lazy import to avoid circular dependency
    from viznoir.context.generic import GenericContextParser
    return GenericContextParser()


def parse_case_context(path: str) -> CaseContext:
    """Convenience: find parser and parse in one call."""
    return get_parser(path).parse(path)
```

```python
# src/viznoir/context/generic.py
"""Generic context parser — mesh quality from VTK data, no solver-specific info."""
from __future__ import annotations

from viznoir.context.models import CaseContext, MeshQuality


class GenericContextParser:
    """Fallback parser for any VTK-readable file. Extracts mesh quality only."""

    def can_parse(self, path: str) -> bool:
        return True  # Fallback: accepts anything

    def parse(self, path: str) -> CaseContext:
        from viznoir.engine.readers import read_dataset
        dataset = read_dataset(path)
        return self._extract(dataset)

    def _extract(self, dataset: object) -> CaseContext:
        """Extract CaseContext from a VTK dataset object."""
        import vtk

        n_cells = dataset.GetNumberOfCells()  # type: ignore[union-attr]
        n_points = dataset.GetNumberOfPoints()  # type: ignore[union-attr]

        # Cell type census
        cell_types: dict[str, int] = {}
        _TYPE_NAMES = {
            vtk.VTK_HEXAHEDRON: "hexahedron",
            vtk.VTK_TETRA: "tetrahedron",
            vtk.VTK_WEDGE: "wedge",
            vtk.VTK_PYRAMID: "pyramid",
            vtk.VTK_QUAD: "quad",
            vtk.VTK_TRIANGLE: "triangle",
            vtk.VTK_VOXEL: "voxel",
            vtk.VTK_PIXEL: "pixel",
            vtk.VTK_LINE: "line",
            vtk.VTK_VERTEX: "vertex",
        }
        for i in range(n_cells):
            ct = dataset.GetCellType(i)  # type: ignore[union-attr]
            name = _TYPE_NAMES.get(ct, f"type_{ct}")
            cell_types[name] = cell_types.get(name, 0) + 1

        # Bounding box
        bounds = list(dataset.GetBounds())  # type: ignore[union-attr]
        bb_min = [bounds[0], bounds[2], bounds[4]]
        bb_max = [bounds[1], bounds[3], bounds[5]]

        # Infer dimensions: if one axis extent is zero or very thin, it's 2D
        extents = [bb_max[i] - bb_min[i] for i in range(3)]
        max_extent = max(extents) if max(extents) > 0 else 1.0
        thin_axes = sum(1 for e in extents if e / max_extent < 0.01)
        dimensions = 2 if thin_axes >= 1 else 3

        return CaseContext(
            solver=None,
            boundary_conditions=[],
            transport_properties=[],
            mesh_quality=MeshQuality(
                cell_count=n_cells,
                point_count=n_points,
                cell_types=cell_types,
                bounding_box=(bb_min, bb_max),
                max_aspect_ratio=None,
                max_non_orthogonality=None,
                max_skewness=None,
            ),
            derived_quantities=[],
            dimensions=dimensions,
            time_steps=None,
            raw_metadata={},
        )
```

**Step 4: Run tests**

Run: `pytest tests/test_context/test_parser.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/viznoir/context/parser.py src/viznoir/context/generic.py tests/test_context/test_parser.py
git commit -m "feat: add ContextParser protocol + GenericParser

ContextParser protocol with register/get_parser/parse_case_context.
GenericContextParser: mesh quality + dimensions from any VTK dataset.
Registry pattern for solver-specific parser extensions."
```

---

### Task 3: OpenFOAM Context Parser

**Files:**
- Create: `src/viznoir/context/openfoam.py`
- Create: `tests/test_context/test_openfoam.py`
- Create: `tests/fixtures/openfoam_cavity/` (minimal fixture)
- Modify: `src/viznoir/context/__init__.py` (auto-register)

**Step 1: Create OpenFOAM fixture**

Create a minimal cavity case structure for testing (no actual mesh, just text files):

```
tests/fixtures/openfoam_cavity/
├── 0/
│   ├── U
│   └── p
├── constant/
│   └── transportProperties
└── system/
    └── controlDict
```

Fixture file contents:

```
# tests/fixtures/openfoam_cavity/0/U
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    movingWall
    {
        type            fixedValue;
        value           uniform (1 0 0);
    }
    fixedWalls
    {
        type            noSlip;
    }
    frontAndBack
    {
        type            empty;
    }
}
```

```
# tests/fixtures/openfoam_cavity/0/p
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    movingWall
    {
        type            zeroGradient;
    }
    fixedWalls
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}
```

```
# tests/fixtures/openfoam_cavity/constant/transportProperties
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}

nu              [0 2 -1 0 0 0 0] 0.01;
```

```
# tests/fixtures/openfoam_cavity/system/controlDict
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         0.5;
deltaT          0.005;
writeControl    timeStep;
writeInterval   20;
```

**Step 2: Write failing tests**

```python
# tests/test_context/test_openfoam.py
"""Tests for OpenFOAM context parser."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "openfoam_cavity"


@pytest.fixture
def cavity_dir():
    if not FIXTURE_DIR.exists():
        pytest.skip("OpenFOAM cavity fixture not found")
    return str(FIXTURE_DIR)


class TestOpenFOAMParser:
    def test_can_parse_with_0_dir(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        p = OpenFOAMContextParser()
        assert p.can_parse(cavity_dir) is True

    def test_cannot_parse_random_dir(self, tmp_path):
        from viznoir.context.openfoam import OpenFOAMContextParser
        p = OpenFOAMContextParser()
        assert p.can_parse(str(tmp_path)) is False


class TestOpenFOAMBoundaryConditions:
    def test_extracts_velocity_bcs(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        ctx = OpenFOAMContextParser().parse(cavity_dir)
        u_bcs = [bc for bc in ctx.boundary_conditions if bc.field == "U"]
        assert len(u_bcs) == 3
        moving = next(bc for bc in u_bcs if bc.patch_name == "movingWall")
        assert moving.type == "fixedValue"
        assert moving.value == [1, 0, 0]

    def test_extracts_pressure_bcs(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        ctx = OpenFOAMContextParser().parse(cavity_dir)
        p_bcs = [bc for bc in ctx.boundary_conditions if bc.field == "p"]
        assert len(p_bcs) == 3
        moving = next(bc for bc in p_bcs if bc.patch_name == "movingWall")
        assert moving.type == "zeroGradient"


class TestOpenFOAMTransport:
    def test_extracts_nu(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        ctx = OpenFOAMContextParser().parse(cavity_dir)
        nu_props = [tp for tp in ctx.transport_properties if tp.name == "nu"]
        assert len(nu_props) == 1
        assert nu_props[0].value == pytest.approx(0.01)


class TestOpenFOAMSolver:
    def test_extracts_solver_info(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        ctx = OpenFOAMContextParser().parse(cavity_dir)
        assert ctx.solver is not None
        assert ctx.solver.name == "icoFoam"

    def test_raw_metadata_has_timing(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        ctx = OpenFOAMContextParser().parse(cavity_dir)
        assert "endTime" in ctx.raw_metadata
        assert ctx.raw_metadata["endTime"] == pytest.approx(0.5)
        assert ctx.raw_metadata["deltaT"] == pytest.approx(0.005)


class TestOpenFOAMDerived:
    def test_computes_reynolds_number(self, cavity_dir):
        from viznoir.context.openfoam import OpenFOAMContextParser
        ctx = OpenFOAMContextParser().parse(cavity_dir)
        re_list = [dq for dq in ctx.derived_quantities if dq.name == "Re"]
        assert len(re_list) == 1
        assert re_list[0].value == pytest.approx(100.0)


class TestOpenFOAMDictParser:
    """Unit tests for the low-level OpenFOAM dictionary parser."""

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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context/test_openfoam.py -v`
Expected: FAIL

**Step 3: Implement OpenFOAM parser**

Create `src/viznoir/context/openfoam.py` — parse OpenFOAM text dictionary files:

Key implementation points:
- `can_parse()`: check if `0/` and `constant/` directories exist at path (or parent of .foam file)
- `_parse_boundary_file()`: regex-based parser for OpenFOAM boundary condition files in `0/`
- `_parse_transport_properties()`: extract `nu`, `mu`, etc. from `constant/transportProperties`
- `_parse_control_dict()`: extract solver name, timing from `system/controlDict`
- `_parse_openfoam_value()`: utility to parse `uniform (1 0 0)`, `0.01`, `(1 0 0)` etc.
- `_compute_derived()`: calculate Re from transport properties + boundary values + bounding box

Register in `src/viznoir/context/__init__.py`:
```python
from viznoir.context.openfoam import OpenFOAMContextParser
from viznoir.context.parser import register_parser
register_parser(OpenFOAMContextParser())
```

**Step 4: Run tests**

Run: `pytest tests/test_context/test_openfoam.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/viznoir/context/openfoam.py src/viznoir/context/__init__.py \
        tests/test_context/test_openfoam.py tests/fixtures/openfoam_cavity/
git commit -m "feat: add OpenFOAM context parser (L3)

Parse 0/ boundary files, constant/transportProperties, system/controlDict.
Extract BC, nu, solver info, timing. Auto-compute Re from transport + geometry.
Registered via ContextParser protocol for auto-discovery."
```

---

### Task 4: L2 Field Topology Analyzer

**Files:**
- Create: `src/viznoir/engine/topology.py`
- Test: `tests/test_engine/test_topology.py`

This is the core value — universal VTK field topology extraction.

**Step 1: Write failing tests**

```python
# tests/test_engine/test_topology.py
"""Tests for engine/topology.py — field topology extraction (L2)."""
from __future__ import annotations

import numpy as np
import pytest
import vtk
from vtk.util.numpy_support import numpy_to_vtk


def _make_cavity_2d(n: int = 20):
    """Create a synthetic 2D lid-driven cavity velocity field.

    Top wall moves right (Ux=1), creates a clockwise primary vortex.
    """
    grid = vtk.vtkImageData()
    grid.SetDimensions(n + 1, n + 1, 1)
    grid.SetOrigin(0, 0, 0)
    grid.SetSpacing(1.0 / n, 1.0 / n, 1.0)

    # Synthetic velocity: clockwise vortex centered at (0.5, 0.75)
    n_pts = grid.GetNumberOfPoints()
    vel = np.zeros((n_pts, 3), dtype=np.float64)
    for i in range(n_pts):
        x, y, _ = grid.GetPoint(i)
        # Stream function: psi = sin(pi*x) * sin(pi*y) * y
        # Simplified lid-driven-like pattern
        vel[i, 0] = np.sin(np.pi * x) * np.cos(np.pi * y) * 0.5   # Ux
        vel[i, 1] = -np.cos(np.pi * x) * np.sin(np.pi * y) * 0.5  # Uy
        vel[i, 2] = 0.0

    vtk_vel = numpy_to_vtk(vel)
    vtk_vel.SetName("U")
    vtk_vel.SetNumberOfComponents(3)
    grid.GetPointData().AddArray(vtk_vel)
    grid.GetPointData().SetActiveVectors("U")

    # Add pressure field
    pressure = np.zeros(n_pts, dtype=np.float64)
    for i in range(n_pts):
        x, y, _ = grid.GetPoint(i)
        pressure[i] = -0.5 * (vel[i, 0] ** 2 + vel[i, 1] ** 2)  # Bernoulli-like
    vtk_p = numpy_to_vtk(pressure)
    vtk_p.SetName("p")
    grid.GetPointData().AddArray(vtk_p)

    return grid


class TestVortexDetection:
    def test_detects_primary_vortex(self):
        from viznoir.engine.topology import detect_vortices
        ds = _make_cavity_2d(30)
        vortices = detect_vortices(ds, "U")
        assert len(vortices) >= 1
        # Primary vortex should be roughly centered
        primary = max(vortices, key=lambda v: v.strength)
        assert 0.2 < primary.center[0] < 0.8
        assert 0.2 < primary.center[1] < 0.8

    def test_vortex_has_rotation(self):
        from viznoir.engine.topology import detect_vortices
        ds = _make_cavity_2d(30)
        vortices = detect_vortices(ds, "U")
        assert len(vortices) >= 1
        assert vortices[0].rotation in ("clockwise", "counter-clockwise")

    def test_vortex_has_positive_strength(self):
        from viznoir.engine.topology import detect_vortices
        ds = _make_cavity_2d(30)
        vortices = detect_vortices(ds, "U")
        for v in vortices:
            assert v.strength > 0

    def test_empty_velocity_returns_empty(self):
        from viznoir.engine.topology import detect_vortices
        grid = vtk.vtkImageData()
        grid.SetDimensions(3, 3, 1)
        vel = numpy_to_vtk(np.zeros((9, 3), dtype=np.float64))
        vel.SetName("U")
        vel.SetNumberOfComponents(3)
        grid.GetPointData().AddArray(vel)
        vortices = detect_vortices(grid, "U")
        assert vortices == []


class TestCriticalPoints:
    def test_finds_stagnation_points(self):
        from viznoir.engine.topology import detect_critical_points
        ds = _make_cavity_2d(30)
        cps = detect_critical_points(ds, "U")
        assert len(cps) >= 1
        # All stagnation points should have low velocity
        for cp in cps:
            assert cp.velocity_magnitude < 0.1

    def test_critical_point_has_position(self):
        from viznoir.engine.topology import detect_critical_points
        ds = _make_cavity_2d(30)
        cps = detect_critical_points(ds, "U")
        if cps:
            assert len(cps[0].position) >= 2


class TestCenterlineProfiles:
    def test_auto_probes_return_profiles(self):
        from viznoir.engine.topology import extract_centerline_profiles
        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["U", "p"], num_lines=2)
        assert len(profiles) >= 2

    def test_profile_has_field_data(self):
        from viznoir.engine.topology import extract_centerline_profiles
        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["U"], num_lines=1)
        assert len(profiles) >= 1
        p = profiles[0]
        assert p.name != ""
        assert len(p.coordinates) > 0
        assert "Ux" in p.fields or "U" in p.fields

    def test_profile_coordinates_are_normalized(self):
        from viznoir.engine.topology import extract_centerline_profiles
        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["p"], num_lines=1)
        coords = profiles[0].coordinates
        assert min(coords) >= 0.0
        assert max(coords) <= 1.01  # small float tolerance


class TestGradientAnalysis:
    def test_gradient_stats(self):
        from viznoir.engine.topology import compute_gradient_stats
        ds = _make_cavity_2d(30)
        stats = compute_gradient_stats(ds, "p")
        assert "mean_magnitude" in stats
        assert "max_magnitude" in stats
        assert stats["max_magnitude"] >= stats["mean_magnitude"]


class TestFieldTopologyFull:
    def test_analyze_field_topology_velocity(self):
        from viznoir.engine.topology import analyze_field_topology
        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "U")
        assert topo.field_name == "U"
        assert len(topo.vortices) >= 1
        assert topo.field_range["min"] is not None
        assert len(topo.centerline_profiles) >= 1

    def test_analyze_field_topology_scalar(self):
        from viznoir.engine.topology import analyze_field_topology
        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "p")
        assert topo.field_name == "p"
        assert topo.vortices == []  # Scalar field: no vortex detection
        assert topo.gradient_stats is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine/test_topology.py -v`
Expected: FAIL

**Step 3: Implement topology analyzer**

Create `src/viznoir/engine/topology.py` with these functions:

- `detect_vortices(dataset, field_name, threshold)` → `list[Vortex]`
  - `vtkGradientFilter` for velocity gradients
  - Compute Q-criterion: Q = 0.5 * (|Ω|² - |S|²)
  - Threshold Q > 0, `vtkConnectivityFilter` for regions
  - Compute centroid, vorticity at center → strength, rotation

- `detect_critical_points(dataset, field_name, epsilon)` → `list[CriticalPoint]`
  - Compute velocity magnitude, threshold < epsilon
  - Extract point positions

- `extract_centerline_profiles(dataset, field_names, num_lines)` → `list[LineProfile]`
  - Auto-detect probe lines from bounding box center (x, y, z axes)
  - `vtkLineSource` + `vtkProbeFilter`
  - Extract field values along line

- `compute_gradient_stats(dataset, field_name)` → `dict`
  - `vtkGradientFilter` on scalar field
  - Compute mean/max gradient magnitude, dominant direction

- `analyze_field_topology(dataset, field_name)` → `FieldTopology`
  - Orchestrator: calls the above functions
  - Detects if field is vector (→ vortex detection) or scalar (→ gradient only)
  - Returns complete FieldTopology dataclass

Data models (`Vortex`, `CriticalPoint`, `LineProfile`, `FieldTopology`) as dataclasses in the same file.

**Step 4: Run tests**

Run: `pytest tests/test_engine/test_topology.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/viznoir/engine/topology.py tests/test_engine/test_topology.py
git commit -m "feat: add L2 FieldTopology analyzer (engine/topology.py)

Vortex detection (Q-criterion + connectivity), critical points,
auto centerline profiles (vtkProbeFilter), gradient analysis.
Universal VTK — works with any dataset with velocity/pressure fields."
```

---

### Task 5: `inspect_physics` MCP Tool

**Files:**
- Create: `src/viznoir/tools/inspect_physics.py`
- Modify: `src/viznoir/server.py` (add tool registration)
- Test: `tests/test_tools/test_inspect_physics.py`

**Step 1: Write failing tests**

```python
# tests/test_tools/test_inspect_physics.py
"""Tests for inspect_physics MCP tool."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import vtk


@pytest.fixture
def vti_file(tmp_path):
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
    src.Update()
    path = str(tmp_path / "test.vti")
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetFileName(path)
    writer.SetInputData(src.GetOutput())
    writer.Write()
    return path


class TestInspectPhysicsImpl:
    @pytest.mark.asyncio
    async def test_returns_field_topologies(self, vti_file):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        result = await inspect_physics_impl(vti_file)
        assert "field_topologies" in result
        assert isinstance(result["field_topologies"], list)

    @pytest.mark.asyncio
    async def test_returns_case_context_null_for_vti(self, vti_file):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        result = await inspect_physics_impl(vti_file)
        # VTI has no case context (no OpenFOAM structure)
        # GenericParser provides mesh quality only
        assert "case_context" in result
        ctx = result["case_context"]
        assert ctx is not None  # GenericParser always returns something
        assert ctx["mesh_quality"]["cell_count"] > 0

    @pytest.mark.asyncio
    async def test_returns_extraction_time(self, vti_file):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        result = await inspect_physics_impl(vti_file)
        assert "extraction_time_ms" in result
        assert result["extraction_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_with_openfoam_case_dir(self, vti_file):
        """When case_dir points to OpenFOAM structure, L3 is enriched."""
        fixture = Path(__file__).parent.parent / "fixtures" / "openfoam_cavity"
        if not fixture.exists():
            pytest.skip("OpenFOAM fixture not found")
        from viznoir.tools.inspect_physics import inspect_physics_impl
        result = await inspect_physics_impl(vti_file, case_dir=str(fixture))
        ctx = result["case_context"]
        assert len(ctx["boundary_conditions"]) > 0

    @pytest.mark.asyncio
    async def test_field_filter(self, vti_file):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        result = await inspect_physics_impl(vti_file, fields=["RTData"])
        assert len(result["field_topologies"]) == 1
        assert result["field_topologies"][0]["field_name"] == "RTData"

    @pytest.mark.asyncio
    async def test_hint_when_no_case_dir(self, vti_file):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        result = await inspect_physics_impl(vti_file, case_dir=None)
        # Should provide hint for LLM
        assert "case_context_hint" in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools/test_inspect_physics.py -v`
Expected: FAIL

**Step 3: Implement**

```python
# src/viznoir/tools/inspect_physics.py
"""inspect_physics tool — structured physics data extraction for LLM reasoning."""
from __future__ import annotations

import asyncio
import time
from typing import Any


async def inspect_physics_impl(
    file_path: str,
    *,
    case_dir: str | None = None,
    fields: list[str] | None = None,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> dict[str, Any]:
    """Extract L2 field topology + L3 case context for LLM consumption."""
    loop = asyncio.get_event_loop()
    t0 = time.perf_counter()

    def _run() -> dict[str, Any]:
        from viznoir.engine.readers import read_dataset
        from viznoir.engine.topology import analyze_field_topology
        from viznoir.context.parser import parse_case_context

        dataset = read_dataset(file_path)

        # Discover fields
        pd = dataset.GetPointData()
        cd = dataset.GetCellData()
        all_fields = []
        for i in range(pd.GetNumberOfArrays()):
            name = pd.GetArrayName(i)
            if name:
                all_fields.append(name)
        for i in range(cd.GetNumberOfArrays()):
            name = cd.GetArrayName(i)
            if name:
                all_fields.append(name)

        if fields:
            all_fields = [f for f in all_fields if f in fields]

        # L2: Field topology for each field
        topologies = []
        for field_name in all_fields:
            topo = analyze_field_topology(
                dataset, field_name,
                probe_lines=probe_lines,
                vortex_threshold=vortex_threshold,
            )
            topologies.append(topo.to_dict())

        # L3: Case context
        context_path = case_dir or file_path
        case_ctx = parse_case_context(context_path)
        case_dict = case_ctx.to_dict()

        # Hint for LLM when L3 is sparse
        hint = None
        if not case_ctx.boundary_conditions and not case_ctx.solver:
            hint = (
                "L3 case context unavailable (no solver-specific files found). "
                "Ask the user for: boundary conditions, Reynolds number, "
                "solver type, and simulation assumptions."
            )

        return {
            "field_topologies": topologies,
            "case_context": case_dict,
            "case_context_hint": hint,
        }

    result = await loop.run_in_executor(None, _run)
    result["extraction_time_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return result
```

Add to `src/viznoir/server.py` (after the `analyze_data` tool, around line 999):

```python
@mcp.tool()
async def inspect_physics(
    file_path: str,
    case_dir: str | None = None,
    fields: list[str] | None = None,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> dict[str, Any]:
    """Extract structured physics data from simulation results for analysis.

    Returns L2 field topology (vortices, critical points, centerline profiles,
    gradient analysis) + L3 case context (boundary conditions, transport
    properties, solver info, mesh quality, derived quantities like Re).

    L2 works universally with any VTK dataset. L3 requires solver-specific
    files (currently supports OpenFOAM; extensible via ContextParser protocol).

    Use this instead of analyze_data for physics-aware analysis workflows.

    Args:
        file_path: Path to VTK/OpenFOAM data file
        case_dir: Path to solver case directory (e.g., OpenFOAM case root).
                  If None, attempts to infer from file_path parent.
        fields: Analyze only these fields (None for all)
        probe_lines: Number of auto centerline probes (default 3)
        vortex_threshold: Q-criterion threshold for vortex detection
    """
    file_path = _validate_file_path(file_path)
    logger.debug("tool.inspect_physics: file=%s case_dir=%s", file_path, case_dir)
    t0 = time.monotonic()
    from viznoir.tools.inspect_physics import inspect_physics_impl
    result = await inspect_physics_impl(
        file_path, case_dir=case_dir, fields=fields,
        probe_lines=probe_lines, vortex_threshold=vortex_threshold,
    )
    logger.debug("tool.inspect_physics: done in %.2fs", time.monotonic() - t0)
    return result
```

**Step 4: Run tests**

Run: `pytest tests/test_tools/test_inspect_physics.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `pytest --cov=viznoir --cov-report=term-missing -q`
Expected: ALL PASS, coverage >= 80%

**Step 6: Commit**

```bash
git add src/viznoir/tools/inspect_physics.py src/viznoir/server.py \
        tests/test_tools/test_inspect_physics.py
git commit -m "feat: add inspect_physics MCP tool

Replaces analyze_data with structured L2+L3 extraction.
L2: field topology (vortices, critical points, probes, gradients)
L3: case context (BC, transport, solver, mesh quality, Re)
LLM-ready JSON output for physics reasoning."
```

---

### Task 6: Deprecate `analyze_data` + Update CLAUDE.md + Final Verification

**Files:**
- Modify: `src/viznoir/server.py` (deprecation notice on analyze_data)
- Modify: `CLAUDE.md` (update architecture, tool count, add inspect_physics)
- Modify: `README.md` / `README.ko.md` (tool count 21 → 22)

**Step 1: Add deprecation to analyze_data**

In `src/viznoir/server.py`, update the `analyze_data` docstring:

```python
async def analyze_data(...):
    """[DEPRECATED — use inspect_physics instead]

    Analyze VTK/simulation data. Returns basic statistics and hardcoded
    equation suggestions. For physics-aware analysis with vortex detection,
    boundary condition parsing, and LLM-ready structured data, use
    inspect_physics.
    ...
    """
```

**Step 2: Update CLAUDE.md**

- Tool count: 21 → 22
- Add `inspect_physics` to architecture section
- Add `context/` module to file structure
- Add `engine/topology.py` description

**Step 3: Update README metrics**

- Tool count badge/table: 21 → 22
- Test count: update if changed

**Step 4: Run full verification**

```bash
ruff check src/ tests/
mypy src/viznoir/ --ignore-missing-imports
pytest --cov=viznoir --cov-report=term-missing -q
```

Expected: 0 lint errors, 0 type errors, all tests pass, coverage >= 80%

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: deprecate analyze_data, update docs for inspect_physics

analyze_data marked deprecated (use inspect_physics).
CLAUDE.md: add context/ module, topology.py, tool count 22.
README: update tool count and architecture description."
```

---

## Execution Order

Tasks 1-2 are foundational (data models + parser protocol).
Task 3 depends on 1-2 (OpenFOAM parser uses models).
Task 4 is independent of 1-3 (pure VTK, no context needed).
Task 5 depends on all (integrates L2 + L3).
Task 6 is cleanup/docs.

**Parallelizable:** Task 3 and Task 4 can run in parallel after Tasks 1-2.

```
Task 1 → Task 2 → ┬→ Task 3 (OpenFOAM) ─┬→ Task 5 → Task 6
                   └→ Task 4 (Topology)  ─┘
```
