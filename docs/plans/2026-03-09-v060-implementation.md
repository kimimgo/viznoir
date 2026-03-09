# viznoir v0.6.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Science Storyteller v2 (L2 FieldTopology + L3 CaseContext + `inspect_physics` MCP tool) + compose_assets quality improvement — parallel execution via agent team.

**Architecture:** New `context/` module with `ContextParser` protocol for solver-specific metadata. New `engine/topology.py` for universal VTK field topology analysis (Q-criterion, critical points, centerline probes). Improved `anim/compositor.py` for professional layout quality. `inspect_physics` MCP tool integrates L2+L3.

**Tech Stack:** VTK 9.4 (vtkGradientFilter, vtkProbeFilter, vtkConnectivityFilter), Python 3.10+ dataclasses, Pydantic, PIL/Pillow.

---

## Agent Team Assignment

| Agent | Tasks | Owned Files |
|-------|-------|-------------|
| cc-viznoir-1 | A-1, A-2, A-3 | `src/viznoir/context/*`, `tests/test_context/*` |
| cc-viznoir-2 | A-4 | `src/viznoir/engine/topology.py`, `tests/test_engine/test_topology.py` |
| cc-viznoir-3 | B-1, B-2, B-3 | `src/viznoir/anim/compositor.py`, `tests/test_core/test_compositor*.py` |
| cc (Lead) | A-5, A-6 | `src/viznoir/tools/inspect_physics.py`, `src/viznoir/server.py`, docs |

---

### Task A-1: L3 CaseContext Data Models

**Owner:** cc-viznoir-1

**Files:**
- Create: `src/viznoir/context/__init__.py`
- Create: `src/viznoir/context/models.py`
- Create: `tests/test_context/__init__.py`
- Test: `tests/test_context/test_models.py`

**Step 1: Write failing tests**

```python
# tests/test_context/__init__.py
# (empty)

# tests/test_context/test_models.py
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
            bounding_box=[[0, 0, 0], [0.1, 0.1, 0.005]],
        )
        assert mq.dimensions == 2  # thin z-axis → 2D


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

    def test_to_dict_with_all_fields(self):
        from viznoir.context.models import (
            BoundaryCondition, CaseContext, DerivedQuantity,
            MeshQuality, SolverInfo, TransportProperty,
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'viznoir.context'`

**Step 3: Write minimal implementation**

```python
# src/viznoir/context/__init__.py
"""Context module — solver-specific case metadata extraction."""

# src/viznoir/context/models.py
"""L3 CaseContext data models for solver-specific metadata."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class BoundaryCondition:
    """A boundary condition on a specific patch for a specific field."""
    patch_name: str
    field: str
    type: str
    value: Any = None


@dataclass
class TransportProperty:
    """A transport property (e.g., viscosity, density)."""
    name: str
    value: float
    unit: str | None = None


@dataclass
class SolverInfo:
    """Solver metadata (name, algorithm, turbulence model)."""
    name: str
    algorithm: str | None = None
    turbulence_model: str | None = None
    steady: bool = True


@dataclass
class MeshQuality:
    """Mesh quality metrics extracted from the dataset."""
    cell_count: int
    point_count: int
    cell_types: dict[str, int]
    bounding_box: list[list[float]]
    max_aspect_ratio: float | None = None
    max_non_orthogonality: float | None = None
    max_skewness: float | None = None

    @property
    def dimensions(self) -> int:
        """Infer 2D vs 3D from bounding box thickness."""
        bb = self.bounding_box
        extents = [abs(bb[1][i] - bb[0][i]) for i in range(3)]
        min_extent = min(extents)
        max_extent = max(extents)
        if max_extent == 0:
            return 3
        if min_extent / max_extent < 0.01:
            return 2
        return 3


@dataclass
class DerivedQuantity:
    """A derived dimensionless quantity (Re, Ma, Pr, etc.)."""
    name: str
    value: float
    formula: str
    inputs: dict[str, float]


@dataclass
class CaseContext:
    """Complete case context from solver-specific metadata."""
    mesh_quality: MeshQuality
    boundary_conditions: list[BoundaryCondition] = field(default_factory=list)
    transport_properties: list[TransportProperty] = field(default_factory=list)
    solver: SolverInfo | None = None
    derived_quantities: list[DerivedQuantity] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context/test_models.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/context/ tests/test_context/
git commit -m "feat(context): add L3 CaseContext data models"
```

---

### Task A-2: ContextParser Protocol + GenericParser + Registry

**Owner:** cc-viznoir-1 (depends on A-1)

**Files:**
- Create: `src/viznoir/context/parser.py`
- Create: `src/viznoir/context/generic.py`
- Test: `tests/test_context/test_parser.py`

**Step 1: Write failing tests**

```python
# tests/test_context/test_parser.py
"""Tests for ContextParser protocol, GenericParser, and Registry."""
from __future__ import annotations

import numpy as np


def _make_vtk_dataset():
    """Create a minimal VTK dataset for testing."""
    import vtkmodules.vtkCommonDataModel as dm
    import vtkmodules.vtkCommonCore as core

    grid = dm.vtkImageData()
    grid.SetDimensions(11, 11, 2)
    grid.SetOrigin(0, 0, 0)
    grid.SetSpacing(0.01, 0.01, 0.005)

    n_cells = grid.GetNumberOfCells()
    n_points = grid.GetNumberOfPoints()

    # Add a scalar field
    pressure = core.vtkFloatArray()
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/viznoir/context/parser.py
"""ContextParser protocol and registry for solver-specific parsers."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from viznoir.context.models import CaseContext


@runtime_checkable
class ContextParser(Protocol):
    """Protocol for solver-specific context parsers."""

    def can_parse(self, path: str) -> bool:
        """Return True if this parser can handle the given file/directory."""
        ...

    def parse_dataset(self, dataset: object) -> CaseContext:
        """Extract CaseContext from a VTK dataset."""
        ...


class ContextParserRegistry:
    """Registry of context parsers, checked in order."""

    def __init__(self) -> None:
        self._parsers: list[ContextParser] = []

    def register(self, parser: ContextParser) -> None:
        self._parsers.append(parser)

    def get_parser(self, path: str) -> ContextParser | None:
        for parser in self._parsers:
            if parser.can_parse(path):
                return parser
        return None


def get_default_registry() -> ContextParserRegistry:
    """Create registry with built-in parsers (Generic as fallback)."""
    from viznoir.context.generic import GenericContextParser

    registry = ContextParserRegistry()
    # Add specific parsers first (OpenFOAM, etc.) — they'll be checked in order
    # Generic is fallback — always returns True for can_parse
    registry.register(GenericContextParser())
    return registry
```

```python
# src/viznoir/context/generic.py
"""GenericContextParser — extracts mesh quality from any VTK dataset."""
from __future__ import annotations

from viznoir.context.models import CaseContext, MeshQuality


class GenericContextParser:
    """Fallback parser: extracts mesh quality from any VTK dataset."""

    def can_parse(self, path: str) -> bool:
        return True

    def parse_dataset(self, dataset: object) -> CaseContext:
        """Extract basic mesh quality metrics from a VTK dataset."""
        cell_count = dataset.GetNumberOfCells()  # type: ignore[attr-defined]
        point_count = dataset.GetNumberOfPoints()  # type: ignore[attr-defined]

        # Cell types
        cell_types: dict[str, int] = {}
        for i in range(cell_count):
            ct = dataset.GetCellType(i)  # type: ignore[attr-defined]
            name = _vtk_cell_type_name(ct)
            cell_types[name] = cell_types.get(name, 0) + 1

        # Bounding box
        bounds = list(dataset.GetBounds())  # type: ignore[attr-defined]
        bb = [
            [bounds[0], bounds[2], bounds[4]],
            [bounds[1], bounds[3], bounds[5]],
        ]

        mq = MeshQuality(
            cell_count=cell_count,
            point_count=point_count,
            cell_types=cell_types,
            bounding_box=bb,
        )

        return CaseContext(mesh_quality=mq)


def _vtk_cell_type_name(cell_type: int) -> str:
    """Map VTK cell type integer to human-readable name."""
    _MAP = {
        3: "line", 5: "triangle", 8: "pixel", 9: "quad",
        10: "tetra", 11: "voxel", 12: "hexahedron", 13: "wedge", 14: "pyramid",
    }
    return _MAP.get(cell_type, f"type_{cell_type}")
```

**Step 4: Run tests**

Run: `pytest tests/test_context/test_parser.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/context/parser.py src/viznoir/context/generic.py tests/test_context/test_parser.py
git commit -m "feat(context): add ContextParser protocol, GenericParser, and registry"
```

---

### Task A-3: OpenFOAM Context Parser

**Owner:** cc-viznoir-1 (depends on A-2)

**Files:**
- Create: `src/viznoir/context/openfoam.py`
- Test: `tests/test_context/test_openfoam.py`
- Fixture: `tests/fixtures/cavity_case/` (minimal OpenFOAM case)

**Refer to:** `docs/plans/2026-03-08-science-storyteller-v2-implementation.md` Task 3 for full parsing spec.

Key parsing targets:
- `system/controlDict` → solver name, time info
- `constant/transportProperties` → nu, rho → DerivedQuantity(Re)
- `constant/turbulenceProperties` → turbulence_model
- `0/U`, `0/p` → BoundaryCondition per patch

**Step 1: Create minimal OpenFOAM fixture**

```bash
mkdir -p tests/fixtures/cavity_case/{system,constant,0}
```

Create minimal controlDict, transportProperties, turbulenceProperties, U, p files.

**Step 2: Write failing tests**

```python
# tests/test_context/test_openfoam.py
"""Tests for OpenFOAM context parser."""
from __future__ import annotations

import os
from pathlib import Path


# Fixture path — populated in Step 1
CAVITY_DIR = str(Path(__file__).parent.parent / "fixtures" / "cavity_case")


class TestOpenFOAMParser:
    def test_can_parse_foam_dir(self):
        from viznoir.context.openfoam import OpenFOAMContextParser
        parser = OpenFOAMContextParser()
        assert parser.can_parse(CAVITY_DIR) is True

    def test_cannot_parse_random_dir(self, tmp_path):
        from viznoir.context.openfoam import OpenFOAMContextParser
        parser = OpenFOAMContextParser()
        assert parser.can_parse(str(tmp_path)) is False

    def test_parse_case_dir(self):
        from viznoir.context.openfoam import OpenFOAMContextParser
        parser = OpenFOAMContextParser()
        ctx = parser.parse_case_dir(CAVITY_DIR)
        assert ctx.solver is not None
        assert ctx.solver.name == "icoFoam"

    def test_boundary_conditions(self):
        from viznoir.context.openfoam import OpenFOAMContextParser
        parser = OpenFOAMContextParser()
        ctx = parser.parse_case_dir(CAVITY_DIR)
        assert len(ctx.boundary_conditions) > 0
        # movingWall should have fixedValue for U
        moving_wall_u = [
            bc for bc in ctx.boundary_conditions
            if bc.patch_name == "movingWall" and bc.field == "U"
        ]
        assert len(moving_wall_u) == 1
        assert moving_wall_u[0].type == "fixedValue"

    def test_transport_properties(self):
        from viznoir.context.openfoam import OpenFOAMContextParser
        parser = OpenFOAMContextParser()
        ctx = parser.parse_case_dir(CAVITY_DIR)
        nu_props = [tp for tp in ctx.transport_properties if tp.name == "nu"]
        assert len(nu_props) == 1

    def test_derived_quantities_re(self):
        from viznoir.context.openfoam import OpenFOAMContextParser
        parser = OpenFOAMContextParser()
        ctx = parser.parse_case_dir(CAVITY_DIR)
        re_q = [dq for dq in ctx.derived_quantities if dq.name == "Re"]
        # Re calculation depends on reference velocity/length — may or may not be present
        # At minimum, transport properties should be extracted


class TestRegistryIntegration:
    def test_openfoam_before_generic(self):
        from viznoir.context.openfoam import OpenFOAMContextParser
        from viznoir.context.parser import ContextParserRegistry
        from viznoir.context.generic import GenericContextParser

        registry = ContextParserRegistry()
        registry.register(OpenFOAMContextParser())
        registry.register(GenericContextParser())

        parser = registry.get_parser(CAVITY_DIR)
        assert isinstance(parser, OpenFOAMContextParser)
```

**Step 2-5:** Implement OpenFOAM parser (regex-based dict parsing for OpenFOAM files), run tests, commit.

```bash
git commit -m "feat(context): add OpenFOAM context parser with BC/transport/solver extraction"
```

---

### Task A-4: L2 Field Topology Analyzer

**Owner:** cc-viznoir-2 (independent, parallel with A-1~3)

**Files:**
- Create: `src/viznoir/engine/topology.py`
- Test: `tests/test_engine/test_topology.py`

**Refer to:** `docs/plans/2026-03-08-science-storyteller-v2-implementation.md` Task 4 for full spec.

**Data models** (in topology.py):

```python
@dataclass
class Vortex:
    center: list[float]
    strength: float
    rotation: str  # "clockwise" / "counter-clockwise"
    radius: float | None = None

@dataclass
class CriticalPoint:
    position: list[float]
    type: str  # "stagnation" / "separation" / "reattachment"
    velocity_magnitude: float

@dataclass
class LineProfile:
    start: list[float]
    end: list[float]
    num_points: int
    fields: dict[str, list[float]]  # field_name → sampled values

@dataclass
class FieldTopology:
    field_name: str
    field_range: dict[str, float]  # min, max, mean, std
    vortices: list[Vortex]
    critical_points: list[CriticalPoint]
    centerline_profiles: list[LineProfile]
    gradient_stats: dict[str, Any]
    spatial_distribution: str | None = None
```

**5 functions to implement:**

1. `detect_vortices(dataset, field_name, threshold)` → `list[Vortex]`
   - `vtkGradientFilter` on velocity → compute Q-criterion
   - Threshold Q > 0, `vtkConnectivityFilter` for regions
   - Extract centroid, vorticity sign → strength, rotation

2. `detect_critical_points(dataset, field_name, epsilon)` → `list[CriticalPoint]`
   - Find cells where velocity magnitude < epsilon
   - Classify: stagnation (near wall), separation, reattachment

3. `extract_centerline_profiles(dataset, field_names, num_lines)` → `list[LineProfile]`
   - Auto-detect centerlines from bounding box (x, y, z axis midlines)
   - `vtkLineSource` + `vtkProbeFilter` → sample fields

4. `compute_gradient_stats(dataset, field_name)` → `dict`
   - `vtkGradientFilter` on scalar → mean/max gradient magnitude

5. `analyze_field_topology(dataset, field_name)` → `FieldTopology`
   - Orchestrator: calls 1-4, computes field_range stats

**Tests: synthetic 2D cavity dataset** with known vortex at center.

```bash
git commit -m "feat(engine): add L2 field topology analyzer (vortex detection, critical points, line probes)"
```

---

### Task B-1: Layout Engine Parameterization

**Owner:** cc-viznoir-3 (independent, parallel)

**Files:**
- Modify: `src/viznoir/anim/compositor.py:62-143` (render_story_layout)
- Modify: `src/viznoir/anim/compositor.py:151-198` (render_grid_layout)
- Test: `tests/test_core/test_compositor_layout.py`

**Changes:**

1. `render_story_layout`: add `min_panel_width` param (default 200). If panels would be narrower, split into multiple rows.
2. `render_grid_layout`: add `labels` param, `padding` param (default responsive: `max(10, min(width, height) // 80)`), support `cols="auto"` based on asset count.
3. Both: responsive title/label height scaling based on canvas size.

**Step 1: Write failing tests**

```python
# tests/test_core/test_compositor_layout.py
"""Tests for improved compositor layout engine."""
from __future__ import annotations

from PIL import Image

from viznoir.anim.compositor import render_grid_layout, render_story_layout


class TestStoryLayoutImprovements:
    def test_min_panel_width_wraps_to_rows(self):
        """10 assets at 1920 width with min_panel_width=300 should wrap to 2 rows."""
        assets = [Image.new("RGBA", (400, 300), (i * 25, 0, 0, 255)) for i in range(10)]
        labels = [f"Panel {i}" for i in range(10)]
        result = render_story_layout(
            assets, labels, width=1920, height=1080, min_panel_width=300,
        )
        assert result.size == (1920, 1080)

    def test_responsive_title_height(self):
        """4K output should have larger title than 720p."""
        assets = [Image.new("RGBA", (400, 300), (100, 0, 0, 255))]
        labels = ["Test"]
        r1 = render_story_layout(assets, labels, title="Title", width=3840, height=2160)
        r2 = render_story_layout(assets, labels, title="Title", width=1280, height=720)
        assert r1.size == (3840, 2160)
        assert r2.size == (1280, 720)


class TestGridLayoutImprovements:
    def test_auto_cols(self):
        """4 assets should auto-select 2 cols."""
        assets = [Image.new("RGBA", (400, 300), (i * 60, 0, 0, 255)) for i in range(4)]
        result = render_grid_layout(assets, cols=0, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_grid_with_labels(self):
        """Grid layout should support labels."""
        assets = [Image.new("RGBA", (400, 300), (100, 0, 0, 255)) for i in range(4)]
        labels = ["A", "B", "C", "D"]
        result = render_grid_layout(
            assets, cols=2, width=1920, height=1080, labels=labels,
        )
        assert result.size == (1920, 1080)

    def test_responsive_padding(self):
        """Padding should scale with canvas size."""
        assets = [Image.new("RGBA", (400, 300), (100, 0, 0, 255)) for i in range(4)]
        result = render_grid_layout(assets, cols=2, width=3840, height=2160)
        assert result.size == (3840, 2160)

    def test_no_sparse_cells(self):
        """3 assets in 2-col grid should NOT have empty 4th cell artifact."""
        assets = [Image.new("RGBA", (400, 300), (i * 80, 0, 0, 255)) for i in range(3)]
        result = render_grid_layout(assets, cols=2, width=1920, height=1080)
        assert result.size == (1920, 1080)
```

**Step 2-4:** Implement, run tests, iterate.

**Step 5: Commit**

```bash
git commit -m "feat(compositor): parameterize layout engine — responsive padding, auto-cols, min panel width"
```

---

### Task B-2: Font System Improvement

**Owner:** cc-viznoir-3 (depends on B-1)

**Files:**
- Modify: `src/viznoir/anim/compositor.py:36-54` (_get_font, _FONT_CANDIDATES)
- Test: `tests/test_core/test_compositor_font.py`

**Changes:**

1. Expand `_FONT_CANDIDATES` with macOS/Windows paths
2. Add CJK font candidates (NotoSansCJK, etc.)
3. Font size scaling: `_get_scaled_font(base_size, canvas_width, reference_width=1920)`
4. Replace all hardcoded font sizes with scaled versions

```bash
git commit -m "feat(compositor): improve font system — platform paths, CJK support, size scaling"
```

---

### Task B-3: Label Visibility

**Owner:** cc-viznoir-3 (depends on B-2)

**Files:**
- Modify: `src/viznoir/anim/compositor.py:135-141` (label drawing in story)
- Test: `tests/test_core/test_compositor_labels.py`

**Changes:**

1. Semi-transparent background box behind label text (RGBA with alpha=180)
2. Text truncation with "..." for labels exceeding panel width
3. Consistent label positioning across layouts

```bash
git commit -m "feat(compositor): improve label visibility — background boxes, truncation"
```

---

### Task A-5: inspect_physics MCP Tool

**Owner:** cc (Lead) — depends on A-1~4 completion

**Files:**
- Create: `src/viznoir/tools/inspect_physics.py`
- Modify: `src/viznoir/server.py` (register tool)
- Test: `tests/test_tools/test_inspect_physics.py`

**Step 1: Write failing tests**

```python
# tests/test_tools/test_inspect_physics.py
"""Tests for inspect_physics MCP tool."""
from __future__ import annotations

import pytest


def _make_cavity_dataset():
    """Create a 2D cavity-like dataset with velocity and pressure."""
    import vtkmodules.vtkCommonCore as core
    import vtkmodules.vtkCommonDataModel as dm
    import numpy as np

    grid = dm.vtkImageData()
    grid.SetDimensions(21, 21, 2)
    grid.SetOrigin(0, 0, 0)
    grid.SetSpacing(0.005, 0.005, 0.005)

    n_points = grid.GetNumberOfPoints()

    # Velocity field (lid-driven pattern)
    vel = core.vtkFloatArray()
    vel.SetName("U")
    vel.SetNumberOfComponents(3)
    vel.SetNumberOfTuples(n_points)
    for i in range(n_points):
        x, y, z = grid.GetPoint(i)
        ux = y * 10.0  # simple shear
        uy = -x * 5.0
        vel.SetTuple3(i, ux, uy, 0)
    grid.GetPointData().AddArray(vel)

    # Pressure field
    pressure = core.vtkFloatArray()
    pressure.SetName("p")
    pressure.SetNumberOfTuples(n_points)
    for i in range(n_points):
        x, y, z = grid.GetPoint(i)
        pressure.SetValue(i, -(x * x + y * y))
    grid.GetPointData().AddArray(pressure)

    return grid


class TestInspectPhysicsImpl:
    async def test_returns_field_topologies(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        # Write a VTI file
        import vtkmodules.vtkIOXML as io
        ds = _make_cavity_dataset()
        writer = io.vtkXMLImageDataWriter()
        fpath = str(tmp_path / "cavity.vti")
        writer.SetFileName(fpath)
        writer.SetInputData(ds)
        writer.Write()

        result = await inspect_physics_impl(file_path=fpath)
        assert "field_topologies" in result
        assert len(result["field_topologies"]) >= 2  # U and p

    async def test_field_topology_has_range(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        import vtkmodules.vtkIOXML as io
        ds = _make_cavity_dataset()
        writer = io.vtkXMLImageDataWriter()
        fpath = str(tmp_path / "cavity.vti")
        writer.SetFileName(fpath)
        writer.SetInputData(ds)
        writer.Write()

        result = await inspect_physics_impl(file_path=fpath)
        topo = result["field_topologies"][0]
        assert "field_range" in topo
        assert "min" in topo["field_range"]

    async def test_case_context_without_case_dir(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        import vtkmodules.vtkIOXML as io
        ds = _make_cavity_dataset()
        writer = io.vtkXMLImageDataWriter()
        fpath = str(tmp_path / "cavity.vti")
        writer.SetFileName(fpath)
        writer.SetInputData(ds)
        writer.Write()

        result = await inspect_physics_impl(file_path=fpath)
        assert "case_context" in result
        # Without case_dir, should still have mesh quality
        assert result["case_context"]["mesh_quality"]["cell_count"] > 0

    async def test_extraction_time(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        import vtkmodules.vtkIOXML as io
        ds = _make_cavity_dataset()
        writer = io.vtkXMLImageDataWriter()
        fpath = str(tmp_path / "cavity.vti")
        writer.SetFileName(fpath)
        writer.SetInputData(ds)
        writer.Write()

        result = await inspect_physics_impl(file_path=fpath)
        assert "extraction_time_ms" in result
        assert result["extraction_time_ms"] > 0

    async def test_field_filter(self, tmp_path):
        from viznoir.tools.inspect_physics import inspect_physics_impl
        import vtkmodules.vtkIOXML as io
        ds = _make_cavity_dataset()
        writer = io.vtkXMLImageDataWriter()
        fpath = str(tmp_path / "cavity.vti")
        writer.SetFileName(fpath)
        writer.SetInputData(ds)
        writer.Write()

        result = await inspect_physics_impl(file_path=fpath, fields=["p"])
        assert len(result["field_topologies"]) == 1
        assert result["field_topologies"][0]["field_name"] == "p"
```

**Step 3: Write implementation**

```python
# src/viznoir/tools/inspect_physics.py
"""inspect_physics tool — structured physics data extraction for LLM storytelling."""
from __future__ import annotations

import time
from typing import Any

from viznoir.engine.readers import read_dataset
from viznoir.engine.topology import analyze_field_topology
from viznoir.context.generic import GenericContextParser
from viznoir.context.parser import get_default_registry


async def inspect_physics_impl(
    file_path: str,
    *,
    case_dir: str | None = None,
    fields: list[str] | None = None,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> dict[str, Any]:
    """Extract structured physics data from a simulation dataset."""
    t0 = time.perf_counter()

    dataset = read_dataset(file_path)

    # Discover available fields
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    all_fields = []
    for i in range(pd.GetNumberOfArrays()):
        all_fields.append(pd.GetArrayName(i))
    for i in range(cd.GetNumberOfArrays()):
        name = cd.GetArrayName(i)
        if name not in all_fields:
            all_fields.append(name)

    if fields:
        all_fields = [f for f in all_fields if f in fields]

    # L2: Field topology analysis
    topologies = []
    for field_name in all_fields:
        topo = analyze_field_topology(
            dataset, field_name,
            probe_lines=probe_lines,
            vortex_threshold=vortex_threshold,
        )
        topologies.append(topo.to_dict())

    # L3: Case context
    if case_dir:
        registry = get_default_registry()
        parser = registry.get_parser(case_dir)
        if parser and hasattr(parser, "parse_case_dir"):
            ctx = parser.parse_case_dir(case_dir)
        else:
            ctx = GenericContextParser().parse_dataset(dataset)
    else:
        ctx = GenericContextParser().parse_dataset(dataset)

    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "field_topologies": topologies,
        "case_context": ctx.to_dict(),
        "case_context_hint": None if case_dir else "Provide case_dir for full solver metadata (BC, transport, solver info)",
        "extraction_time_ms": round(elapsed, 1),
    }
```

Register in server.py:

```python
# In src/viznoir/server.py, add to tool registration section:
@mcp.tool()
async def inspect_physics(
    file_path: str,
    case_dir: str | None = None,
    fields: list[str] | None = None,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> dict[str, Any]:
    """Extract structured physics data for AI storytelling.

    Analyzes simulation data to extract:
    - L2 FieldTopology: vortex detection, critical points, centerline profiles, gradient stats
    - L3 CaseContext: boundary conditions, transport properties, solver info, mesh quality

    Returns structured JSON for LLM to build physics narratives.
    """
    from viznoir.tools.inspect_physics import inspect_physics_impl
    return await inspect_physics_impl(
        file_path, case_dir=case_dir, fields=fields,
        probe_lines=probe_lines, vortex_threshold=vortex_threshold,
    )
```

**Step 4-5: Run tests, commit**

```bash
git commit -m "feat: add inspect_physics MCP tool — L2 topology + L3 context integration"
```

---

### Task A-6: Documentation + Deprecation

**Owner:** cc (Lead) — depends on A-5

**Files:**
- Modify: `src/viznoir/server.py` (analyze_data deprecation notice)
- Modify: `CLAUDE.md` (tool count, architecture)
- Modify: `README.md` (tool count)
- Modify: `README.ko.md` (tool count)

**Changes:**
1. Add `[DEPRECATED — use inspect_physics]` to analyze_data docstring
2. Update tool count: 21 → 22
3. Add `context/` module to architecture diagram
4. Add `engine/topology.py` description

**Verification:**

```bash
ruff check src/ tests/
mypy src/viznoir/ --ignore-missing-imports
pytest --cov=viznoir --cov-report=term-missing -q
```

```bash
git commit -m "docs: update tool count to 22, add context module, deprecate analyze_data"
```

---

## Quality Gate (Lead responsibility)

After all tasks complete:

```bash
# Full test suite
pytest --cov=viznoir --cov-report=term-missing -q

# Verify coverage ≥80%
# Verify test count ≥ 1315 + ~200 new = ~1515

# Lint + type check
ruff check src/ tests/
mypy src/viznoir/ --ignore-missing-imports

# E2E: inspect_physics on real data
python -c "
import asyncio
from viznoir.tools.inspect_physics import inspect_physics_impl
# Use a test VTI file
result = asyncio.run(inspect_physics_impl('tests/fixtures/some_test.vti'))
print(f'Fields: {len(result[\"field_topologies\"])}')
print(f'Context: {result[\"case_context\"][\"mesh_quality\"][\"cell_count\"]} cells')
"
```
