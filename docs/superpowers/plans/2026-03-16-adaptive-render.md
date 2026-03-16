# Adaptive Render Resolution — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded 1080p defaults with config-driven render profiles (`analyze`/`preview`/`publish`), add PNG compression control, and auto cell-to-point conversion for streamlines.

**Architecture:** New `core/profiles.py` module owns resolution+encoding config. `server.py` delegates to `resolve_profile()` instead of hardcoded dicts. `engine/renderer.py` gains `png_compress_level` field. `engine/filters.py` gains auto cell-to-point for point-data-required filters.

**Tech Stack:** Python 3.10+, VTK, FastMCP, pytest

**Spec:** `docs/superpowers/specs/2026-03-16-adaptive-render-design.md`

**Branch:** `feat/adaptive-render-v2` (from `main`)

---

## Chunk 1: core/profiles.py + tests

### Task 1: Create `core/profiles.py` with tests (TDD)

**Files:**
- Create: `src/viznoir/core/profiles.py`
- Test: `tests/test_core/test_profiles.py`

- [ ] **Step 1: Write failing tests for resolve_profile**

```python
# tests/test_core/test_profiles.py
"""Tests for render profile resolution."""

import pytest

from viznoir.core.profiles import PROFILES, RenderProfile, resolve_profile


class TestRenderProfile:
    def test_profile_is_frozen(self):
        p = RenderProfile(800, 600, 6, "test")
        with pytest.raises(AttributeError):
            p.width = 1024


class TestResolveProfile:
    def test_analyze_default(self):
        p = resolve_profile()
        assert p.width == 854
        assert p.height == 480
        assert p.label == "analyze"

    def test_preview(self):
        p = resolve_profile("preview")
        assert p.width == 1280
        assert p.height == 720

    def test_publish(self):
        p = resolve_profile("publish")
        assert p.width == 1920
        assert p.height == 1080
        assert p.png_compress_level == 9

    def test_custom_override_both(self):
        p = resolve_profile("analyze", width=3840, height=2160)
        assert p.width == 3840
        assert p.height == 2160
        assert p.label == "custom"

    def test_one_sided_width_raises(self):
        with pytest.raises(ValueError, match="both width and height"):
            resolve_profile("analyze", width=1920)

    def test_one_sided_height_raises(self):
        with pytest.raises(ValueError, match="both width and height"):
            resolve_profile("analyze", height=1080)

    def test_unknown_purpose_raises(self):
        with pytest.raises(ValueError, match="Unknown purpose"):
            resolve_profile("cinematic")

    def test_bounds_zero_raises(self):
        with pytest.raises(ValueError, match="1-8192"):
            resolve_profile("analyze", width=0, height=480)

    def test_bounds_too_large_raises(self):
        with pytest.raises(ValueError, match="1-8192"):
            resolve_profile("analyze", width=10000, height=480)

    def test_all_profiles_have_valid_dimensions(self):
        for name, p in PROFILES.items():
            assert 1 <= p.width <= 8192, f"{name} width"
            assert 1 <= p.height <= 8192, f"{name} height"
            assert 0 <= p.png_compress_level <= 9, f"{name} compress"
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

Run: `pytest tests/test_core/test_profiles.py -v`
Expected: `ModuleNotFoundError: No module named 'viznoir.core.profiles'`

- [ ] **Step 3: Implement core/profiles.py**

```python
# src/viznoir/core/profiles.py
"""Render profiles — resolution + encoding presets for MCP image tools."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RenderProfile", "PROFILES", "resolve_profile"]


@dataclass(frozen=True)
class RenderProfile:
    """Resolution and encoding settings for a single render call."""

    width: int
    height: int
    png_compress_level: int  # 0-9 (0=fastest/largest, 9=slowest/smallest)
    label: str


PROFILES: dict[str, RenderProfile] = {
    "analyze": RenderProfile(854, 480, 6, "analyze"),
    "preview": RenderProfile(1280, 720, 6, "preview"),
    "publish": RenderProfile(1920, 1080, 9, "publish"),
}


def resolve_profile(
    purpose: str = "analyze",
    width: int | None = None,
    height: int | None = None,
) -> RenderProfile:
    """Resolve a RenderProfile from purpose preset with optional overrides.

    Args:
        purpose: Preset name — "analyze" (480p), "preview" (720p), "publish" (1080p).
        width: Override width (must provide both or neither).
        height: Override height (must provide both or neither).

    Returns:
        Resolved RenderProfile.

    Raises:
        ValueError: One-sided override, out-of-bounds, or unknown purpose.
    """
    if (width is None) != (height is None):
        raise ValueError(
            f"Specify both width and height, or neither. Got width={width}, height={height}"
        )
    if width is not None and height is not None:
        if not (1 <= width <= 8192 and 1 <= height <= 8192):
            raise ValueError(f"width and height must be 1-8192. Got {width}x{height}")
        base = PROFILES.get(purpose, PROFILES["analyze"])
        return RenderProfile(width, height, base.png_compress_level, "custom")
    profile = PROFILES.get(purpose)
    if profile is None:
        raise ValueError(f"Unknown purpose '{purpose}'. Available: {list(PROFILES)}")
    return profile
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_core/test_profiles.py -v`
Expected: 11 passed

- [ ] **Step 5: Lint + type check**

Run: `ruff check src/viznoir/core/profiles.py && mypy src/viznoir/core/profiles.py --ignore-missing-imports`
Expected: No issues

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/core/profiles.py tests/test_core/test_profiles.py
git commit -m "feat: add core/profiles.py — render profile resolution

RenderProfile dataclass + PROFILES dict + resolve_profile().
Aspect ratio protection (one-sided override raises ValueError).
Bounds validation (1-8192). 11 tests."
```

---

## Chunk 2: engine/renderer.py — PNG compression

### Task 2: Add png_compress_level to RenderConfig and _capture_png

**Files:**
- Modify: `src/viznoir/engine/renderer.py:24-44` (RenderConfig), `565-582` (_capture_png), `148`, `213`, `356`
- Test: `tests/test_engine/test_renderer.py`

- [ ] **Step 1: Write failing test for RenderConfig.png_compress_level**

Add to existing `tests/test_engine/test_renderer.py`:

```python
class TestRenderConfigCompressLevel:
    def test_default_compress_level(self):
        from viznoir.engine.renderer import RenderConfig
        cfg = RenderConfig()
        assert cfg.png_compress_level == 6

    def test_custom_compress_level(self):
        from viznoir.engine.renderer import RenderConfig
        cfg = RenderConfig(png_compress_level=1)
        assert cfg.png_compress_level == 1
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_engine/test_renderer.py::TestRenderConfigCompressLevel -v`
Expected: `TypeError: __init__() got an unexpected keyword argument 'png_compress_level'`

- [ ] **Step 3: Add png_compress_level to RenderConfig**

In `src/viznoir/engine/renderer.py`, add after `transfer_preset` field (line ~43):

```python
    png_compress_level: int = 6  # 0-9, controls vtkPNGWriter compression
```

- [ ] **Step 4: Update _capture_png to accept compress_level**

Change `_capture_png` function (line ~565):

```python
def _capture_png(rw: vtk.vtkRenderWindow, compress_level: int = 6) -> bytes:
```

Inside the function, after `writer = vtk.vtkPNGWriter()`, add:

```python
    writer.SetCompressionLevel(compress_level)
```

- [ ] **Step 5: Update all 3 call sites**

Line ~148 (empty dataset early return):
```python
return _capture_png(rw, self._config.png_compress_level)
```

Line ~213 (normal render return):
```python
return _capture_png(rw, self._config.png_compress_level)
```

Line ~356 (render_multiple return):
```python
return _capture_png(rw, self._config.png_compress_level)
```

- [ ] **Step 6: Run tests — expect PASS**

Run: `pytest tests/test_engine/test_renderer.py -v`
Expected: All pass (including new tests)

- [ ] **Step 7: Commit**

```bash
git add src/viznoir/engine/renderer.py tests/test_engine/test_renderer.py
git commit -m "feat: add png_compress_level to RenderConfig + _capture_png

RenderConfig.png_compress_level (0-9, default 6).
vtkPNGWriter.SetCompressionLevel() called at all 3 _capture_png sites."
```

---

## Chunk 3: engine/filters.py — auto cell-to-point

### Task 3: Add _auto_cell_to_point and apply to streamlines/glyph

**Files:**
- Modify: `src/viznoir/engine/filters.py:271` (streamlines), `644` (glyph)
- Test: `tests/test_engine/test_filters.py`

- [ ] **Step 1: Write failing tests for _auto_cell_to_point**

Add to `tests/test_engine/test_filters.py`:

```python
class TestAutoCellToPoint:
    def _make_cell_only_dataset(self):
        """Create a dataset with a vector field only in cell data."""
        import vtk
        import numpy as np
        from vtkmodules.util.numpy_support import numpy_to_vtk

        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
        src.Update()
        ds = src.GetOutput()

        n_cells = ds.GetNumberOfCells()
        vectors = numpy_to_vtk(np.random.rand(n_cells, 3).astype(np.float64))
        vectors.SetName("CellVectors")
        ds.GetCellData().AddArray(vectors)
        return ds

    def test_cell_only_converts(self):
        from viznoir.engine.filters import _auto_cell_to_point

        ds = self._make_cell_only_dataset()
        assert ds.GetPointData().GetArray("CellVectors") is None
        result = _auto_cell_to_point(ds, "CellVectors")
        assert result.GetPointData().GetArray("CellVectors") is not None

    def test_point_already_exists_noop(self):
        from viznoir.engine.filters import _auto_cell_to_point

        import vtk
        src = vtk.vtkRTAnalyticSource()
        src.Update()
        ds = src.GetOutput()
        # RTData is point data
        result = _auto_cell_to_point(ds, "RTData")
        assert result is ds  # same object, no conversion

    def test_missing_field_noop(self):
        from viznoir.engine.filters import _auto_cell_to_point

        import vtk
        src = vtk.vtkRTAnalyticSource()
        src.Update()
        ds = src.GetOutput()
        result = _auto_cell_to_point(ds, "nonexistent")
        assert result is ds
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_engine/test_filters.py::TestAutoCellToPoint -v`
Expected: `ImportError: cannot import name '_auto_cell_to_point'`

- [ ] **Step 3: Implement _auto_cell_to_point**

Add to `src/viznoir/engine/filters.py` (after imports, before first filter function):

```python
def _auto_cell_to_point(dataset: vtk.vtkDataSet, array_name: str) -> vtk.vtkDataSet:
    """Convert cell data to point data if array exists only in cell data."""
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    if pd.GetArray(array_name) is not None:
        return dataset
    if cd.GetArray(array_name) is None:
        return dataset
    c2p = vtk.vtkCellDataToPointData()
    c2p.SetInputData(dataset)
    c2p.Update()
    return c2p.GetOutput()
```

- [ ] **Step 4: Apply to streamlines function**

In `streamlines()` (line ~271), after the dataset is received but before StreamTracer setup, add:

```python
    dataset = _auto_cell_to_point(dataset, vectors)
```

Where `vectors` is the vector field name parameter.

- [ ] **Step 5: Apply to glyph function**

In `glyph()` (line ~644), same pattern — auto-convert before glyph filter:

```python
    dataset = _auto_cell_to_point(dataset, vectors)
```

- [ ] **Step 6: Run tests — expect PASS**

Run: `pytest tests/test_engine/test_filters.py -v`
Expected: All pass (existing + 3 new)

- [ ] **Step 7: Commit**

```bash
git add src/viznoir/engine/filters.py tests/test_engine/test_filters.py
git commit -m "feat: auto cell-to-point conversion for streamlines/glyph

_auto_cell_to_point() detects cell-only vector fields and applies
vtkCellDataToPointData before StreamTracer/Glyph. 3 new tests."
```

---

## Chunk 4: server.py — purpose parameter for 7 tools + compare fix

### Task 4: Migrate server.py to use resolve_profile

**Files:**
- Modify: `src/viznoir/server.py`
- Modify: `src/viznoir/tools/compare.py:66-67`

- [ ] **Step 1: Delete _PURPOSE_RESOLUTION and _resolve_size from server.py**

Remove the `_PURPOSE_RESOLUTION` dict and `_resolve_size()` function (added by feat/adaptive-render-benchmark branch). If on a fresh branch from main, these won't exist — skip this step.

- [ ] **Step 2: Add import at top of server.py**

After existing imports (line ~14):

```python
from viznoir.core.profiles import resolve_profile
```

- [ ] **Step 3: Update render tool (line ~136)**

Change:
```python
    width: int = 1920,
    height: int = 1080,
```
To:
```python
    purpose: Literal["analyze", "preview", "publish"] = "analyze",
    width: int | None = None,
    height: int | None = None,
```

Add docstring entries for purpose/width/height. In function body, before calling render_impl:
```python
    profile = resolve_profile(purpose, width, height)
```
Pass `width=profile.width, height=profile.height` to render_impl.

- [ ] **Step 4: Update slice tool** — same pattern as render

- [ ] **Step 5: Update contour tool** — same pattern

- [ ] **Step 6: Update clip tool** — same pattern

- [ ] **Step 7: Update streamlines tool** — same pattern

- [ ] **Step 8: Update compare tool**

Same purpose/width/height pattern. Then fix `tools/compare.py` line 66-67:

Change:
```python
half_w = (width or 1920) // 2
h = height or 1080
```
To:
```python
half_w = width // 2
h = height
```

- [ ] **Step 9: Update batch_render tool** — same purpose/width/height pattern

- [ ] **Step 10: Run lint + type check**

Run: `ruff check src/viznoir/server.py src/viznoir/tools/compare.py && mypy src/viznoir/server.py --ignore-missing-imports`
Expected: No issues

- [ ] **Step 11: Run full test suite**

Run: `pytest tests/ -q --tb=short`
Expected: 1489+ passed, 0 failed

- [ ] **Step 12: Commit**

```bash
git add src/viznoir/server.py src/viznoir/tools/compare.py
git commit -m "feat: apply purpose parameter to 7 image tools

render, slice, contour, clip, streamlines, compare, batch_render
now accept purpose='analyze'|'preview'|'publish' (default: analyze=480p).
Removes hardcoded 1920x1080 defaults.
compare_impl fallback removed (callers always pass resolved integers)."
```

---

## Chunk 5: Verify + cleanup

### Task 5: Full verification and final commit

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -q --tb=short`
Expected: All pass

- [ ] **Step 2: Lint entire project**

Run: `ruff check src/ tests/ && mypy src/viznoir/ --ignore-missing-imports`
Expected: 0 issues

- [ ] **Step 3: Verify no Japanese/non-English comments**

Run: `python3 -c "..." scan for non-ASCII in src/viznoir/`
Expected: No CJK characters in source files

- [ ] **Step 4: Run benchmark to confirm performance**

Run: `VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow python3 -c "from viznoir.engine.renderer import RenderConfig, VTKRenderer; ..."`
Expected: ~17ms at 480p default

- [ ] **Step 5: Final commit (if any cleanup)**

```bash
git commit -m "chore: cleanup and verify adaptive render v2"
```
