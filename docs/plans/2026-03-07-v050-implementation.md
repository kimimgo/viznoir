# v0.5.0 Science Storyteller Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add data insight extraction (`analyze_data`), asset composition (`compose_assets`), and storytelling support to viznoir.

**Architecture:** Hybrid approach — viznoir provides Level 2 physics-aware analysis + asset composition tools; LLM agent handles story planning. New `engine/analysis.py` does VTK data analysis, `anim/` package gets timeline + transitions + compositor for video output, `server.py` gains 2 tools + 1 prompt + 1 resource.

**Tech Stack:** VTK (data analysis), Pillow (frame compositing), ffmpeg (video encoding), cairosvg (LaTeX), pytest

---

### Task 1: Engine Analysis — Field Statistics & Anomaly Detection

**Files:**
- Create: `src/viznoir/engine/analysis.py`
- Test: `tests/test_engine/test_analysis.py`

**Step 1: Write the failing tests**

```python
# tests/test_engine/test_analysis.py
"""Tests for engine/analysis.py — data insight extraction."""

from __future__ import annotations

import pytest
import vtk


def _make_wavelet():
    """Create a wavelet dataset for testing."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-16, 16, -16, 16, -16, 16)
    src.Update()
    return src.GetOutput()


class TestComputeFieldStats:
    def test_returns_dict_with_required_keys(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        stats = compute_field_stats(ds, "RTData")
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "std" in stats

    def test_min_less_than_max(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        stats = compute_field_stats(ds, "RTData")
        assert stats["min"] < stats["max"]

    def test_mean_between_min_and_max(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        stats = compute_field_stats(ds, "RTData")
        assert stats["min"] <= stats["mean"] <= stats["max"]

    def test_unknown_field_raises(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        with pytest.raises(KeyError):
            compute_field_stats(ds, "NonExistentField")


class TestDetectAnomalies:
    def test_returns_list(self):
        from viznoir.engine.analysis import detect_anomalies
        ds = _make_wavelet()
        anomalies = detect_anomalies(ds, "RTData")
        assert isinstance(anomalies, list)

    def test_anomalies_have_location_and_value(self):
        from viznoir.engine.analysis import detect_anomalies
        ds = _make_wavelet()
        anomalies = detect_anomalies(ds, "RTData")
        if anomalies:
            a = anomalies[0]
            assert "location" in a
            assert "value" in a
            assert "type" in a
            assert len(a["location"]) == 3

    def test_finds_extrema_in_wavelet(self):
        from viznoir.engine.analysis import detect_anomalies
        ds = _make_wavelet()
        anomalies = detect_anomalies(ds, "RTData")
        # Wavelet has known extrema — should find at least one
        assert len(anomalies) >= 1


class TestInferPhysicsContext:
    def test_known_field_returns_context(self):
        from viznoir.engine.analysis import infer_physics_context
        ctx = infer_physics_context("Pressure", {"min": -100, "max": 500, "mean": 200, "std": 120})
        assert isinstance(ctx, str)
        assert len(ctx) > 10

    def test_unknown_field_returns_generic(self):
        from viznoir.engine.analysis import infer_physics_context
        ctx = infer_physics_context("RTData", {"min": 0, "max": 300, "mean": 150, "std": 50})
        assert isinstance(ctx, str)


class TestRecommendViews:
    def test_returns_list_of_dicts(self):
        from viznoir.engine.analysis import recommend_views
        anomalies = [{"type": "local_extremum", "location": [3.0, 0, 0], "value": 500}]
        views = recommend_views("Pressure", anomalies, bounds=[[-10, 10], [-5, 5], [-5, 5]])
        assert isinstance(views, list)
        if views:
            v = views[0]
            assert "type" in v
            assert "params" in v
            assert "reason" in v

    def test_anomaly_generates_slice_view(self):
        from viznoir.engine.analysis import recommend_views
        anomalies = [{"type": "local_extremum", "location": [3.0, 0, 0], "value": 500}]
        views = recommend_views("Pressure", anomalies, bounds=[[-10, 10], [-5, 5], [-5, 5]])
        slice_views = [v for v in views if v["type"] == "slice"]
        assert len(slice_views) >= 1


class TestFullAnalysis:
    def test_analyze_dataset_returns_report(self):
        from viznoir.engine.analysis import analyze_dataset
        ds = _make_wavelet()
        report = analyze_dataset(ds)
        assert "summary" in report
        assert "field_analyses" in report
        assert report["summary"]["num_points"] > 0

    def test_analyze_dataset_with_domain_hint(self):
        from viznoir.engine.analysis import analyze_dataset
        ds = _make_wavelet()
        report = analyze_dataset(ds, domain="cfd")
        assert report["summary"]["domain_guess"] == "cfd"

    def test_analyze_dataset_with_focus(self):
        from viznoir.engine.analysis import analyze_dataset
        ds = _make_wavelet()
        report = analyze_dataset(ds, focus="RTData")
        assert len(report["field_analyses"]) == 1
        assert report["field_analyses"][0]["name"] == "RTData"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine/test_analysis.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'viznoir.engine.analysis'`

**Step 3: Implement `engine/analysis.py`**

```python
# src/viznoir/engine/analysis.py
"""Data insight extraction — field statistics, anomaly detection, physics context."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


def compute_field_stats(dataset: Any, field_name: str) -> dict[str, float]:
    """Compute basic statistics for a scalar field using VTK native arrays."""
    arr = dataset.GetPointData().GetArray(field_name)
    if arr is None:
        arr = dataset.GetCellData().GetArray(field_name)
    if arr is None:
        raise KeyError(f"Field '{field_name}' not found in dataset")

    from vtk.util.numpy_support import vtk_to_numpy
    data = vtk_to_numpy(arr)

    # Handle vector fields — compute magnitude
    if data.ndim > 1:
        data = np.linalg.norm(data, axis=1)

    return {
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
    }


def detect_anomalies(
    dataset: Any,
    field_name: str,
    *,
    top_n: int = 5,
    threshold_sigma: float = 2.5,
) -> list[dict[str, Any]]:
    """Detect local extrema and anomalies in a scalar field.

    Uses gradient magnitude to find regions of rapid change,
    then identifies points exceeding threshold_sigma standard deviations.
    """
    arr = dataset.GetPointData().GetArray(field_name)
    if arr is None:
        arr = dataset.GetCellData().GetArray(field_name)
    if arr is None:
        raise KeyError(f"Field '{field_name}' not found")

    from vtk.util.numpy_support import vtk_to_numpy
    data = vtk_to_numpy(arr)
    if data.ndim > 1:
        data = np.linalg.norm(data, axis=1)

    mean, std = np.mean(data), np.std(data)
    if std < 1e-12:
        return []

    # Find points beyond threshold
    deviations = np.abs(data - mean) / std
    extreme_mask = deviations > threshold_sigma
    extreme_indices = np.where(extreme_mask)[0]

    if len(extreme_indices) == 0:
        # Fallback: just report global max and min
        max_idx = int(np.argmax(data))
        min_idx = int(np.argmin(data))
        extreme_indices = np.array([max_idx, min_idx])

    # Sort by deviation (most extreme first) and take top_n
    sorted_indices = extreme_indices[np.argsort(-deviations[extreme_indices])][:top_n]

    anomalies = []
    for idx in sorted_indices:
        pt = dataset.GetPoint(int(idx))
        val = float(data[idx])
        anomalies.append({
            "type": "local_extremum" if val > mean else "local_minimum",
            "location": [round(pt[0], 3), round(pt[1], 3), round(pt[2], 3)],
            "value": round(val, 4),
            "significance": "high" if deviations[idx] > 3.0 else "medium",
        })

    return anomalies


# --- Physics context inference ---

_PHYSICS_KEYWORDS: dict[str, dict[str, str]] = {
    r"^p$|pressure|p_rgh": {
        "name": "pressure",
        "high_gradient": "Large pressure gradient suggests strong flow acceleration or shock formation",
        "uniform": "Relatively uniform pressure field — steady or stagnant flow region",
    },
    r"^U$|velocity|vel": {
        "name": "velocity",
        "high_gradient": "Sharp velocity gradient indicates shear layer or boundary layer",
        "uniform": "Uniform velocity — developed flow or free-stream region",
    },
    r"temperature|^T$|temp": {
        "name": "temperature",
        "high_gradient": "Strong temperature gradient — active heat transfer region",
        "uniform": "Thermal equilibrium region",
    },
    r"stress|von.?mises|sigma": {
        "name": "stress",
        "high_gradient": "Stress concentration — potential failure initiation site",
        "uniform": "Low stress region — structurally safe zone",
    },
    r"displacement|deform|^d$|^u$": {
        "name": "displacement",
        "high_gradient": "Localized deformation — possible hinge or buckling point",
        "uniform": "Rigid body region — minimal deformation",
    },
    r"k$|tke|turbulent.*kinetic": {
        "name": "turbulent_kinetic_energy",
        "high_gradient": "High turbulence production zone",
        "uniform": "Low turbulence — laminar or far-field",
    },
}


def infer_physics_context(field_name: str, stats: dict[str, float]) -> str:
    """Infer physics context string from field name and statistics."""
    gradient_range = stats["max"] - stats["min"]
    cv = stats["std"] / abs(stats["mean"]) if abs(stats["mean"]) > 1e-12 else 0.0

    for pattern, info in _PHYSICS_KEYWORDS.items():
        if re.search(pattern, field_name, re.IGNORECASE):
            if cv > 0.3:
                return f"{info['high_gradient']} (range: {gradient_range:.4g}, CV: {cv:.2f})"
            else:
                return f"{info['uniform']} (range: {gradient_range:.4g}, CV: {cv:.2f})"

    # Generic fallback
    if cv > 0.3:
        return f"High spatial variation in {field_name} (range: {gradient_range:.4g}, CV: {cv:.2f})"
    return f"Relatively uniform {field_name} distribution (range: {gradient_range:.4g}, CV: {cv:.2f})"


def recommend_views(
    field_name: str,
    anomalies: list[dict[str, Any]],
    *,
    bounds: list[list[float]] | None = None,
) -> list[dict[str, Any]]:
    """Generate recommended view parameters from anomalies."""
    views: list[dict[str, Any]] = []

    for anomaly in anomalies[:3]:  # Top 3 anomalies
        loc = anomaly["location"]

        # Slice at anomaly location — perpendicular to longest axis
        if bounds:
            extents = [b[1] - b[0] for b in bounds]
            longest = extents.index(max(extents))
            normal = [0, 0, 0]
            normal[longest] = 1
        else:
            normal = [1, 0, 0]

        views.append({
            "type": "slice",
            "params": {"origin": loc, "normal": normal},
            "reason": f"{field_name} {anomaly['type']} at ({loc[0]}, {loc[1]}, {loc[2]})",
        })

    # Always recommend a contour at significant values
    if anomalies:
        values = [a["value"] for a in anomalies[:2]]
        views.append({
            "type": "contour",
            "params": {"values": [round(v, 4) for v in values]},
            "reason": f"Iso-surfaces at {field_name} extrema",
        })

    return views


# --- Equation suggestions ---

_DOMAIN_EQUATIONS: dict[str, list[dict[str, str]]] = {
    "cfd": [
        {"context": "momentum conservation", "latex": r"\rho \frac{D\mathbf{u}}{Dt} = -\nabla p + \mu \nabla^2 \mathbf{u} + \mathbf{f}", "name": "Navier-Stokes"},
        {"context": "mass conservation", "latex": r"\nabla \cdot \mathbf{u} = 0", "name": "Continuity"},
        {"context": "pressure-velocity coupling", "latex": r"p + \frac{1}{2}\rho v^2 = \text{const}", "name": "Bernoulli"},
    ],
    "fea": [
        {"context": "equilibrium", "latex": r"\nabla \cdot \boldsymbol{\sigma} + \mathbf{b} = 0", "name": "Cauchy equilibrium"},
        {"context": "yield criterion", "latex": r"\sigma_{vm} = \sqrt{\frac{3}{2} s_{ij} s_{ij}}", "name": "von Mises"},
    ],
    "thermal": [
        {"context": "heat conduction", "latex": r"\rho c_p \frac{\partial T}{\partial t} = k \nabla^2 T + q", "name": "Heat equation"},
        {"context": "convective heat transfer", "latex": r"q = h A (T_s - T_\infty)", "name": "Newton's cooling"},
    ],
}


def _guess_domain(field_names: list[str]) -> str:
    """Guess physics domain from field names."""
    names_lower = " ".join(f.lower() for f in field_names)
    if any(kw in names_lower for kw in ["velocity", "pressure", " u ", " p "]):
        return "cfd"
    if any(kw in names_lower for kw in ["stress", "displacement", "strain"]):
        return "fea"
    if any(kw in names_lower for kw in ["temperature", "heat", "thermal"]):
        return "thermal"
    return "cfd"  # default


def analyze_dataset(
    dataset: Any,
    *,
    focus: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Full dataset analysis — returns Level 2 insight report."""
    # Collect field names
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    all_fields = []
    for i in range(pd.GetNumberOfArrays()):
        all_fields.append(("point", pd.GetArrayName(i)))
    for i in range(cd.GetNumberOfArrays()):
        all_fields.append(("cell", cd.GetArrayName(i)))

    field_names = [name for _, name in all_fields if name]

    if domain is None:
        domain = _guess_domain(field_names)

    # Bounds
    bounds_flat = list(dataset.GetBounds())
    bounds = [[bounds_flat[i], bounds_flat[i + 1]] for i in range(0, 6, 2)]

    # Filter by focus
    if focus:
        all_fields = [(loc, name) for loc, name in all_fields if name == focus]

    # Analyze each field
    field_analyses = []
    for _, field_name in all_fields:
        if not field_name:
            continue
        try:
            stats = compute_field_stats(dataset, field_name)
        except (KeyError, ValueError):
            continue

        anomalies = detect_anomalies(dataset, field_name)
        physics_ctx = infer_physics_context(field_name, stats)
        views = recommend_views(field_name, anomalies, bounds=bounds)

        field_analyses.append({
            "name": field_name,
            "stats": stats,
            "physics_context": physics_ctx,
            "anomalies": anomalies,
            "recommended_views": views,
        })

    return {
        "summary": {
            "num_points": dataset.GetNumberOfPoints(),
            "num_cells": dataset.GetNumberOfCells(),
            "bounds": bounds,
            "fields": field_names,
            "domain_guess": domain,
        },
        "field_analyses": field_analyses,
        "suggested_equations": _DOMAIN_EQUATIONS.get(domain, []),
    }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine/test_analysis.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/engine/analysis.py tests/test_engine/test_analysis.py
git commit -m "feat(engine): add analysis module — field stats, anomaly detection, physics context"
```

---

### Task 2: `analyze_data` MCP Tool + LaTeX Cache

**Files:**
- Create: `src/viznoir/tools/analyze.py`
- Modify: `src/viznoir/server.py` (add analyze_data tool)
- Modify: `src/viznoir/anim/latex.py` (add SVG cache)
- Test: `tests/test_tools/test_analyze_tool.py`

**Step 1: Write the failing tests**

```python
# tests/test_tools/test_analyze_tool.py
"""Tests for analyze_data MCP tool."""

from __future__ import annotations

import pytest


class TestAnalyzeDataTool:
    async def test_tool_registered(self):
        from fastmcp import Client
        from viznoir.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert "analyze_data" in names

    async def test_nonexistent_file_returns_error(self):
        from fastmcp import Client
        from viznoir.server import mcp

        async with Client(mcp) as client:
            try:
                result = await client.call_tool("analyze_data", {"file_path": "/nonexistent/file.vtk"})
                text = str(result)
                assert "error" in text.lower() or "not found" in text.lower()
            except Exception as e:
                assert "not found" in str(e).lower() or "error" in str(e).lower()


class TestLatexCache:
    def test_cache_speedup(self):
        from viznoir.anim.latex import render_latex
        import time

        tex = r"E = mc^2"
        # First call — cold
        t0 = time.perf_counter()
        render_latex(tex, color="FFFFFF")
        cold_ms = (time.perf_counter() - t0) * 1000

        # Second call — cached
        t0 = time.perf_counter()
        render_latex(tex, color="FFFFFF")
        warm_ms = (time.perf_counter() - t0) * 1000

        # Cached should be significantly faster
        assert warm_ms < cold_ms * 0.5 or warm_ms < 30

    def test_different_colors_different_cache(self):
        from viznoir.anim.latex import render_latex
        img1 = render_latex(r"x^2", color="FFFFFF")
        img2 = render_latex(r"x^2", color="FF0000")
        # Both should produce valid images (not same cache entry for different colors)
        assert img1.width > 0
        assert img2.width > 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools/test_analyze_tool.py -v`
Expected: FAIL (analyze_data tool not registered)

**Step 3: Implement**

Create `src/viznoir/tools/analyze.py`:
```python
"""analyze_data tool — VTK data insight extraction."""

from __future__ import annotations

from typing import Any

from viznoir.core.runner import VTKRunner
from viznoir.engine.readers import read_vtk_file


async def analyze_data_impl(
    file_path: str,
    runner: VTKRunner,
    *,
    focus: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Load VTK file and run full analysis. Returns Level 2 insight report."""
    import asyncio

    def _run():
        dataset = read_vtk_file(file_path)
        from viznoir.engine.analysis import analyze_dataset
        return analyze_dataset(dataset, focus=focus, domain=domain)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)
```

Add to `src/viznoir/server.py` (after `volume_render` tool, ~line 787):
```python
@mcp.tool()
async def analyze_data(
    file_path: str,
    focus: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Analyze VTK/simulation data and extract physics-aware insights.

    Returns a Level 2 report with:
    - Field statistics (min/max/mean/std)
    - Physics context (what the numbers mean)
    - Anomaly locations (where to look)
    - Recommended views (slice/contour parameters ready for tool calls)
    - Suggested equations (relevant governing equations)

    Use this as the first step in a storytelling workflow:
    1. analyze_data → get insights
    2. Plan story from insights (use story_planning prompt)
    3. Execute recommended_views with render/slice/contour tools
    4. compose_assets → final output

    Args:
        file_path: Path to VTK/OpenFOAM/CGNS file
        focus: Analyze only this field (None for all fields)
        domain: Physics domain hint — "cfd", "fea", "thermal" (None for auto-detect)
    """
    file_path = _validate_file_path(file_path)
    logger.debug("tool.analyze_data: start file=%s focus=%s domain=%s", file_path, focus, domain)
    t0 = time.monotonic()
    from viznoir.tools.analyze import analyze_data_impl

    result = await analyze_data_impl(file_path, _runner, focus=focus, domain=domain)
    logger.debug("tool.analyze_data: done in %.2fs", time.monotonic() - t0)
    return result
```

Add LaTeX SVG cache to `src/viznoir/anim/latex.py` — modify `render_latex()`:
```python
# Add at module level (after CAIROSVG_AVAILABLE):
_SVG_CACHE: dict[str, str] = {}

# In render_latex(), replace the LATEX_AVAILABLE branch:
    if LATEX_AVAILABLE and CAIROSVG_AVAILABLE:
        cache_key = f"{body}:{color.lstrip('#')}:{preamble}"
        svg_text = _SVG_CACHE.get(cache_key)

        if svg_text is None:
            tex_source = _LATEX_TEMPLATE % {
                "preamble": preamble,
                "color": color.lstrip("#"),
                "body": body,
            }
            with tempfile.TemporaryDirectory(prefix="viznoir-latex-") as tmp:
                work_dir = Path(tmp)
                dvi = _latex_to_dvi(tex_source, work_dir)
                svg_text = _dvi_to_svg(dvi, work_dir)
                svg_text = _colorize_svg(svg_text, color.lstrip("#"))
            _SVG_CACHE[cache_key] = svg_text

        png_bytes = _svg_to_png(svg_text, scale=scale)
        buf = BytesIO(png_bytes)
        return PILImage.open(buf).convert("RGBA")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tools/test_analyze_tool.py tests/test_anim/test_latex.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/tools/analyze.py src/viznoir/server.py src/viznoir/anim/latex.py \
    tests/test_tools/test_analyze_tool.py
git commit -m "feat: add analyze_data MCP tool + LaTeX SVG cache"
```

---

### Task 3: Animation Timeline + Transitions

**Files:**
- Create: `src/viznoir/anim/timeline.py`
- Create: `src/viznoir/anim/transitions.py`
- Test: `tests/test_anim/test_timeline.py`
- Test: `tests/test_anim/test_transitions.py`

**Step 1: Write failing tests**

```python
# tests/test_anim/test_timeline.py
"""Tests for anim/timeline.py — scene sequencing."""

from __future__ import annotations

import pytest


class TestScene:
    def test_scene_creation(self):
        from viznoir.anim.timeline import Scene
        s = Scene(asset_indices=[0, 1], duration=3.0, transition="fade_in")
        assert s.duration == 3.0
        assert s.transition == "fade_in"


class TestTimeline:
    def test_total_duration(self):
        from viznoir.anim.timeline import Scene, Timeline
        scenes = [
            Scene(asset_indices=[0], duration=3.0),
            Scene(asset_indices=[1], duration=4.0),
        ]
        tl = Timeline(scenes)
        assert tl.total_duration == 7.0

    def test_frame_count(self):
        from viznoir.anim.timeline import Scene, Timeline
        scenes = [Scene(asset_indices=[0], duration=2.0)]
        tl = Timeline(scenes, fps=30)
        assert tl.frame_count == 60

    def test_scene_at_time(self):
        from viznoir.anim.timeline import Scene, Timeline
        scenes = [
            Scene(asset_indices=[0], duration=3.0),
            Scene(asset_indices=[1], duration=4.0),
        ]
        tl = Timeline(scenes)
        idx, local_t = tl.scene_at(0.0)
        assert idx == 0
        assert local_t == 0.0

        idx, local_t = tl.scene_at(3.5)
        assert idx == 1
        assert 0.0 < local_t < 1.0

    def test_scene_at_end(self):
        from viznoir.anim.timeline import Scene, Timeline
        scenes = [Scene(asset_indices=[0], duration=2.0)]
        tl = Timeline(scenes)
        idx, local_t = tl.scene_at(2.0)
        assert idx == 0
        assert local_t == 1.0

    def test_empty_timeline(self):
        from viznoir.anim.timeline import Timeline
        tl = Timeline([])
        assert tl.total_duration == 0.0
        assert tl.frame_count == 0
```

```python
# tests/test_anim/test_transitions.py
"""Tests for anim/transitions.py — scene transitions."""

from __future__ import annotations

import numpy as np
from PIL import Image


def _red_image(w=100, h=100):
    return Image.new("RGBA", (w, h), (255, 0, 0, 255))

def _blue_image(w=100, h=100):
    return Image.new("RGBA", (w, h), (0, 0, 255, 255))


class TestFadeIn:
    def test_t0_is_transparent(self):
        from viznoir.anim.transitions import fade_in
        img = _red_image()
        result = fade_in(img, 0.0)
        assert result.getpixel((50, 50))[3] == 0

    def test_t1_is_opaque(self):
        from viznoir.anim.transitions import fade_in
        img = _red_image()
        result = fade_in(img, 1.0)
        assert result.getpixel((50, 50))[3] == 255


class TestFadeOut:
    def test_t0_is_opaque(self):
        from viznoir.anim.transitions import fade_out
        img = _red_image()
        result = fade_out(img, 0.0)
        assert result.getpixel((50, 50))[3] == 255

    def test_t1_is_transparent(self):
        from viznoir.anim.transitions import fade_out
        img = _red_image()
        result = fade_out(img, 1.0)
        assert result.getpixel((50, 50))[3] == 0


class TestDissolve:
    def test_t0_is_source(self):
        from viznoir.anim.transitions import dissolve
        result = dissolve(_red_image(), _blue_image(), 0.0)
        r, g, b, a = result.getpixel((50, 50))
        assert r == 255 and b == 0

    def test_t1_is_target(self):
        from viznoir.anim.transitions import dissolve
        result = dissolve(_red_image(), _blue_image(), 1.0)
        r, g, b, a = result.getpixel((50, 50))
        assert r == 0 and b == 255

    def test_t05_is_blend(self):
        from viznoir.anim.transitions import dissolve
        result = dissolve(_red_image(), _blue_image(), 0.5)
        r, g, b, a = result.getpixel((50, 50))
        assert 100 < r < 200  # approximately blended


class TestWipe:
    def test_wipe_left_t0(self):
        from viznoir.anim.transitions import wipe
        result = wipe(_red_image(), _blue_image(), 0.0, direction="left")
        # At t=0, should be all source (red)
        r, g, b, a = result.getpixel((50, 50))
        assert r == 255

    def test_wipe_left_t1(self):
        from viznoir.anim.transitions import wipe
        result = wipe(_red_image(), _blue_image(), 1.0, direction="left")
        # At t=1, should be all target (blue)
        r, g, b, a = result.getpixel((50, 50))
        assert b == 255


class TestGetTransition:
    def test_known_transitions(self):
        from viznoir.anim.transitions import get_transition
        for name in ["fade_in", "fade_out", "dissolve", "wipe_left", "wipe_right"]:
            fn = get_transition(name)
            assert callable(fn)

    def test_unknown_raises(self):
        from viznoir.anim.transitions import get_transition
        import pytest
        with pytest.raises(KeyError):
            get_transition("nonexistent")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_anim/test_timeline.py tests/test_anim/test_transitions.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement `anim/timeline.py` and `anim/transitions.py`**

`src/viznoir/anim/timeline.py` (~120 LOC):
```python
"""Scene timeline — manages scene sequencing and duration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Scene:
    """A single scene in the timeline."""
    asset_indices: list[int]
    duration: float = 3.0
    transition: str = "fade_in"
    equation_entrance: str | None = None


@dataclass
class Timeline:
    """Ordered sequence of scenes with timing."""
    scenes: list[Scene]
    fps: int = 30

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    @property
    def frame_count(self) -> int:
        return int(self.total_duration * self.fps)

    def scene_at(self, global_t: float) -> tuple[int, float]:
        """Return (scene_index, local_t) for a given global time.

        local_t is normalized [0, 1] within the scene.
        """
        if not self.scenes:
            return (0, 0.0)

        t = max(0.0, min(global_t, self.total_duration))
        elapsed = 0.0
        for i, scene in enumerate(self.scenes):
            if elapsed + scene.duration >= t or i == len(self.scenes) - 1:
                local = (t - elapsed) / scene.duration if scene.duration > 0 else 0.0
                return (i, min(local, 1.0))
            elapsed += scene.duration
        return (len(self.scenes) - 1, 1.0)

    def frame_times(self) -> list[float]:
        """Generate list of global times for each frame."""
        if self.frame_count == 0:
            return []
        dt = 1.0 / self.fps
        return [i * dt for i in range(self.frame_count)]
```

`src/viznoir/anim/transitions.py` (~150 LOC):
```python
"""Scene transitions — fade, dissolve, wipe effects."""

from __future__ import annotations

from typing import Callable

import numpy as np
from PIL import Image


def fade_in(img: Image.Image, t: float) -> Image.Image:
    """Fade from transparent to opaque."""
    alpha = int(255 * max(0.0, min(1.0, t)))
    result = img.copy().convert("RGBA")
    r, g, b, a = result.split()
    a = a.point(lambda x: int(x * alpha / 255))
    return Image.merge("RGBA", (r, g, b, a))


def fade_out(img: Image.Image, t: float) -> Image.Image:
    """Fade from opaque to transparent."""
    return fade_in(img, 1.0 - t)


def dissolve(src: Image.Image, dst: Image.Image, t: float) -> Image.Image:
    """Cross-dissolve between two images."""
    t = max(0.0, min(1.0, t))
    src_rgba = src.convert("RGBA")
    dst_rgba = dst.convert("RGBA")
    return Image.blend(src_rgba, dst_rgba, t)


def wipe(
    src: Image.Image,
    dst: Image.Image,
    t: float,
    direction: str = "left",
) -> Image.Image:
    """Wipe transition between two images."""
    t = max(0.0, min(1.0, t))
    w, h = src.size
    result = src.copy().convert("RGBA")
    dst_rgba = dst.convert("RGBA")

    if direction == "left":
        cut = int(w * t)
        if cut > 0:
            result.paste(dst_rgba.crop((0, 0, cut, h)), (0, 0))
    elif direction == "right":
        cut = int(w * (1 - t))
        if cut < w:
            result.paste(dst_rgba.crop((cut, 0, w, h)), (cut, 0))
    elif direction == "down":
        cut = int(h * t)
        if cut > 0:
            result.paste(dst_rgba.crop((0, 0, w, cut)), (0, 0))
    elif direction == "up":
        cut = int(h * (1 - t))
        if cut < h:
            result.paste(dst_rgba.crop((0, cut, w, h)), (0, cut))

    return result


# Registry
_TRANSITIONS: dict[str, Callable] = {
    "fade_in": fade_in,
    "fade_out": fade_out,
    "dissolve": dissolve,
    "wipe_left": lambda src, dst, t: wipe(src, dst, t, "left"),
    "wipe_right": lambda src, dst, t: wipe(src, dst, t, "right"),
    "wipe_down": lambda src, dst, t: wipe(src, dst, t, "down"),
    "wipe_up": lambda src, dst, t: wipe(src, dst, t, "up"),
}


def get_transition(name: str) -> Callable:
    """Get a transition function by name."""
    if name not in _TRANSITIONS:
        raise KeyError(f"Unknown transition: {name}. Available: {list(_TRANSITIONS.keys())}")
    return _TRANSITIONS[name]
```

**Step 4: Run tests**

Run: `pytest tests/test_anim/test_timeline.py tests/test_anim/test_transitions.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/anim/timeline.py src/viznoir/anim/transitions.py \
    tests/test_anim/test_timeline.py tests/test_anim/test_transitions.py
git commit -m "feat(anim): add timeline scene sequencing + transition effects"
```

---

### Task 4: Compositor + `compose_assets` MCP Tool

**Files:**
- Create: `src/viznoir/anim/compositor.py`
- Create: `src/viznoir/tools/compose.py`
- Modify: `src/viznoir/server.py` (add compose_assets tool)
- Test: `tests/test_anim/test_compositor.py`
- Test: `tests/test_tools/test_compose_tool.py`

**Step 1: Write failing tests**

```python
# tests/test_anim/test_compositor.py
"""Tests for anim/compositor.py — frame compositing + video export."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image


def _make_asset_image(color=(255, 0, 0, 255), size=(200, 150)):
    return Image.new("RGBA", size, color)


class TestRenderStoryLayout:
    def test_returns_image(self):
        from viznoir.anim.compositor import render_story_layout
        assets = [_make_asset_image(), _make_asset_image((0, 0, 255, 255))]
        labels = ["Panel A", "Panel B"]
        result = render_story_layout(assets, labels, width=800, height=600)
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)

    def test_single_asset(self):
        from viznoir.anim.compositor import render_story_layout
        result = render_story_layout([_make_asset_image()], ["Solo"], width=800, height=600)
        assert result.size == (800, 600)


class TestRenderGridLayout:
    def test_returns_correct_size(self):
        from viznoir.anim.compositor import render_grid_layout
        assets = [_make_asset_image() for _ in range(4)]
        result = render_grid_layout(assets, cols=2, width=800, height=600)
        assert isinstance(result, Image.Image)

    def test_single_column(self):
        from viznoir.anim.compositor import render_grid_layout
        assets = [_make_asset_image() for _ in range(3)]
        result = render_grid_layout(assets, cols=1, width=400, height=900)
        assert result.size == (400, 900)


class TestRenderSlidesLayout:
    def test_returns_list_of_images(self):
        from viznoir.anim.compositor import render_slides_layout
        assets = [_make_asset_image(), _make_asset_image((0, 255, 0, 255))]
        results = render_slides_layout(assets, ["Slide 1", "Slide 2"], width=1920, height=1080)
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, Image.Image) for r in results)


class TestExportVideo:
    def test_export_creates_file(self, tmp_path):
        from viznoir.anim.compositor import export_video
        frames = [_make_asset_image(size=(320, 240)) for _ in range(10)]
        out = tmp_path / "test.mp4"
        # Mock ffmpeg subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            export_video(frames, out, fps=10)
            mock_run.assert_called_once()
```

```python
# tests/test_tools/test_compose_tool.py
"""Tests for compose_assets MCP tool."""

from __future__ import annotations


class TestComposeAssetsTool:
    async def test_tool_registered(self):
        from fastmcp import Client
        from viznoir.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert "compose_assets" in names
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_anim/test_compositor.py tests/test_tools/test_compose_tool.py -v`
Expected: FAIL

**Step 3: Implement**

`src/viznoir/anim/compositor.py` (~250 LOC):
```python
"""Frame compositor — layout rendering and video export."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    pass

BG_COLOR = (0x1C, 0x1C, 0x2E, 255)
TEXT_WHITE = (255, 255, 255, 255)
TEXT_DIM = (0x88, 0x92, 0xB0, 255)
ACCENT_TEAL = (0x00, 0xD4, 0xAA, 255)


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def render_story_layout(
    assets: list[Image.Image],
    labels: list[str] | None = None,
    *,
    title: str | None = None,
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Compose assets into a single story-style dashboard."""
    canvas = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    if title:
        font_title = _get_font(28)
        draw.text((30, 15), title, fill=ACCENT_TEAL, font=font_title)
        y_start = 60
    else:
        y_start = 20

    if not assets:
        return canvas

    # Auto-layout: distribute assets in a row
    n = len(assets)
    padding = 20
    avail_w = width - padding * (n + 1)
    avail_h = height - y_start - 60  # leave room for labels
    panel_w = avail_w // n
    panel_h = avail_h

    for i, asset in enumerate(assets):
        x = padding + i * (panel_w + padding)
        y = y_start

        # Resize asset to fit panel
        asset_ratio = asset.width / asset.height
        panel_ratio = panel_w / panel_h
        if asset_ratio > panel_ratio:
            new_w = panel_w
            new_h = int(panel_w / asset_ratio)
        else:
            new_h = panel_h
            new_w = int(panel_h * asset_ratio)

        resized = asset.resize((new_w, new_h), Image.LANCZOS)
        paste_x = x + (panel_w - new_w) // 2
        paste_y = y + (panel_h - new_h) // 2
        canvas.paste(resized, (paste_x, paste_y), resized)

        # Label
        if labels and i < len(labels):
            font_label = _get_font(14)
            draw.text((x, height - 40), labels[i], fill=TEXT_DIM, font=font_label)

    return canvas


def render_grid_layout(
    assets: list[Image.Image],
    cols: int = 2,
    *,
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Compose assets into an N×M grid."""
    canvas = Image.new("RGBA", (width, height), BG_COLOR)

    if not assets:
        return canvas

    rows = (len(assets) + cols - 1) // cols
    padding = 10
    cell_w = (width - padding * (cols + 1)) // cols
    cell_h = (height - padding * (rows + 1)) // rows

    for i, asset in enumerate(assets):
        row, col = divmod(i, cols)
        x = padding + col * (cell_w + padding)
        y = padding + row * (cell_h + padding)

        # Fit asset into cell
        asset_resized = asset.copy()
        asset_resized.thumbnail((cell_w, cell_h), Image.LANCZOS)
        paste_x = x + (cell_w - asset_resized.width) // 2
        paste_y = y + (cell_h - asset_resized.height) // 2
        canvas.paste(asset_resized, (paste_x, paste_y), asset_resized)

    return canvas


def render_slides_layout(
    assets: list[Image.Image],
    labels: list[str] | None = None,
    *,
    width: int = 1920,
    height: int = 1080,
) -> list[Image.Image]:
    """Create one slide image per asset."""
    slides = []
    for i, asset in enumerate(assets):
        slide = Image.new("RGBA", (width, height), BG_COLOR)
        draw = ImageDraw.Draw(slide)

        # Center the asset
        asset_copy = asset.copy()
        max_w, max_h = width - 80, height - 120
        asset_copy.thumbnail((max_w, max_h), Image.LANCZOS)
        x = (width - asset_copy.width) // 2
        y = (height - asset_copy.height) // 2
        slide.paste(asset_copy, (x, y), asset_copy)

        # Label
        if labels and i < len(labels):
            font = _get_font(24)
            draw.text((40, height - 50), labels[i], fill=TEXT_WHITE, font=font)

        slides.append(slide)

    return slides


def export_video(
    frames: list[Image.Image],
    output_path: Path,
    *,
    fps: int = 30,
    preset: str = "medium",
) -> None:
    """Export frames to MP4 via ffmpeg pipe."""
    if not frames:
        return

    w, h = frames[0].size

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", preset,
        "-crf", "23",
        str(output_path),
    ]

    proc = subprocess.run(
        cmd,
        input=b"".join(f.convert("RGBA").tobytes() for f in frames),
        capture_output=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode(errors='replace')[:500]}")
```

`src/viznoir/tools/compose.py` (~120 LOC):
```python
"""compose_assets tool — combine assets into deliverable formats."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from viznoir.core.output import PipelineResult


async def compose_assets_impl(
    assets: list[dict[str, Any]],
    *,
    layout: str = "story",
    title: str | None = None,
    width: int = 1920,
    height: int = 1080,
    scenes: list[dict[str, Any]] | None = None,
    fps: int = 30,
    output_dir: str = "/tmp/viznoir-compose",
) -> dict[str, Any]:
    """Compose assets into the requested layout format."""
    import asyncio

    def _run():
        from PIL import Image as PILImage
        from viznoir.anim.compositor import (
            render_story_layout,
            render_grid_layout,
            render_slides_layout,
            export_video,
        )
        from viznoir.anim.latex import render_latex

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Load/generate asset images
        images = []
        labels = []
        for asset in assets:
            atype = asset.get("type", "render")
            label = asset.get("label", "")
            labels.append(label)

            if atype == "render" and "path" in asset:
                images.append(PILImage.open(asset["path"]).convert("RGBA"))
            elif atype == "latex" and "tex" in asset:
                color = asset.get("color", "FFFFFF")
                images.append(render_latex(asset["tex"], color=color))
            elif atype == "plot" and "path" in asset:
                images.append(PILImage.open(asset["path"]).convert("RGBA"))
            elif atype == "text":
                # Simple text card
                img = PILImage.new("RGBA", (400, 100), (0x1C, 0x1C, 0x2E, 255))
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), asset.get("content", ""), fill=(255, 255, 255, 255))
                images.append(img)
            else:
                # Placeholder
                images.append(PILImage.new("RGBA", (200, 150), (100, 100, 100, 255)))

        if layout == "story":
            result_img = render_story_layout(images, labels, title=title, width=width, height=height)
            path = out / "story.png"
            result_img.save(str(path))
            return {"output": str(path), "layout": "story", "assets_count": len(images)}

        elif layout == "grid":
            cols = min(len(images), 3)
            result_img = render_grid_layout(images, cols=cols, width=width, height=height)
            path = out / "grid.png"
            result_img.save(str(path))
            return {"output": str(path), "layout": "grid", "assets_count": len(images)}

        elif layout == "slides":
            slides = render_slides_layout(images, labels, width=width, height=height)
            paths = []
            for i, slide in enumerate(slides):
                p = out / f"slide_{i:03d}.png"
                slide.save(str(p))
                paths.append(str(p))
            return {"output": paths, "layout": "slides", "slides_count": len(slides)}

        elif layout == "video":
            if not scenes:
                # Auto-generate scenes from assets
                scenes = [{"assets": [i], "duration": 3.0, "transition": "fade_in"} for i in range(len(images))]

            from viznoir.anim.timeline import Scene, Timeline
            from viznoir.anim.transitions import get_transition

            tl_scenes = [
                Scene(
                    asset_indices=s.get("assets", [0]),
                    duration=s.get("duration", 3.0),
                    transition=s.get("transition", "fade_in"),
                )
                for s in scenes
            ]
            tl = Timeline(tl_scenes, fps=fps)

            # Render frames
            frames = []
            bg = PILImage.new("RGBA", (width, height), (0x1C, 0x1C, 0x2E, 255))
            for t in tl.frame_times():
                scene_idx, local_t = tl.scene_at(t)
                scene = tl_scenes[scene_idx]

                # Compose current scene's assets
                scene_assets = [images[i] for i in scene.asset_indices if i < len(images)]
                if not scene_assets:
                    frames.append(bg.copy())
                    continue

                frame = render_story_layout(scene_assets, width=width, height=height)

                # Apply transition (first 20% of scene)
                trans_duration = 0.2
                if local_t < trans_duration and scene.transition:
                    try:
                        trans_fn = get_transition(scene.transition)
                        trans_t = local_t / trans_duration
                        if scene.transition in ("fade_in",):
                            frame = trans_fn(frame, trans_t)
                        elif scene.transition in ("fade_out",):
                            frame = trans_fn(frame, trans_t)
                        else:
                            frame = trans_fn(bg, frame, trans_t)
                    except (KeyError, TypeError):
                        pass

                frames.append(frame)

            path = out / "video.mp4"
            export_video(frames, path, fps=fps)
            return {
                "output": str(path),
                "layout": "video",
                "duration": tl.total_duration,
                "frames": len(frames),
            }

        else:
            raise ValueError(f"Unknown layout: {layout}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)
```

Add to `src/viznoir/server.py` (after `analyze_data`):
```python
@mcp.tool()
async def compose_assets(
    assets: list[dict[str, Any]],
    layout: Literal["story", "grid", "slides", "video"] = "story",
    title: str | None = None,
    width: int = 1920,
    height: int = 1080,
    scenes: list[dict[str, Any]] | None = None,
    fps: int = 30,
) -> dict[str, Any] | Image:
    """Compose multiple assets into a deliverable format.

    Supports four layout modes:
    - story: Single dashboard image (1920x1080) — 3Blue1Brown style
    - grid: N×M grid for paper figures
    - slides: One PNG per asset for presentations (Marp/PPT input)
    - video: MP4 with scene transitions + easing

    Asset types:
    - {"type": "render", "path": "/output/render.png", "label": "Description"}
    - {"type": "latex", "tex": "E=mc^2", "color": "00D4AA", "label": "Energy"}
    - {"type": "plot", "path": "/output/graph.png", "label": "Time series"}
    - {"type": "text", "content": "Key finding here", "label": "Insight"}

    For video layout, provide scenes:
    [{"assets": [0, 1], "duration": 4.0, "transition": "dissolve"}]

    Available transitions: fade_in, fade_out, dissolve, wipe_left, wipe_right

    Args:
        assets: List of asset definitions
        layout: Output format — story, grid, slides, video
        title: Optional title text
        width: Output width in pixels
        height: Output height in pixels
        scenes: Scene definitions for video layout
        fps: Frames per second for video layout
    """
    logger.debug("tool.compose_assets: layout=%s assets=%d", layout, len(assets))
    t0 = time.monotonic()
    from viznoir.tools.compose import compose_assets_impl

    result = await compose_assets_impl(
        assets, layout=layout, title=title, width=width, height=height,
        scenes=scenes, fps=fps,
    )
    logger.debug("tool.compose_assets: done in %.2fs", time.monotonic() - t0)
    return result
```

**Step 4: Run tests**

Run: `pytest tests/test_anim/test_compositor.py tests/test_tools/test_compose_tool.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/anim/compositor.py src/viznoir/tools/compose.py src/viznoir/server.py \
    tests/test_anim/test_compositor.py tests/test_tools/test_compose_tool.py
git commit -m "feat: add compose_assets MCP tool + compositor layouts + video export"
```

---

### Task 5: Story Planning Prompt + Storytelling Resource

**Files:**
- Modify: `src/viznoir/prompts/guides.py` (add story_planning prompt)
- Modify: `src/viznoir/resources/catalog.py` (add storytelling resource)
- Modify: `tests/test_tools/test_mcp_integration.py` (update tool count 19→21, add prompt/resource checks)

**Step 1: Write failing tests**

Update `tests/test_tools/test_mcp_integration.py`:
- Change `test_list_tools_returns_19` → `test_list_tools_returns_21` (assert `== 21`)
- Add `"analyze_data"` and `"compose_assets"` to `expected_names` set
- Add test for `story_planning` prompt
- Add test for `viznoir://storytelling` resource

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools/test_mcp_integration.py -v`
Expected: FAIL (count mismatch, missing prompt/resource)

**Step 3: Implement**

Add `story_planning` prompt to `src/viznoir/prompts/guides.py` (in `register_prompts`, after `visualization_guide`):
```python
    @mcp.prompt()
    def story_planning(domain: str = "cfd") -> str:
        """Guide for creating a data-driven story from analyze_data results."""
        return _STORY_PLANNING_GUIDE.replace("{domain}", domain)
```

Add guide content:
```python
_STORY_PLANNING_GUIDE = """\
# Science Storytelling Guide ({domain})

You have an analysis report from viznoir's analyze_data tool.
Create a storyline that explains the key physics to a non-expert.

## Narrative Structure

1. **HOOK** — Start with the most surprising finding
   "At this point, pressure spikes 3x — here's why that matters"

2. **CONTEXT** — What is this simulation? Why does it matter?
   Use overview render (isometric, cinematic lighting)

3. **EVIDENCE** — Execute recommended_views from the analysis
   Each view should reveal one insight. Order: overview → detail → extreme

4. **EQUATION** — Place suggested_equations after the phenomenon they explain
   Use viznoir's LaTeX rendering (supports full LaTeX: underbrace, frac, etc.)

5. **CONCLUSION** — Engineering judgment
   "This design needs reinforcement at location X" or "Flow separation is acceptable"

## How to Use viznoir Tools

For each scene in your story:
1. Pick a recommended_view from analyze_data results
2. Call the corresponding tool (render, slice, contour, streamlines)
3. Add LaTeX equations as compose_assets entries
4. Use compose_assets to combine into final deliverable

## compose_assets Format

```json
{
  "assets": [
    {"type": "render", "path": "/output/overview.png", "label": "Flow overview"},
    {"type": "latex", "tex": "Re = \\\\frac{\\\\rho U L}{\\\\mu}", "color": "00D4AA"},
    {"type": "text", "content": "Reynolds number indicates turbulent regime"}
  ],
  "layout": "story"
}
```

## Output Options
- story: Single image dashboard (quick sharing)
- grid: Multi-panel figure (paper/report)
- slides: PNG sequence (presentation)
- video: MP4 with transitions (conference talk)
"""
```

Add `viznoir://storytelling` resource to `src/viznoir/resources/catalog.py`:
```python
    @mcp.resource("viznoir://storytelling")
    def storytelling_resource() -> str:
        return json.dumps(_STORYTELLING_DATA, indent=2)
```

```python
_STORYTELLING_DATA = {
    "scene_templates": {
        "overview": {"camera": "isometric", "lighting": "cinematic", "purpose": "Full domain overview"},
        "zoom_anomaly": {"camera": "custom", "lighting": "dramatic", "purpose": "Anomaly close-up"},
        "cross_section": {"tool": "slice", "lighting": "publication", "purpose": "Internal structure"},
        "equation_overlay": {"tool": "compose_assets", "purpose": "Physics law connection"},
    },
    "narrative_patterns": {
        "cfd": ["overview", "streamlines", "pressure_slice", "vorticity", "equation", "conclusion"],
        "fea": ["overview", "stress_contour", "deformation", "hotspot_zoom", "safety_factor", "conclusion"],
        "thermal": ["overview", "temperature_field", "heat_flux", "boundary_detail", "equation", "conclusion"],
    },
    "annotation_styles": {
        "insight": {"color": "#00D4AA", "font_weight": "bold"},
        "warning": {"color": "#FF6B6B", "font_weight": "bold"},
        "reference": {"color": "#8892B0", "font_weight": "normal"},
    },
}
```

**Step 4: Run tests**

Run: `pytest tests/test_tools/test_mcp_integration.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/viznoir/prompts/guides.py src/viznoir/resources/catalog.py \
    tests/test_tools/test_mcp_integration.py
git commit -m "feat: add story_planning prompt + storytelling resource"
```

---

### Task 6: Full Integration Test + CLAUDE.md Update

**Files:**
- Modify: `CLAUDE.md` (update tool count 19→21, add new modules)
- Create: `tests/test_tools/test_storytelling_e2e.py` (end-to-end integration test)

**Step 1: Write e2e integration test**

```python
# tests/test_tools/test_storytelling_e2e.py
"""End-to-end test: analyze_data → compose_assets pipeline."""

from __future__ import annotations

import vtk
import pytest
from pathlib import Path


def _make_wavelet_file(tmp_path: Path) -> str:
    """Create a wavelet VTK file for testing."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-8, 8, -8, 8, -8, 8)
    src.Update()

    writer = vtk.vtkXMLImageDataWriter()
    path = str(tmp_path / "wavelet.vti")
    writer.SetFileName(path)
    writer.SetInputData(src.GetOutput())
    writer.Write()
    return path


class TestAnalyzeToComposePipeline:
    def test_analyze_returns_insights(self):
        from viznoir.engine.analysis import analyze_dataset
        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(-8, 8, -8, 8, -8, 8)
        src.Update()
        report = analyze_dataset(src.GetOutput())

        assert report["summary"]["num_points"] > 0
        assert len(report["field_analyses"]) >= 1
        assert len(report["suggested_equations"]) >= 1

        # Verify recommended_views have usable params
        for fa in report["field_analyses"]:
            for view in fa["recommended_views"]:
                assert "type" in view
                assert "params" in view

    def test_compose_story_from_latex(self, tmp_path):
        from viznoir.anim.compositor import render_story_layout
        from viznoir.anim.latex import render_latex

        eq = render_latex(r"\nabla \cdot \mathbf{u} = 0", color="00D4AA")
        result = render_story_layout([eq], ["Continuity equation"], width=800, height=400)
        assert result.size == (800, 400)

        path = tmp_path / "story.png"
        result.save(str(path))
        assert path.exists()
```

**Step 2: Update CLAUDE.md**

- Tools: 19 → 21 (add analyze_data, compose_assets)
- Resources: 11 → 12 (add viznoir://storytelling)
- Prompts: 3 → 4 (add story_planning)
- Add `engine/analysis.py`, `anim/timeline.py`, `anim/transitions.py`, `anim/compositor.py`, `tools/analyze.py`, `tools/compose.py` to architecture section

**Step 3: Run full test suite**

Run: `pytest --cov=viznoir --cov-report=term-missing -q`
Expected: All tests pass, coverage ≥ 95%

**Step 4: Commit**

```bash
git add CLAUDE.md tests/test_tools/test_storytelling_e2e.py
git commit -m "feat: v0.5.0 Science Storyteller — full integration + docs update"
```

---

## Task Dependency Graph

```
Task 1 (engine/analysis.py)
  ↓
Task 2 (analyze_data tool + LaTeX cache)
  ↓                    Task 3 (timeline + transitions) ← independent
  ↓                      ↓
Task 4 (compositor + compose_assets) ← depends on Task 3
  ↓
Task 5 (prompt + resource)
  ↓
Task 6 (integration test + docs)
```

**Parallelizable**: Task 1 and Task 3 have zero file overlap → can run simultaneously.
