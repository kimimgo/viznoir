# ME Autoresearch Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ME (Mechanical Engineering) computation primitives and autonomous analysis harness to viznoir, enabling AI agents to inspect FEA data and autonomously deliver engineering insights (safety factor, hotspots, failure criteria, deformation overlay).

**Architecture:** Two-layer approach inspired by Karpathy's autoresearch pattern. Layer 1 (Engine): `engine/mechanics.py` provides numpy-based tensor algebra, safety factor, failure criteria, hotspot detection as pure VTK filter functions. Layer 3 (Harness): Enhanced skills teach AI agents to compose these primitives autonomously. Two new MCP tools (`inspect_mechanics`, `deform_compare`) bridge engine to agent.

**Tech Stack:** Python 3.10+, VTK (vtk.util.numpy_support), numpy, FastMCP, Pydantic

---

## Agent Teams Assignment

Four parallel tracks with file ownership boundaries. **No file is owned by two teammates.**

| Track | Owner | Files | Depends On |
|-------|-------|-------|------------|
| **A: ME Engine** | `me-engine` | `engine/mechanics.py`, `tests/test_engine/test_mechanics.py` | — |
| **B: ME Physics & Context** | `me-physics` | `engine/physics.py` (lines 114-126 + append), `context/models.py` (append), `context/mechanics.py`, `tests/test_engine/test_physics_me.py`, `tests/test_context/test_mechanics_ctx.py` | — |
| **C: ME Tools** | `me-tools` | `tools/inspect_mechanics.py`, `tools/deform_compare.py`, `server.py` (tool registration), `tests/test_tools/test_inspect_mechanics.py`, `tests/test_tools/test_deform_compare.py` | A, B |
| **D: ME Harness** | `me-harness` | `.claude-plugin/skills/fea-workflow/SKILL.md`, `.claude-plugin/skills/cae-postprocess/SKILL.md`, `resources/catalog.py` (fea section), `presets/registry.py` (structural_fea), `prompts/guides.py` (fea section), `engine/filters.py` (registry append), `core/registry.py` (registry append) | A, C |

**Execution order:** A + B parallel → C → D

---

## Track A: ME Engine Primitives

### Task 1: Stress Tensor Decomposition

**Files:**
- Create: `src/viznoir/engine/mechanics.py`
- Test: `tests/test_engine/test_mechanics.py`

- [ ] **Step 1: Write failing tests for tensor decomposition**

```python
# tests/test_engine/test_mechanics.py
"""Tests for ME computation primitives."""

from __future__ import annotations

import numpy as np
import pytest


class TestStressTensorDecompose:
    """Test stress_tensor_decompose() — 6-component tensor to scalar fields."""

    def _make_dataset_with_tensor(self, components: list[list[float]]):
        """Create VTK unstructured grid with a 6-component stress tensor array."""
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        for i in range(len(components)):
            points.InsertNextPoint(float(i), 0.0, 0.0)
        grid.SetPoints(points)

        arr = numpy_to_vtk(np.array(components, dtype=np.float64))
        arr.SetName("stress_tensor")
        grid.GetPointData().AddArray(arr)
        return grid

    def test_von_mises_uniaxial(self):
        """Uniaxial tension: sigma_xx=100, rest=0 → von Mises = 100."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        # [sxx, syy, szz, sxy, syz, sxz]
        data = self._make_dataset_with_tensor([[100.0, 0, 0, 0, 0, 0]])
        result = stress_tensor_decompose(data, "stress_tensor")

        vm = result.GetPointData().GetArray("von_mises_stress")
        assert vm is not None
        assert abs(vm.GetValue(0) - 100.0) < 0.1

    def test_von_mises_pure_shear(self):
        """Pure shear: sxy=100 → von Mises = sqrt(3)*100 ≈ 173.2."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        data = self._make_dataset_with_tensor([[0, 0, 0, 100.0, 0, 0]])
        result = stress_tensor_decompose(data, "stress_tensor")

        vm = result.GetPointData().GetArray("von_mises_stress")
        assert abs(vm.GetValue(0) - 173.205) < 0.1

    def test_principal_stresses_sorted(self):
        """Principal stresses should be sorted: sigma1 >= sigma2 >= sigma3."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        data = self._make_dataset_with_tensor([[300, 100, 200, 0, 0, 0]])
        result = stress_tensor_decompose(data, "stress_tensor")

        s1 = result.GetPointData().GetArray("principal_stress_1").GetValue(0)
        s2 = result.GetPointData().GetArray("principal_stress_2").GetValue(0)
        s3 = result.GetPointData().GetArray("principal_stress_3").GetValue(0)
        assert s1 >= s2 >= s3
        assert abs(s1 - 300.0) < 0.1
        assert abs(s2 - 200.0) < 0.1
        assert abs(s3 - 100.0) < 0.1

    def test_tresca_stress(self):
        """Tresca = sigma1 - sigma3."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        data = self._make_dataset_with_tensor([[300, 100, 200, 0, 0, 0]])
        result = stress_tensor_decompose(data, "stress_tensor")

        tresca = result.GetPointData().GetArray("tresca_stress").GetValue(0)
        assert abs(tresca - 200.0) < 0.1

    def test_hydrostatic_stress(self):
        """Hydrostatic = (sxx + syy + szz) / 3."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        data = self._make_dataset_with_tensor([[300, 150, 60, 0, 0, 0]])
        result = stress_tensor_decompose(data, "stress_tensor")

        hydro = result.GetPointData().GetArray("hydrostatic_stress").GetValue(0)
        assert abs(hydro - 170.0) < 0.1

    def test_output_arrays_all_present(self):
        """All 7 output arrays should be present."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        data = self._make_dataset_with_tensor([[100, 50, 25, 10, 5, 3]])
        result = stress_tensor_decompose(data, "stress_tensor")

        expected = [
            "von_mises_stress", "tresca_stress",
            "principal_stress_1", "principal_stress_2", "principal_stress_3",
            "hydrostatic_stress", "deviatoric_stress",
        ]
        for name in expected:
            assert result.GetPointData().GetArray(name) is not None, f"Missing: {name}"

    def test_multi_point(self):
        """Works with multiple points."""
        from viznoir.engine.mechanics import stress_tensor_decompose

        data = self._make_dataset_with_tensor([
            [100, 0, 0, 0, 0, 0],
            [0, 200, 0, 0, 0, 0],
            [50, 50, 50, 0, 0, 0],
        ])
        result = stress_tensor_decompose(data, "stress_tensor")

        vm = result.GetPointData().GetArray("von_mises_stress")
        assert vm.GetNumberOfTuples() == 3

    def test_invalid_tensor_field_raises(self):
        """Non-existent field raises FieldNotFoundError."""
        from viznoir.engine.mechanics import stress_tensor_decompose
        from viznoir.errors import FieldNotFoundError

        data = self._make_dataset_with_tensor([[100, 0, 0, 0, 0, 0]])
        with pytest.raises(FieldNotFoundError):
            stress_tensor_decompose(data, "nonexistent")

    def test_wrong_component_count_raises(self):
        """Field with != 6 components raises ValueError."""
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        from viznoir.engine.mechanics import stress_tensor_decompose

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        points.InsertNextPoint(0, 0, 0)
        grid.SetPoints(points)
        arr = numpy_to_vtk(np.array([[1.0, 2.0, 3.0]]))
        arr.SetName("bad_tensor")
        grid.GetPointData().AddArray(arr)

        with pytest.raises(ValueError, match="6 components"):
            stress_tensor_decompose(grid, "bad_tensor")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine/test_mechanics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'viznoir.engine.mechanics'`

- [ ] **Step 3: Implement stress_tensor_decompose**

```python
# src/viznoir/engine/mechanics.py
"""ME computation primitives — tensor algebra, safety factor, failure criteria, hotspot detection.

Pure VTK + numpy analysis for mechanical engineering post-processing.
All functions follow the engine/filters.py pattern: VTK dataset in → VTK dataset out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from viznoir.errors import FieldNotFoundError

if TYPE_CHECKING:
    import vtk

__all__ = [
    "stress_tensor_decompose",
    "safety_factor",
    "failure_criterion",
    "hotspot_detect",
    "deform_overlay",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_array(
    dataset: vtk.vtkDataObject,
    field_name: str,
) -> tuple[Any, str]:
    """Get VTK array from point or cell data. Returns (vtk_array, association).

    Raises FieldNotFoundError if not found.
    """
    pd = dataset.GetPointData()
    arr = pd.GetArray(field_name)
    if arr is not None:
        return arr, "point"

    cd = dataset.GetCellData()
    arr = cd.GetArray(field_name)
    if arr is not None:
        return arr, "cell"

    msg = f"Field '{field_name}' not found in point or cell data"
    raise FieldNotFoundError(msg)


def _add_array(
    dataset: vtk.vtkDataObject,
    np_array: np.ndarray,
    name: str,
    association: str,
) -> None:
    """Add a numpy array to VTK dataset as named array."""
    from vtk.util.numpy_support import numpy_to_vtk

    vtk_arr = numpy_to_vtk(np_array.astype(np.float64), deep=True)
    vtk_arr.SetName(name)

    if association == "point":
        dataset.GetPointData().AddArray(vtk_arr)
    else:
        dataset.GetCellData().AddArray(vtk_arr)


# ---------------------------------------------------------------------------
# Tensor decomposition
# ---------------------------------------------------------------------------


def stress_tensor_decompose(
    data: vtk.vtkDataObject,
    tensor_field: str,
) -> vtk.vtkDataObject:
    """Decompose 6-component stress tensor into scalar fields.

    Input tensor format: [sxx, syy, szz, sxy, syz, sxz] (Voigt notation).

    Output arrays added to dataset:
    - von_mises_stress: equivalent stress
    - tresca_stress: max shear stress criterion
    - principal_stress_1/2/3: eigenvalues sorted descending
    - hydrostatic_stress: mean normal stress
    - deviatoric_stress: von Mises of deviatoric part (same as von Mises)

    Args:
        data: VTK dataset with a 6-component tensor array.
        tensor_field: Name of the stress tensor array.

    Returns:
        Same dataset with 7 new scalar arrays added.

    Raises:
        FieldNotFoundError: If tensor_field not found.
        ValueError: If array doesn't have exactly 6 components.
    """
    from vtk.util.numpy_support import vtk_to_numpy

    vtk_arr, assoc = _get_array(data, tensor_field)

    if vtk_arr.GetNumberOfComponents() != 6:
        msg = f"Stress tensor '{tensor_field}' must have 6 components, got {vtk_arr.GetNumberOfComponents()}"
        raise ValueError(msg)

    t = vtk_to_numpy(vtk_arr)  # shape: (N, 6)
    sxx, syy, szz, sxy, syz, sxz = t[:, 0], t[:, 1], t[:, 2], t[:, 3], t[:, 4], t[:, 5]

    # Von Mises
    vm = np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy**2 + syz**2 + sxz**2)
    )

    # Hydrostatic
    hydro = (sxx + syy + szz) / 3.0

    # Principal stresses via eigenvalue decomposition
    n = len(sxx)
    principals = np.empty((n, 3), dtype=np.float64)
    for i in range(n):
        mat = np.array([
            [sxx[i], sxy[i], sxz[i]],
            [sxy[i], syy[i], syz[i]],
            [sxz[i], syz[i], szz[i]],
        ])
        eigvals = np.linalg.eigvalsh(mat)
        principals[i] = np.sort(eigvals)[::-1]  # descending

    s1, s2, s3 = principals[:, 0], principals[:, 1], principals[:, 2]

    # Tresca
    tresca = s1 - s3

    # Add all arrays
    _add_array(data, vm, "von_mises_stress", assoc)
    _add_array(data, tresca, "tresca_stress", assoc)
    _add_array(data, s1, "principal_stress_1", assoc)
    _add_array(data, s2, "principal_stress_2", assoc)
    _add_array(data, s3, "principal_stress_3", assoc)
    _add_array(data, hydro, "hydrostatic_stress", assoc)
    _add_array(data, vm, "deviatoric_stress", assoc)  # same as von Mises for stress

    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine/test_mechanics.py::TestStressTensorDecompose -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/engine/mechanics.py tests/test_engine/test_mechanics.py
git commit -m "feat(engine): add stress tensor decomposition primitives"
```

---

### Task 2: Safety Factor & Failure Criteria

**Files:**
- Modify: `src/viznoir/engine/mechanics.py`
- Modify: `tests/test_engine/test_mechanics.py`

- [ ] **Step 1: Write failing tests for safety_factor**

```python
# Append to tests/test_engine/test_mechanics.py

class TestSafetyFactor:
    """Test safety_factor() — yield/stress ratio as new array."""

    def _make_dataset_with_scalar(self, values: list[float], name: str = "von_mises"):
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        for i in range(len(values)):
            points.InsertNextPoint(float(i), 0.0, 0.0)
        grid.SetPoints(points)
        arr = numpy_to_vtk(np.array(values, dtype=np.float64))
        arr.SetName(name)
        grid.GetPointData().AddArray(arr)
        return grid

    def test_basic_sf(self):
        """SF = yield / stress → 250/100 = 2.5."""
        from viznoir.engine.mechanics import safety_factor

        data = self._make_dataset_with_scalar([100.0, 200.0, 250.0])
        result = safety_factor(data, "von_mises", yield_strength=250.0)

        sf = result.GetPointData().GetArray("safety_factor")
        assert sf is not None
        assert abs(sf.GetValue(0) - 2.5) < 0.01
        assert abs(sf.GetValue(1) - 1.25) < 0.01
        assert abs(sf.GetValue(2) - 1.0) < 0.01

    def test_sf_clamps_at_zero_stress(self):
        """Zero stress → SF capped at 999.0 (avoid inf)."""
        from viznoir.engine.mechanics import safety_factor

        data = self._make_dataset_with_scalar([0.0, 50.0])
        result = safety_factor(data, "von_mises", yield_strength=250.0)

        sf = result.GetPointData().GetArray("safety_factor")
        assert sf.GetValue(0) == 999.0

    def test_sf_custom_result_name(self):
        """Custom result_name parameter."""
        from viznoir.engine.mechanics import safety_factor

        data = self._make_dataset_with_scalar([100.0])
        result = safety_factor(data, "von_mises", yield_strength=250.0, result_name="SF")

        assert result.GetPointData().GetArray("SF") is not None

    def test_sf_field_not_found(self):
        """Missing field raises FieldNotFoundError."""
        from viznoir.engine.mechanics import safety_factor
        from viznoir.errors import FieldNotFoundError

        data = self._make_dataset_with_scalar([100.0])
        with pytest.raises(FieldNotFoundError):
            safety_factor(data, "nonexistent", yield_strength=250.0)


class TestFailureCriterion:
    """Test failure_criterion() — multi-criteria failure evaluation."""

    def _make_dataset_with_tensor(self, components: list[list[float]]):
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        for i in range(len(components)):
            points.InsertNextPoint(float(i), 0.0, 0.0)
        grid.SetPoints(points)
        arr = numpy_to_vtk(np.array(components, dtype=np.float64))
        arr.SetName("stress_tensor")
        grid.GetPointData().AddArray(arr)
        return grid

    def test_von_mises_criterion(self):
        """von_mises criterion: ratio = von_mises / yield."""
        from viznoir.engine.mechanics import failure_criterion

        data = self._make_dataset_with_tensor([[200, 0, 0, 0, 0, 0]])
        result = failure_criterion(data, "stress_tensor", criterion="von_mises", yield_strength=250.0)

        ratio = result.GetPointData().GetArray("failure_ratio")
        assert ratio is not None
        assert abs(ratio.GetValue(0) - 200.0 / 250.0) < 0.01

    def test_tresca_criterion(self):
        """tresca criterion: ratio = tresca / yield."""
        from viznoir.engine.mechanics import failure_criterion

        data = self._make_dataset_with_tensor([[300, 100, 200, 0, 0, 0]])
        result = failure_criterion(data, "stress_tensor", criterion="tresca", yield_strength=250.0)

        ratio = result.GetPointData().GetArray("failure_ratio")
        # Tresca = 300 - 100 = 200, ratio = 200/250 = 0.8
        assert abs(ratio.GetValue(0) - 0.8) < 0.01

    def test_max_principal_criterion(self):
        """max_principal criterion: ratio = sigma1 / yield."""
        from viznoir.engine.mechanics import failure_criterion

        data = self._make_dataset_with_tensor([[300, 100, 200, 0, 0, 0]])
        result = failure_criterion(data, "stress_tensor", criterion="max_principal", yield_strength=250.0)

        ratio = result.GetPointData().GetArray("failure_ratio")
        assert abs(ratio.GetValue(0) - 300.0 / 250.0) < 0.01

    def test_failed_regions_array(self):
        """failed_region array: 1 where ratio > 1.0, 0 otherwise."""
        from viznoir.engine.mechanics import failure_criterion

        data = self._make_dataset_with_tensor([
            [200, 0, 0, 0, 0, 0],  # VM=200, ratio=0.8 → safe
            [300, 0, 0, 0, 0, 0],  # VM=300, ratio=1.2 → failed
        ])
        result = failure_criterion(data, "stress_tensor", criterion="von_mises", yield_strength=250.0)

        failed = result.GetPointData().GetArray("failed_region")
        assert failed.GetValue(0) == 0.0
        assert failed.GetValue(1) == 1.0

    def test_unknown_criterion_raises(self):
        """Unknown criterion name raises ValueError."""
        from viznoir.engine.mechanics import failure_criterion

        data = self._make_dataset_with_tensor([[100, 0, 0, 0, 0, 0]])
        with pytest.raises(ValueError, match="criterion"):
            failure_criterion(data, "stress_tensor", criterion="unknown", yield_strength=250.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine/test_mechanics.py::TestSafetyFactor tests/test_engine/test_mechanics.py::TestFailureCriterion -v`
Expected: FAIL — `ImportError: cannot import name 'safety_factor'`

- [ ] **Step 3: Implement safety_factor and failure_criterion**

Append to `src/viznoir/engine/mechanics.py`:

```python
# ---------------------------------------------------------------------------
# Safety factor
# ---------------------------------------------------------------------------


def safety_factor(
    data: vtk.vtkDataObject,
    stress_field: str,
    yield_strength: float,
    *,
    result_name: str = "safety_factor",
) -> vtk.vtkDataObject:
    """Compute safety factor array: SF = yield_strength / stress.

    Args:
        data: VTK dataset with a scalar stress array.
        stress_field: Name of the stress array (e.g., "von_mises_stress").
        yield_strength: Material yield strength in same units as stress.
        result_name: Name for the output SF array.

    Returns:
        Same dataset with safety factor array added.
    """
    from vtk.util.numpy_support import vtk_to_numpy

    vtk_arr, assoc = _get_array(data, stress_field)
    stress = vtk_to_numpy(vtk_arr).flatten()

    sf = np.where(stress > 0, yield_strength / stress, 999.0)
    _add_array(data, sf, result_name, assoc)
    return data


# ---------------------------------------------------------------------------
# Failure criteria
# ---------------------------------------------------------------------------

_CRITERIA = {"von_mises", "tresca", "max_principal", "drucker_prager"}


def failure_criterion(
    data: vtk.vtkDataObject,
    tensor_field: str,
    criterion: str,
    yield_strength: float,
    *,
    friction_angle: float = 30.0,
) -> vtk.vtkDataObject:
    """Evaluate failure criterion and add failure_ratio + failed_region arrays.

    failure_ratio = effective_stress / yield_strength
    failed_region = 1 where ratio > 1.0, else 0

    Args:
        data: VTK dataset with 6-component stress tensor.
        tensor_field: Name of the tensor array.
        criterion: One of "von_mises", "tresca", "max_principal", "drucker_prager".
        yield_strength: Material yield strength.
        friction_angle: Friction angle in degrees (for Drucker-Prager only).

    Returns:
        Dataset with failure_ratio and failed_region arrays.
    """
    if criterion not in _CRITERIA:
        msg = f"Unknown criterion '{criterion}'. Choose from: {sorted(_CRITERIA)}"
        raise ValueError(msg)

    # Decompose tensor first (adds principal stresses etc.)
    data = stress_tensor_decompose(data, tensor_field)

    from vtk.util.numpy_support import vtk_to_numpy

    if criterion == "von_mises":
        effective = vtk_to_numpy(data.GetPointData().GetArray("von_mises_stress") or data.GetCellData().GetArray("von_mises_stress")).flatten()
    elif criterion == "tresca":
        effective = vtk_to_numpy(data.GetPointData().GetArray("tresca_stress") or data.GetCellData().GetArray("tresca_stress")).flatten()
    elif criterion == "max_principal":
        effective = vtk_to_numpy(data.GetPointData().GetArray("principal_stress_1") or data.GetCellData().GetArray("principal_stress_1")).flatten()
    elif criterion == "drucker_prager":
        vm_arr = data.GetPointData().GetArray("von_mises_stress") or data.GetCellData().GetArray("von_mises_stress")
        hydro_arr = data.GetPointData().GetArray("hydrostatic_stress") or data.GetCellData().GetArray("hydrostatic_stress")
        vm = vtk_to_numpy(vm_arr).flatten()
        hydro = vtk_to_numpy(hydro_arr).flatten()
        phi = np.radians(friction_angle)
        k = 6.0 * np.sin(phi) / (3.0 - np.sin(phi))
        effective = vm + k * hydro

    _, assoc = _get_array(data, tensor_field)
    ratio = effective / yield_strength
    failed = np.where(ratio > 1.0, 1.0, 0.0)

    _add_array(data, ratio, "failure_ratio", assoc)
    _add_array(data, failed, "failed_region", assoc)
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine/test_mechanics.py -v`
Expected: All tests PASS (10 tensor + 9 SF/failure = 19 total)

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/engine/mechanics.py tests/test_engine/test_mechanics.py
git commit -m "feat(engine): add safety factor and failure criteria"
```

---

### Task 3: Hotspot Detection & Deformation Overlay

**Files:**
- Modify: `src/viznoir/engine/mechanics.py`
- Modify: `tests/test_engine/test_mechanics.py`

- [ ] **Step 1: Write failing tests for hotspot_detect and deform_overlay**

```python
# Append to tests/test_engine/test_mechanics.py
from dataclasses import dataclass


class TestHotspotDetect:
    """Test hotspot_detect() — find extreme value locations."""

    def _make_grid_with_field(self, coords_values: list[tuple[tuple, float]], name: str = "stress"):
        """Create grid with known point locations and scalar values."""
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        values = []
        for (x, y, z), val in coords_values:
            points.InsertNextPoint(x, y, z)
            values.append(val)
        grid.SetPoints(points)
        arr = numpy_to_vtk(np.array(values, dtype=np.float64))
        arr.SetName(name)
        grid.GetPointData().AddArray(arr)
        return grid

    def test_finds_max_hotspot(self):
        from viznoir.engine.mechanics import hotspot_detect

        data = self._make_grid_with_field([
            ((0, 0, 0), 100.0),
            ((1, 0, 0), 500.0),  # max
            ((2, 0, 0), 200.0),
        ])
        spots = hotspot_detect(data, "stress", top_n=1)
        assert len(spots) == 1
        assert abs(spots[0]["value"] - 500.0) < 0.1
        assert spots[0]["position"] == [1.0, 0.0, 0.0]

    def test_top_n_sorted_descending(self):
        from viznoir.engine.mechanics import hotspot_detect

        data = self._make_grid_with_field([
            ((0, 0, 0), 100.0),
            ((1, 0, 0), 500.0),
            ((2, 0, 0), 300.0),
            ((3, 0, 0), 400.0),
        ])
        spots = hotspot_detect(data, "stress", top_n=3)
        assert len(spots) == 3
        assert spots[0]["value"] > spots[1]["value"] > spots[2]["value"]

    def test_returns_point_index(self):
        from viznoir.engine.mechanics import hotspot_detect

        data = self._make_grid_with_field([
            ((0, 0, 0), 100.0),
            ((1, 0, 0), 500.0),
        ])
        spots = hotspot_detect(data, "stress", top_n=1)
        assert spots[0]["point_index"] == 1

    def test_top_n_clamped_to_points(self):
        from viznoir.engine.mechanics import hotspot_detect

        data = self._make_grid_with_field([((0, 0, 0), 10.0), ((1, 0, 0), 20.0)])
        spots = hotspot_detect(data, "stress", top_n=100)
        assert len(spots) == 2


class TestDeformOverlay:
    """Test deform_overlay() — warped + wireframe datasets."""

    def _make_grid_with_displacement(self):
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        points.InsertNextPoint(0, 0, 0)
        points.InsertNextPoint(1, 0, 0)
        points.InsertNextPoint(0.5, 1, 0)
        grid.SetPoints(points)

        # Add a triangle cell
        tri = vtk.vtkTriangle()
        tri.GetPointIds().SetId(0, 0)
        tri.GetPointIds().SetId(1, 1)
        tri.GetPointIds().SetId(2, 2)
        grid.InsertNextCell(tri.GetCellType(), tri.GetPointIds())

        disp = numpy_to_vtk(np.array([[0.1, 0.0, 0.0], [0.2, 0.0, 0.0], [0.15, 0.05, 0.0]], dtype=np.float64))
        disp.SetName("displacement")
        grid.GetPointData().AddArray(disp)
        return grid

    def test_returns_two_datasets(self):
        from viznoir.engine.mechanics import deform_overlay

        data = self._make_grid_with_displacement()
        warped, wireframe = deform_overlay(data, "displacement", scale_factor=10.0)
        assert warped is not None
        assert wireframe is not None

    def test_warped_points_differ(self):
        from viznoir.engine.mechanics import deform_overlay

        data = self._make_grid_with_displacement()
        warped, wireframe = deform_overlay(data, "displacement", scale_factor=10.0)

        # Warped point 0 should be shifted by 10 * 0.1 = 1.0 in x
        wp = warped.GetPoint(0)
        op = wireframe.GetPoint(0)
        assert abs(wp[0] - op[0]) > 0.5  # significant difference

    def test_wireframe_preserves_original(self):
        from viznoir.engine.mechanics import deform_overlay

        data = self._make_grid_with_displacement()
        _, wireframe = deform_overlay(data, "displacement", scale_factor=10.0)

        # Original point 0 should be at (0, 0, 0)
        p = wireframe.GetPoint(0)
        assert abs(p[0]) < 0.01 and abs(p[1]) < 0.01
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine/test_mechanics.py::TestHotspotDetect tests/test_engine/test_mechanics.py::TestDeformOverlay -v`
Expected: FAIL — `ImportError: cannot import name 'hotspot_detect'`

- [ ] **Step 3: Implement hotspot_detect and deform_overlay**

Append to `src/viznoir/engine/mechanics.py`:

```python
# ---------------------------------------------------------------------------
# Hotspot detection
# ---------------------------------------------------------------------------


def hotspot_detect(
    data: vtk.vtkDataObject,
    field_name: str,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Find top-N extreme value locations in a scalar field.

    Returns list of dicts sorted by value descending:
    [{"point_index": int, "position": [x,y,z], "value": float}, ...]
    """
    from vtk.util.numpy_support import vtk_to_numpy

    vtk_arr, _ = _get_array(data, field_name)
    values = vtk_to_numpy(vtk_arr).flatten()

    n = min(top_n, len(values))
    indices = np.argpartition(values, -n)[-n:]
    indices = indices[np.argsort(values[indices])[::-1]]

    spots = []
    for idx in indices:
        pt = list(data.GetPoint(int(idx)))
        spots.append({
            "point_index": int(idx),
            "position": [round(c, 6) for c in pt],
            "value": float(values[idx]),
        })
    return spots


# ---------------------------------------------------------------------------
# Deformation overlay
# ---------------------------------------------------------------------------


def deform_overlay(
    data: vtk.vtkDataObject,
    displacement_field: str,
    scale_factor: float = 1.0,
) -> tuple[vtk.vtkDataObject, vtk.vtkDataObject]:
    """Create warped + original wireframe datasets for overlay visualization.

    Args:
        data: VTK dataset with displacement vector field.
        displacement_field: Name of 3-component displacement array.
        scale_factor: Deformation magnification factor.

    Returns:
        (warped_dataset, original_dataset) — both are independent copies.
    """
    import vtk

    # Wireframe = deep copy of original
    wireframe = data.NewInstance()
    wireframe.DeepCopy(data)

    # Warped = WarpByVector applied
    warp = vtk.vtkWarpVector()
    warp.SetInputData(data)
    warp.SetInputArrayToProcess(0, 0, 0, 0, displacement_field)
    warp.SetScaleFactor(scale_factor)
    warp.Update()
    warped = warp.GetOutput()

    return warped, wireframe
```

- [ ] **Step 4: Run all mechanics tests**

Run: `pytest tests/test_engine/test_mechanics.py -v`
Expected: All 26 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/engine/mechanics.py tests/test_engine/test_mechanics.py
git commit -m "feat(engine): add hotspot detection and deformation overlay"
```

---

## Track B: ME Physics & Context

### Task 4: Extend Physics Detection with ME Patterns

**Files:**
- Modify: `src/viznoir/engine/physics.py` (append patterns after line 126)
- Create: `tests/test_engine/test_physics_me.py`

- [ ] **Step 1: Write failing tests for ME physics patterns**

```python
# tests/test_engine/test_physics_me.py
"""Tests for ME-specific physics detection patterns."""

from __future__ import annotations

import pytest

from viznoir.engine.physics import detect_physics


class TestMEPhysicsDetection:
    """ME field patterns → correct physics type."""

    @pytest.mark.parametrize("name", [
        "strain", "epsilon", "exx", "eyy", "ezz", "exy",
        "principal_strain", "plastic_strain", "elastic_strain",
    ])
    def test_strain_fields(self, name: str):
        p = detect_physics(name)
        assert p.name == "strain"

    @pytest.mark.parametrize("name", [
        "principal_stress_1", "principal_stress_2", "principal_stress_3",
        "sigma_1", "sigma_2", "sigma_3",
    ])
    def test_principal_stress_fields(self, name: str):
        p = detect_physics(name)
        assert p.name == "principal_stress"

    @pytest.mark.parametrize("name", [
        "safety_factor", "SF", "factor_of_safety",
    ])
    def test_safety_factor_fields(self, name: str):
        p = detect_physics(name)
        assert p.name == "safety_factor"

    @pytest.mark.parametrize("name", [
        "failure_ratio", "failure_index", "failed_region",
    ])
    def test_failure_fields(self, name: str):
        p = detect_physics(name)
        assert p.name == "failure"

    @pytest.mark.parametrize("name", [
        "tresca_stress", "tresca",
    ])
    def test_tresca_fields(self, name: str):
        p = detect_physics(name)
        assert p.name == "tresca"

    @pytest.mark.parametrize("name", [
        "hydrostatic_stress", "mean_stress",
    ])
    def test_hydrostatic_fields(self, name: str):
        p = detect_physics(name)
        assert p.name == "hydrostatic"

    def test_stress_pattern_still_works(self):
        """Original stress patterns unchanged."""
        p = detect_physics("von_mises")
        assert p.name == "stress"

    def test_displacement_still_works(self):
        """Original displacement patterns unchanged."""
        p = detect_physics("displacement")
        assert p.name == "displacement"
        assert p.warp is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine/test_physics_me.py -v`
Expected: FAIL — strain/principal_stress/safety_factor patterns not recognized

- [ ] **Step 3: Add ME patterns to physics.py**

Insert after the stress pattern (line 127) and before the displacement pattern (line 128) in `_PHYSICS_PATTERNS`:

```python
    # ME: Strain fields
    (
        r"^strain$|^epsilon$|^e[xyz]{2}$|^exy$|^eyz$|^exz$|^principal_strain|^plastic_strain|^elastic_strain",
        {
            "name": "strain",
            "category": "scalar",
            "colormap": "coolwarm",
            "diverging": True,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    # ME: Principal stress
    (
        r"^principal_stress_[123]$|^sigma_[123]$",
        {
            "name": "principal_stress",
            "category": "scalar",
            "colormap": "Cool to Warm",
            "diverging": True,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    # ME: Safety factor
    (
        r"^safety_factor$|^SF$|^factor_of_safety$",
        {
            "name": "safety_factor",
            "category": "scalar",
            "colormap": "RdYlGn",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    # ME: Failure criterion
    (
        r"^failure_ratio$|^failure_index$|^failed_region$",
        {
            "name": "failure",
            "category": "scalar",
            "colormap": "Reds",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    # ME: Tresca
    (
        r"^tresca_stress$|^tresca$",
        {
            "name": "tresca",
            "category": "scalar",
            "colormap": "Cool to Warm",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    # ME: Hydrostatic stress
    (
        r"^hydrostatic_stress$|^mean_stress$",
        {
            "name": "hydrostatic",
            "category": "scalar",
            "colormap": "coolwarm",
            "diverging": True,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_engine/test_physics_me.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/engine/physics.py tests/test_engine/test_physics_me.py
git commit -m "feat(physics): add ME field patterns (strain, principal, SF, failure, tresca, hydrostatic)"
```

---

### Task 5: ME Context Models and Parser

**Files:**
- Modify: `src/viznoir/context/models.py` (append new dataclasses)
- Create: `src/viznoir/context/mechanics.py`
- Create: `tests/test_context/test_mechanics_ctx.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_context/test_mechanics_ctx.py
"""Tests for ME context parser."""

from __future__ import annotations

import numpy as np
import pytest


class TestMEContextModels:
    """Test ME dataclass models."""

    def test_material_property_creation(self):
        from viznoir.context.models import MaterialProperty

        mat = MaterialProperty(
            name="Steel A36",
            yield_strength=250e6,
            ultimate_strength=400e6,
            elastic_modulus=200e9,
            poisson_ratio=0.3,
        )
        assert mat.yield_strength == 250e6
        assert mat.poisson_ratio == 0.3

    def test_me_analysis_result_creation(self):
        from viznoir.context.models import MEAnalysisResult

        result = MEAnalysisResult(
            max_von_mises=342e6,
            max_displacement=0.0023,
            min_safety_factor=1.46,
            hotspot_count=2,
            failed_volume_fraction=0.0,
            analysis_type="static",
        )
        assert result.min_safety_factor == 1.46

    def test_me_analysis_to_dict(self):
        from viznoir.context.models import MEAnalysisResult

        result = MEAnalysisResult(
            max_von_mises=100.0,
            max_displacement=0.001,
            min_safety_factor=2.5,
            hotspot_count=1,
            failed_volume_fraction=0.0,
            analysis_type="static",
        )
        d = result.to_dict()
        assert d["min_safety_factor"] == 2.5
        assert "analysis_type" in d


class TestMEContextParser:
    """Test MEContextParser — auto-detect ME fields and compute derived quantities."""

    def _make_dataset_with_stress(self, von_mises_values: list[float]):
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        for i, v in enumerate(von_mises_values):
            points.InsertNextPoint(float(i), 0, 0)
        grid.SetPoints(points)
        arr = numpy_to_vtk(np.array(von_mises_values, dtype=np.float64))
        arr.SetName("von_mises_stress")
        grid.GetPointData().AddArray(arr)
        return grid

    def test_detects_stress_field(self):
        from viznoir.context.mechanics import MEContextParser

        data = self._make_dataset_with_stress([100.0, 200.0, 300.0])
        parser = MEContextParser()
        result = parser.analyze(data)
        assert result["max_von_mises"] == pytest.approx(300.0)

    def test_computes_sf_with_material(self):
        from viznoir.context.mechanics import MEContextParser

        data = self._make_dataset_with_stress([100.0, 200.0, 300.0])
        parser = MEContextParser(yield_strength=250.0)
        result = parser.analyze(data)
        assert result["min_safety_factor"] == pytest.approx(250.0 / 300.0, rel=0.01)

    def test_counts_hotspots(self):
        from viznoir.context.mechanics import MEContextParser

        data = self._make_dataset_with_stress([100.0, 200.0, 300.0, 280.0, 310.0])
        parser = MEContextParser(yield_strength=250.0)
        result = parser.analyze(data)
        assert result["hotspot_count"] >= 1

    def test_summary_text(self):
        from viznoir.context.mechanics import MEContextParser

        data = self._make_dataset_with_stress([100.0, 250.0])
        parser = MEContextParser(yield_strength=300.0)
        result = parser.analyze(data)
        assert isinstance(result["summary"], str)
        assert "250" in result["summary"]  # max stress value mentioned
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context/test_mechanics_ctx.py -v`
Expected: FAIL

- [ ] **Step 3: Add MaterialProperty and MEAnalysisResult to context/models.py**

Append to `src/viznoir/context/models.py`:

```python
@dataclass
class MaterialProperty:
    """Material mechanical properties for failure analysis."""

    name: str
    yield_strength: float  # Pa
    ultimate_strength: float | None = None
    elastic_modulus: float | None = None
    poisson_ratio: float | None = None
    density: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class MEAnalysisResult:
    """Summary of ME analysis results."""

    max_von_mises: float
    max_displacement: float | None = None
    min_safety_factor: float | None = None
    hotspot_count: int = 0
    failed_volume_fraction: float = 0.0
    analysis_type: str = "static"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Implement MEContextParser**

```python
# src/viznoir/context/mechanics.py
"""ME context parser — auto-detect ME fields and compute engineering metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import vtk

__all__ = ["MEContextParser"]


class MEContextParser:
    """Analyze VTK dataset for mechanical engineering fields.

    Auto-detects stress, displacement, strain fields and computes
    derived engineering metrics (safety factor, hotspots, failure regions).
    """

    # Known field name patterns (lowercase → category)
    _STRESS_PATTERNS = {"von_mises_stress", "von_mises", "vonmises", "stress", "sigma", "s"}
    _DISP_PATTERNS = {"displacement", "disp", "deformation", "d", "u"}

    def __init__(self, yield_strength: float | None = None):
        self._yield = yield_strength

    def analyze(self, dataset: vtk.vtkDataObject) -> dict[str, Any]:
        """Run ME analysis on dataset. Returns dict with metrics + summary."""
        from vtk.util.numpy_support import vtk_to_numpy

        pd = dataset.GetPointData()
        cd = dataset.GetCellData()

        # Discover fields
        stress_field = self._find_field(pd, cd, self._STRESS_PATTERNS)
        disp_field = self._find_field(pd, cd, self._DISP_PATTERNS)

        result: dict[str, Any] = {"analysis_type": "static"}

        # Stress analysis
        if stress_field:
            arr = pd.GetArray(stress_field) or cd.GetArray(stress_field)
            values = vtk_to_numpy(arr).flatten()
            result["max_von_mises"] = float(np.max(values))
            result["mean_von_mises"] = float(np.mean(values))

            # Safety factor
            if self._yield is not None:
                max_stress = result["max_von_mises"]
                result["min_safety_factor"] = self._yield / max_stress if max_stress > 0 else 999.0
                result["failed_volume_fraction"] = float(np.sum(values > self._yield) / len(values))

            # Hotspots (top 5 by value)
            top_n = min(5, len(values))
            top_indices = np.argpartition(values, -top_n)[-top_n:]
            result["hotspot_count"] = top_n
            result["hotspots"] = [
                {
                    "point_index": int(idx),
                    "position": list(dataset.GetPoint(int(idx))),
                    "value": float(values[idx]),
                }
                for idx in top_indices[np.argsort(values[top_indices])[::-1]]
            ]

        # Displacement analysis
        if disp_field:
            arr = pd.GetArray(disp_field) or cd.GetArray(disp_field)
            disp_data = vtk_to_numpy(arr)
            if disp_data.ndim > 1:
                mag = np.linalg.norm(disp_data, axis=1)
            else:
                mag = np.abs(disp_data)
            result["max_displacement"] = float(np.max(mag))
            result["mean_displacement"] = float(np.mean(mag))

        # Summary text
        result["summary"] = self._build_summary(result)
        return result

    def _find_field(self, pd, cd, patterns: set[str]) -> str | None:
        """Find first matching field name in point or cell data."""
        for source in [pd, cd]:
            for i in range(source.GetNumberOfArrays()):
                name = source.GetArrayName(i)
                if name and name.lower() in patterns:
                    return name
        return None

    def _build_summary(self, result: dict[str, Any]) -> str:
        """Generate human-readable engineering summary."""
        parts = []

        if "max_von_mises" in result:
            parts.append(f"Max von Mises stress: {result['max_von_mises']:.2f}")

        if "max_displacement" in result:
            parts.append(f"Max displacement: {result['max_displacement']:.6f}")

        if "min_safety_factor" in result:
            sf = result["min_safety_factor"]
            status = "SAFE" if sf > 1.5 else "WARNING" if sf > 1.0 else "FAILURE"
            parts.append(f"Min safety factor: {sf:.2f} ({status})")

        if result.get("failed_volume_fraction", 0) > 0:
            pct = result["failed_volume_fraction"] * 100
            parts.append(f"Failed volume: {pct:.1f}%")

        return ". ".join(parts) + "." if parts else "No ME fields detected."
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_context/test_mechanics_ctx.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/context/models.py src/viznoir/context/mechanics.py tests/test_context/test_mechanics_ctx.py
git commit -m "feat(context): add ME context parser with material props and analysis results"
```

---

## Track C: ME MCP Tools

### Task 6: inspect_mechanics MCP Tool

**Files:**
- Create: `src/viznoir/tools/inspect_mechanics.py`
- Modify: `src/viznoir/server.py` (add tool registration)
- Create: `tests/test_tools/test_inspect_mechanics.py`

**Depends on:** Tasks 1-5 (engine/mechanics.py + context/mechanics.py)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tools/test_inspect_mechanics.py
"""Tests for inspect_mechanics MCP tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


class TestInspectMechanicsImpl:
    """Test inspect_mechanics_impl function."""

    def _make_fea_dataset(self):
        """Create dataset with stress tensor + displacement."""
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        n = 10
        for i in range(n):
            points.InsertNextPoint(float(i), 0, 0)
        grid.SetPoints(points)

        # 6-component stress tensor
        tensor_vals = np.random.uniform(50, 300, (n, 6))
        tensor = numpy_to_vtk(tensor_vals)
        tensor.SetName("stress_tensor")
        grid.GetPointData().AddArray(tensor)

        # 3-component displacement
        disp_vals = np.random.uniform(-0.01, 0.01, (n, 3))
        disp = numpy_to_vtk(disp_vals)
        disp.SetName("displacement")
        grid.GetPointData().AddArray(disp)

        # Von Mises as scalar
        vm = numpy_to_vtk(np.random.uniform(100, 350, n))
        vm.SetName("von_mises_stress")
        grid.GetPointData().AddArray(vm)

        return grid

    @pytest.mark.asyncio
    async def test_basic_analysis(self):
        from viznoir.tools.inspect_mechanics import inspect_mechanics_impl

        dataset = self._make_fea_dataset()
        with patch("viznoir.tools.inspect_mechanics.read_dataset", return_value=dataset):
            result = await inspect_mechanics_impl("/fake/beam.vtu")

        assert "max_von_mises" in result
        assert "summary" in result
        assert result["max_von_mises"] > 0

    @pytest.mark.asyncio
    async def test_with_yield_strength(self):
        from viznoir.tools.inspect_mechanics import inspect_mechanics_impl

        dataset = self._make_fea_dataset()
        with patch("viznoir.tools.inspect_mechanics.read_dataset", return_value=dataset):
            result = await inspect_mechanics_impl("/fake/beam.vtu", yield_strength=250.0)

        assert "min_safety_factor" in result
        assert "failed_volume_fraction" in result

    @pytest.mark.asyncio
    async def test_with_tensor_decompose(self):
        from viznoir.tools.inspect_mechanics import inspect_mechanics_impl

        dataset = self._make_fea_dataset()
        with patch("viznoir.tools.inspect_mechanics.read_dataset", return_value=dataset):
            result = await inspect_mechanics_impl(
                "/fake/beam.vtu",
                tensor_field="stress_tensor",
                yield_strength=250.0,
            )

        assert "tensor_decomposition" in result
        assert result["tensor_decomposition"]["fields_added"] >= 7

    @pytest.mark.asyncio
    async def test_hotspots_returned(self):
        from viznoir.tools.inspect_mechanics import inspect_mechanics_impl

        dataset = self._make_fea_dataset()
        with patch("viznoir.tools.inspect_mechanics.read_dataset", return_value=dataset):
            result = await inspect_mechanics_impl("/fake/beam.vtu")

        assert "hotspots" in result
        assert len(result["hotspots"]) > 0
        assert "position" in result["hotspots"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools/test_inspect_mechanics.py -v`
Expected: FAIL

- [ ] **Step 3: Implement inspect_mechanics tool**

```python
# src/viznoir/tools/inspect_mechanics.py
"""inspect_mechanics tool — autonomous ME analysis for FEA data."""

from __future__ import annotations

import time
from typing import Any

from viznoir.engine.readers import read_dataset


async def inspect_mechanics_impl(
    file_path: str,
    *,
    yield_strength: float | None = None,
    tensor_field: str | None = None,
    criterion: str = "von_mises",
    top_hotspots: int = 5,
) -> dict[str, Any]:
    """Run autonomous ME analysis on FEA dataset.

    Parameters
    ----------
    file_path : str
        Path to the FEA result file (.vtu, .exo, .vtk, etc.).
    yield_strength : float | None
        Material yield strength for safety factor calculation.
    tensor_field : str | None
        Name of 6-component stress tensor for decomposition.
        If provided, computes principal stresses, von Mises, Tresca, etc.
    criterion : str
        Failure criterion: von_mises, tresca, max_principal, drucker_prager.
    top_hotspots : int
        Number of hotspot locations to report.

    Returns
    -------
    dict with: summary, max_von_mises, max_displacement, min_safety_factor,
    hotspots, tensor_decomposition, failure_criterion, extraction_time_ms
    """
    import asyncio

    t0 = time.perf_counter()

    def _run() -> dict[str, Any]:
        dataset = read_dataset(file_path)
        result: dict[str, Any] = {}

        # Tensor decomposition (if tensor field provided)
        if tensor_field:
            from viznoir.engine.mechanics import stress_tensor_decompose

            stress_tensor_decompose(dataset, tensor_field)
            result["tensor_decomposition"] = {"fields_added": 7, "source": tensor_field}

        # Failure criterion (if tensor + yield provided)
        if tensor_field and yield_strength:
            from viznoir.engine.mechanics import failure_criterion

            failure_criterion(
                dataset, tensor_field,
                criterion=criterion, yield_strength=yield_strength,
            )
            result["failure_criterion"] = {"criterion": criterion, "yield_strength": yield_strength}

        # ME context analysis
        from viznoir.context.mechanics import MEContextParser

        parser = MEContextParser(yield_strength=yield_strength)
        me_result = parser.analyze(dataset)
        result.update(me_result)

        # Hotspot detection on best available stress field
        from viznoir.engine.mechanics import hotspot_detect

        stress_name = _find_stress_field(dataset)
        if stress_name:
            spots = hotspot_detect(dataset, stress_name, top_n=top_hotspots)
            result["hotspots"] = spots

        return result

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run)
    elapsed = (time.perf_counter() - t0) * 1000
    result["extraction_time_ms"] = round(elapsed, 1)
    return result


def _find_stress_field(dataset) -> str | None:
    """Find best stress field in dataset (von Mises preferred)."""
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    candidates = ["von_mises_stress", "von_mises", "vonMises", "stress", "S", "sigma"]

    for name in candidates:
        if pd.GetArray(name) or cd.GetArray(name):
            return name
    return None
```

- [ ] **Step 4: Register tool in server.py**

Add after the last `@mcp.tool()` registration in `server.py`:

```python
    @mcp.tool()
    async def inspect_mechanics(
        file_path: str,
        yield_strength: float | None = None,
        tensor_field: str | None = None,
        criterion: str = "von_mises",
        top_hotspots: int = 5,
    ) -> dict[str, Any]:
        """Autonomous ME analysis — inspect FEA data and deliver engineering insights.

        Inspects the dataset, auto-detects stress/displacement fields, optionally
        decomposes stress tensors, evaluates failure criteria, and reports safety
        factors, hotspot locations, and failure regions.

        Args:
            file_path: Path to FEA result file (.vtu, .exo, .vtk, etc.)
            yield_strength: Material yield strength (Pa) for safety factor calculation
            tensor_field: Name of 6-component stress tensor for decomposition
            criterion: Failure criterion (von_mises, tresca, max_principal, drucker_prager)
            top_hotspots: Number of hotspot locations to report (default 5)
        """
        file_path = _validate_file_path(file_path)
        from viznoir.tools.inspect_mechanics import inspect_mechanics_impl

        return await inspect_mechanics_impl(
            file_path,
            yield_strength=yield_strength,
            tensor_field=tensor_field,
            criterion=criterion,
            top_hotspots=top_hotspots,
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_tools/test_inspect_mechanics.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/tools/inspect_mechanics.py src/viznoir/server.py tests/test_tools/test_inspect_mechanics.py
git commit -m "feat(tools): add inspect_mechanics MCP tool for autonomous ME analysis"
```

---

### Task 7: deform_compare MCP Tool

**Files:**
- Create: `src/viznoir/tools/deform_compare.py`
- Modify: `src/viznoir/server.py` (add tool registration)
- Create: `tests/test_tools/test_deform_compare.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tools/test_deform_compare.py
"""Tests for deform_compare MCP tool."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest


class TestDeformCompareImpl:
    """Test deform_compare_impl function."""

    def _make_fea_dataset(self):
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        grid = vtk.vtkUnstructuredGrid()
        points = vtk.vtkPoints()
        points.InsertNextPoint(0, 0, 0)
        points.InsertNextPoint(1, 0, 0)
        points.InsertNextPoint(0.5, 1, 0)
        grid.SetPoints(points)

        tri = vtk.vtkTriangle()
        tri.GetPointIds().SetId(0, 0)
        tri.GetPointIds().SetId(1, 1)
        tri.GetPointIds().SetId(2, 2)
        grid.InsertNextCell(tri.GetCellType(), tri.GetPointIds())

        disp = numpy_to_vtk(np.array([
            [0.1, 0.0, 0.0], [0.2, 0.0, 0.0], [0.15, 0.05, 0.0],
        ], dtype=np.float64))
        disp.SetName("displacement")
        grid.GetPointData().AddArray(disp)

        vm = numpy_to_vtk(np.array([100.0, 200.0, 150.0], dtype=np.float64))
        vm.SetName("von_mises_stress")
        grid.GetPointData().AddArray(vm)

        return grid

    @pytest.mark.asyncio
    async def test_returns_pipeline_result(self):
        from viznoir.tools.deform_compare import deform_compare_impl

        dataset = self._make_fea_dataset()
        with patch("viznoir.tools.deform_compare.read_dataset", return_value=dataset):
            result = await deform_compare_impl(
                "/fake/beam.vtu",
                displacement_field="displacement",
                color_field="von_mises_stress",
                scale_factor=10.0,
            )
        assert "warped_bounds" in result
        assert "scale_factor" in result

    @pytest.mark.asyncio
    async def test_default_scale_auto(self):
        from viznoir.tools.deform_compare import deform_compare_impl

        dataset = self._make_fea_dataset()
        with patch("viznoir.tools.deform_compare.read_dataset", return_value=dataset):
            result = await deform_compare_impl(
                "/fake/beam.vtu",
                displacement_field="displacement",
                color_field="von_mises_stress",
            )
        # Auto-scale should compute something reasonable
        assert result["scale_factor"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools/test_deform_compare.py -v`
Expected: FAIL

- [ ] **Step 3: Implement deform_compare tool**

```python
# src/viznoir/tools/deform_compare.py
"""deform_compare tool — deformation overlay visualization for FEA."""

from __future__ import annotations

from typing import Any

import numpy as np

from viznoir.engine.readers import read_dataset


async def deform_compare_impl(
    file_path: str,
    displacement_field: str = "displacement",
    color_field: str | None = None,
    scale_factor: float | None = None,
) -> dict[str, Any]:
    """Create deformation overlay — warped mesh colored by stress + original wireframe.

    Parameters
    ----------
    file_path : str
        Path to FEA result file.
    displacement_field : str
        Name of the displacement vector field.
    color_field : str | None
        Scalar field to color the warped mesh (e.g., "von_mises_stress").
    scale_factor : float | None
        Deformation magnification. None = auto-compute based on mesh size.

    Returns
    -------
    dict with: warped_bounds, original_bounds, scale_factor, max_displacement
    """
    import asyncio

    def _run() -> dict[str, Any]:
        from vtk.util.numpy_support import vtk_to_numpy

        from viznoir.engine.mechanics import deform_overlay

        dataset = read_dataset(file_path)

        # Auto-compute scale factor
        if scale_factor is None:
            disp_arr = dataset.GetPointData().GetArray(displacement_field)
            if disp_arr is None:
                disp_arr = dataset.GetCellData().GetArray(displacement_field)
            disp_np = vtk_to_numpy(disp_arr)
            max_disp = float(np.max(np.linalg.norm(disp_np, axis=1)))

            bounds = dataset.GetBounds()
            char_length = max(
                bounds[1] - bounds[0],
                bounds[3] - bounds[2],
                bounds[5] - bounds[4],
            )
            # Target: deformation visible as ~10% of model size
            sf = (0.1 * char_length / max_disp) if max_disp > 0 else 1.0
        else:
            sf = scale_factor
            disp_arr = dataset.GetPointData().GetArray(displacement_field)
            disp_np = vtk_to_numpy(disp_arr)
            max_disp = float(np.max(np.linalg.norm(disp_np, axis=1)))

        warped, wireframe = deform_overlay(dataset, displacement_field, scale_factor=sf)

        return {
            "warped_bounds": list(warped.GetBounds()),
            "original_bounds": list(wireframe.GetBounds()),
            "scale_factor": round(sf, 2),
            "max_displacement": round(max_disp, 8),
            "color_field": color_field,
            "point_count": warped.GetNumberOfPoints(),
        }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)
```

- [ ] **Step 4: Register in server.py**

```python
    @mcp.tool()
    async def deform_compare(
        file_path: str,
        displacement_field: str = "displacement",
        color_field: str | None = None,
        scale_factor: float | None = None,
    ) -> dict[str, Any]:
        """Deformation overlay — warped mesh with stress coloring + original wireframe.

        Auto-computes scale factor if not provided (targets 10% of model size).

        Args:
            file_path: Path to FEA result file (.vtu, .exo, etc.)
            displacement_field: Name of displacement vector field (default: "displacement")
            color_field: Scalar field to color warped mesh (e.g., "von_mises_stress")
            scale_factor: Deformation magnification (None = auto)
        """
        file_path = _validate_file_path(file_path)
        from viznoir.tools.deform_compare import deform_compare_impl

        return await deform_compare_impl(
            file_path,
            displacement_field=displacement_field,
            color_field=color_field,
            scale_factor=scale_factor,
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_tools/test_deform_compare.py -v`
Expected: All 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/tools/deform_compare.py src/viznoir/server.py tests/test_tools/test_deform_compare.py
git commit -m "feat(tools): add deform_compare MCP tool with auto-scale"
```

---

## Track D: ME Harness & Integration

### Task 8: Register ME Filters in Both Registries

**Files:**
- Modify: `src/viznoir/engine/filters.py` (append to `_FILTER_REGISTRY`, lines 974-975)
- Modify: `src/viznoir/core/registry.py` (append to `FILTER_REGISTRY`)

- [ ] **Step 1: Add to engine/filters.py _FILTER_REGISTRY**

Append after `"tube": tube,` (line 975):

```python
    # ME primitives (delegate to engine/mechanics.py)
    "stress_tensor_decompose": _me_stress_tensor_decompose,
    "safety_factor": _me_safety_factor,
    "failure_criterion": _me_failure_criterion,
```

Add wrapper functions above the registry (they adapt the filter signature to the mechanics module):

```python
def _me_stress_tensor_decompose(data, tensor_field="stress_tensor", **_kwargs):
    from viznoir.engine.mechanics import stress_tensor_decompose
    return stress_tensor_decompose(data, tensor_field)


def _me_safety_factor(data, stress_field="von_mises_stress", yield_strength=250e6, result_name="safety_factor", **_kwargs):
    from viznoir.engine.mechanics import safety_factor
    return safety_factor(data, stress_field, yield_strength, result_name=result_name)


def _me_failure_criterion(data, tensor_field="stress_tensor", criterion="von_mises", yield_strength=250e6, **_kwargs):
    from viznoir.engine.mechanics import failure_criterion
    return failure_criterion(data, tensor_field, criterion=criterion, yield_strength=yield_strength)
```

- [ ] **Step 2: Add to core/registry.py FILTER_REGISTRY**

Append after last entry:

```python
    "StressTensorDecompose": {
        "vtk_class": "custom",
        "params": {
            "tensor_field": {"type": "str", "default": "stress_tensor"},
        },
    },
    "SafetyFactor": {
        "vtk_class": "custom",
        "params": {
            "stress_field": {"type": "str", "default": "von_mises_stress"},
            "yield_strength": {"type": "float", "required": True},
            "result_name": {"type": "str", "default": "safety_factor"},
        },
    },
    "FailureCriterion": {
        "vtk_class": "custom",
        "params": {
            "tensor_field": {"type": "str", "default": "stress_tensor"},
            "criterion": {"type": "str", "default": "von_mises"},
            "yield_strength": {"type": "float", "required": True},
        },
    },
```

- [ ] **Step 3: Run existing filter tests + new test**

Run: `pytest tests/test_engine/test_filters.py tests/test_core/test_registry.py -v`
Expected: All existing tests still PASS

- [ ] **Step 4: Commit**

```bash
git add src/viznoir/engine/filters.py src/viznoir/core/registry.py
git commit -m "feat(registry): register ME filters in both PascalCase and snake_case registries"
```

---

### Task 9: Update Harness Skills

**Files:**
- Modify: `.claude-plugin/skills/fea-workflow/SKILL.md`
- Modify: `.claude-plugin/skills/cae-postprocess/SKILL.md`

- [ ] **Step 1: Rewrite fea-workflow/SKILL.md with autoresearch workflow**

```markdown
---
name: fea-workflow
description: >-
  ME Autoresearch workflow skill for FEA post-processing. AI autonomously
  inspects FEA data, decomposes stress tensors, evaluates failure criteria,
  detects hotspots, computes safety factors, and delivers engineering insights
  with cinema-quality visualizations.
  Triggers: FEA, structural, stress, deformation, displacement, von Mises,
  yield, mode shape, safety factor, failure, principal stress, tensor,
  hotspot, SF, tresca, fatigue, 응력, 변형, 항복, 모드 형상, 안전율
---

# ME Autoresearch — FEA Post-Processing

## The Autoresearch Loop

Unlike traditional workflows where the engineer tells you what to render,
**you decide what analysis is needed based on the data**.

```
1. inspect_data(file_path)           → discover fields, timesteps, topology
2. inspect_mechanics(file_path, ...) → autonomous ME analysis
3. Reason about results              → what's critical? what needs attention?
4. Render/animate critical findings  → cinema-quality visuals
5. Deliver engineering summary       → actionable insights
```

## Step 1: Inspect — What Does This Data Contain?

Always start with `inspect_data(file_path)`. From the fields, determine:

| Field Pattern | Analysis Path |
|---------------|---------------|
| 6-component tensor (stress_tensor, S) | → `inspect_mechanics(tensor_field=...)` for full decomposition |
| von_mises_stress / vonMises | → `inspect_mechanics(yield_strength=...)` for SF + hotspots |
| displacement / D | → `deform_compare(...)` for deformation overlay |
| Multiple timesteps | → modal analysis or transient response |

## Step 2: Analyze — inspect_mechanics Does the Heavy Lifting

```json
inspect_mechanics(
  file_path,
  tensor_field="stress_tensor",
  yield_strength=250e6,
  criterion="von_mises",
  top_hotspots=5
)
```

Returns: max stress, min SF, hotspot locations, failure regions, summary text.

**If no yield strength known**, ask the engineer or use common defaults:
| Material | Yield (MPa) |
|----------|-------------|
| Steel A36 | 250 |
| Steel A572 Gr.50 | 345 |
| Al 6061-T6 | 276 |
| Ti-6Al-4V | 880 |

## Step 3: Reason — Interpret the Results

Based on inspect_mechanics output:

| Condition | Action |
|-----------|--------|
| SF > 2.0 everywhere | "Design is conservative. Consider weight optimization." |
| 1.0 < SF < 1.5 | "Marginal safety. Highlight critical regions." |
| SF < 1.0 anywhere | "FAILURE predicted. Show failed regions + hotspots." |
| Hotspots near geometry features | "Stress concentration at [fillet/hole/notch]. Suggest refinement." |

## Step 4: Visualize — Render Critical Findings

| Finding | Visualization |
|---------|---------------|
| Stress distribution | `cinematic_render(field="von_mises_stress", colormap="Cool to Warm")` |
| Deformed shape | `deform_compare(displacement_field="displacement", color_field="von_mises_stress")` |
| Failure regions | `execute_pipeline` with Threshold(failure_ratio > 1.0) |
| Hotspot close-up | `cinematic_render` with camera focused on hotspot position |
| Safety factor map | `cinematic_render(field="safety_factor", colormap="RdYlGn")` |
| Principal stress | `cinematic_render(field="principal_stress_1", colormap="Cool to Warm")` |

## Step 5: Deliver — Engineering Summary

Always conclude with:
1. **One-sentence verdict**: "Structure is safe / needs attention / will fail"
2. **Key numbers**: Max stress, min SF, max displacement
3. **Hotspot locations**: Where to look
4. **Recommendation**: What to do next (optimize, refine mesh, change material)

## Pipeline Examples

### Full Autoresearch Pipeline
```json
{
  "source": {"file": "/data/beam.vtu"},
  "pipeline": [
    {"filter": "StressTensorDecompose", "params": {"tensor_field": "stress_tensor"}},
    {"filter": "SafetyFactor", "params": {"stress_field": "von_mises_stress", "yield_strength": 250e6}},
    {"filter": "WarpByVector", "params": {"vector": "displacement", "scale_factor": 10}}
  ],
  "output": {"type": "image", "render": {"field": "safety_factor", "colormap": "RdYlGn"}}
}
```

### Failure Region Extraction
```json
{
  "source": {"file": "/data/part.vtu"},
  "pipeline": [
    {"filter": "FailureCriterion", "params": {"tensor_field": "S", "criterion": "von_mises", "yield_strength": 345e6}},
    {"filter": "Threshold", "params": {"field": "failure_ratio", "lower": 1.0}}
  ],
  "output": {"type": "image", "render": {"field": "failure_ratio", "colormap": "Reds"}}
}
```
```

- [ ] **Step 2: Update cae-postprocess/SKILL.md — add ME vocabulary**

Add to the "Universal Vocabulary → Tool Mapping" table:

```markdown
| "안전율", "safety factor" | `inspect_mechanics` | yield_strength required |
| "파괴", "failure" | `inspect_mechanics` | criterion + yield_strength |
| "텐서 분해", "decompose" | `inspect_mechanics` | tensor_field |
| "핫스팟", "hotspot" | `inspect_mechanics` | top_hotspots |
| "변형 비교", "deformation overlay" | `deform_compare` | displacement_field, color_field |
| "주응력", "principal stress" | `inspect_mechanics` → then render principal_stress_1 |
| "트레스카", "tresca" | `inspect_mechanics` → criterion="tresca" |
```

Add to "Field-Based Ideas":

```markdown
- **stress tensor (S, stress_tensor, 6-comp)** → suggest: inspect_mechanics with tensor_field for full decomposition
- **safety_factor** → suggest: cinematic_render with RdYlGn colormap, threshold(SF < 1.5)
- **failure_ratio** → suggest: threshold(failure_ratio > 1.0) + cinematic_render in Reds
- **principal_stress_1/2/3** → suggest: cinematic_render with Cool to Warm
```

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/skills/fea-workflow/SKILL.md .claude-plugin/skills/cae-postprocess/SKILL.md
git commit -m "feat(harness): update ME autoresearch skills with inspect_mechanics workflow"
```

---

### Task 10: Update Resources, Presets, and Prompts

**Files:**
- Modify: `src/viznoir/resources/catalog.py` (fea_pipelines_resource, lines 352-393)
- Modify: `src/viznoir/presets/registry.py` (structural_fea, lines 282-339)
- Modify: `src/viznoir/prompts/guides.py` (fea_postprocess, add static/modal/failure guides)

- [ ] **Step 1: Update fea pipeline resource with ME examples**

In `resources/catalog.py`, expand the `fea_pipelines_resource` function to include:

```python
            "tensor_decomposition": {
                "description": "Decompose stress tensor into principal stresses and von Mises",
                "pipeline": {
                    "source": {"file": "/data/part.vtu"},
                    "pipeline": [
                        {
                            "filter": "StressTensorDecompose",
                            "params": {"tensor_field": "stress_tensor"},
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "von_mises_stress", "colormap": "Cool to Warm"},
                    },
                },
            },
            "safety_factor_map": {
                "description": "Compute and visualize safety factor against yield",
                "pipeline": {
                    "source": {"file": "/data/beam.vtu"},
                    "pipeline": [
                        {
                            "filter": "SafetyFactor",
                            "params": {"stress_field": "von_mises_stress", "yield_strength": 250e6},
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "safety_factor", "colormap": "RdYlGn"},
                    },
                },
            },
            "failure_region": {
                "description": "Identify regions exceeding failure criterion",
                "pipeline": {
                    "source": {"file": "/data/part.vtu"},
                    "pipeline": [
                        {
                            "filter": "FailureCriterion",
                            "params": {
                                "tensor_field": "stress_tensor",
                                "criterion": "von_mises",
                                "yield_strength": 345e6,
                            },
                        },
                        {
                            "filter": "Threshold",
                            "params": {"field": "failure_ratio", "lower": 1.0},
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "failure_ratio", "colormap": "Reds"},
                    },
                },
            },
```

- [ ] **Step 2: Update structural_fea preset with ME fields**

In `presets/registry.py`, add to the `structural_fea["fields"]` dict:

```python
            "safety_factor": {
                "field": "safety_factor",
                "association": "POINTS",
                "colormap": "RdYlGn",
                "representation": "Surface",
                "description": "Safety factor (yield/stress)",
            },
            "principal_stress_1": {
                "field": "principal_stress_1",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
                "description": "Maximum principal stress",
            },
            "failure_ratio": {
                "field": "failure_ratio",
                "association": "POINTS",
                "colormap": "Reds",
                "representation": "Surface",
                "description": "Failure criterion ratio (>1.0 = failure)",
            },
            "tresca": {
                "field": "tresca_stress",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
                "description": "Tresca (max shear) stress",
            },
```

- [ ] **Step 3: Add failure FEA guide to prompts**

In `prompts/guides.py`, add a `_FAILURE_FEA_GUIDE` string and register it in `fea_postprocess`:

```python
        guides = {
            "static": _STATIC_FEA_GUIDE,
            "modal": _MODAL_FEA_GUIDE,
            "failure": _FAILURE_FEA_GUIDE,
        }
```

```python
_FAILURE_FEA_GUIDE = """\
# FEA Failure Analysis Guide

## Autoresearch Workflow
1. **inspect_mechanics** with tensor_field and yield_strength — get SF, hotspots, failure regions
2. **cinematic_render** safety_factor field with RdYlGn colormap — green=safe, red=danger
3. **execute_pipeline** with Threshold(failure_ratio > 1.0) — isolate failed regions
4. **deform_compare** — overlay warped shape on original to show displacement

## Failure Criteria
- **von_mises** (default): Best for ductile metals (steel, aluminum)
- **tresca**: Conservative, max shear stress — use for safety-critical parts
- **max_principal**: Brittle materials (cast iron, ceramics, concrete in tension)
- **drucker_prager**: Pressure-dependent materials (soil, rock, concrete, polymers)

## Key Colormaps
- Safety factor: RdYlGn (red=low SF, green=high SF)
- Failure ratio: Reds (white=safe, red=failed)
- Principal stress: Cool to Warm (compression blue, tension red)
- Von Mises: Cool to Warm or Jet

## Interpretation
- SF > 2.0: Conservative design
- 1.5 < SF < 2.0: Acceptable for most applications
- 1.0 < SF < 1.5: Marginal — review carefully
- SF < 1.0: Predicted failure — redesign required
"""
```

- [ ] **Step 4: Run full test suite to verify nothing broken**

Run: `pytest tests/ -q --ignore=tests/test_tools/test_e2e_production.py`
Expected: All tests PASS, count >= 1505

- [ ] **Step 5: Update CLAUDE.md tool count**

Update `## Key Metrics` in CLAUDE.md: Tools 22 → 24

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/resources/catalog.py src/viznoir/presets/registry.py src/viznoir/prompts/guides.py CLAUDE.md
git commit -m "feat(harness): update FEA resources, presets, and prompts for ME autoresearch"
```

---

## Final Integration

### Task 11: Full Integration Test & Quality Gate

**Files:**
- All modified files
- Run full test suite

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ --cov=viznoir --cov-report=term-missing -q --ignore=tests/test_tools/test_e2e_production.py
```

Expected: All tests PASS, coverage >= 80%

- [ ] **Step 2: Run linter**

```bash
ruff check src/ tests/
```

Expected: No errors

- [ ] **Step 3: Run type checker**

```bash
mypy src/viznoir/ --ignore-missing-imports
```

Expected: No errors

- [ ] **Step 4: Verify new test count**

Total tests should be >= 1505 + ~35 new = 1540+

- [ ] **Step 5: Final commit — update README numbers**

Update README.md Numbers section: **24** MCP tools (was 22)

```bash
git add README.md
git commit -m "docs: update tool count to 24 for ME autoresearch tools"
```

- [ ] **Step 6: Create PR**

```bash
git push origin feature/me-autoresearch-harness
```

Create PR: `feat: ME Autoresearch Harness — autonomous engineering analysis for AI agents`

PR description:
```
## What

Adds ME (Mechanical Engineering) computation primitives and autonomous analysis
harness inspired by Karpathy's autoresearch pattern.

## New MCP Tools (2)

- `inspect_mechanics` — autonomous FEA analysis (tensor decomposition, safety factor,
  failure criteria, hotspot detection)
- `deform_compare` — deformation overlay with auto-scale

## Engine Additions

- `engine/mechanics.py` — stress tensor decomposition, safety factor, failure criteria
  (von Mises, Tresca, max principal, Drucker-Prager), hotspot detection, deform overlay
- `context/mechanics.py` — ME context parser with auto-detection

## Harness (AI Layer)

- Updated `fea-workflow` skill with autoresearch loop
- Updated `cae-postprocess` skill with ME vocabulary
- New FEA pipeline resources and presets
- Failure analysis prompt guide

## The Paradigm Shift

Traditional: "Engineer tells tool what to render"
viznoir: "AI inspects data → reasons about physics → delivers engineering insights"

## Tests

~35 new tests covering all ME primitives, tools, and context parsing.
```
