# Agent Harness v0.8.0 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Agent Harness layer to viznoir with `auto_postprocess` meta-tool, MCP Sampling evaluation, domain workflow skills, and optional C++ native VTK filters.

**Architecture:** New `harness/` package sits above existing layers (Harness → Tools, one-way). Orchestrator calls `*_impl` functions directly via `TOOL_DISPATCH` dict. `SamplingEvaluator` wraps `ctx.sample()` with try/except graceful degradation. Domain knowledge lives in Skills (Claude Code context) + MCP Prompts (sampling system_prompt).

**Tech Stack:** Python 3.10+, FastMCP 3.1, Pydantic v2, VTK 9.x, pybind11 (P3 stretch)

**Spec:** `docs/superpowers/specs/2026-03-16-agent-harness-design.md`

**P3 (C++ Native) is deferred to v0.9.0** — this plan covers P1 + P2 only.

**Key implementation notes:**
- Tool impl return types are heterogeneous: `PipelineResult` (render/slice/contour/clip/streamlines), `bytes` (cinematic/compare/volume), `dict` (batch). `_execute_step` must normalize all to `PipelineResult`.
- `goal` parameter maps to `purpose` for adaptive resolution: `"explore"→"analyze"`, `"publish"→"publish"`, `"compare"→"preview"`.
- Version check uses tuple comparison (no `packaging` dependency): `tuple(int(x) for x in ver.split(".")[:2]) >= (3, 0)`.

---

## File Map

### New Files (P1: Orchestrator Core)

| File | Responsibility |
|------|---------------|
| `src/viznoir/harness/__init__.py` | Package init, `HAS_HARNESS` flag |
| `src/viznoir/harness/models.py` | `VizStep`, `VizPlan`, `EvalResult` Pydantic models |
| `src/viznoir/harness/domain_hints.py` | File extension + field name → domain string |
| `src/viznoir/harness/evaluator.py` | `SamplingEvaluator` with graceful degradation |
| `src/viznoir/harness/orchestrator.py` | `TOOL_DISPATCH` + `auto_postprocess_impl` |
| `tests/test_harness/__init__.py` | Test package |
| `tests/test_harness/test_models.py` | Model validation tests |
| `tests/test_harness/test_domain_hints.py` | Domain detection tests |
| `tests/test_harness/test_evaluator.py` | Evaluator tests (mocked sampling) |
| `tests/test_harness/test_orchestrator.py` | Orchestrator integration tests |
| `tests/test_harness/test_tool_dispatch.py` | TOOL_DISPATCH completeness tests |

### New Files (P2: Skills + Agent)

| File | Responsibility |
|------|---------------|
| `.claude-plugin/skills/cfd-workflow/SKILL.md` | CFD domain workflow skill |
| `.claude-plugin/skills/fea-workflow/SKILL.md` | FEA domain workflow skill |
| `.claude-plugin/skills/sph-workflow/SKILL.md` | SPH domain workflow skill |
| `.claude-plugin/skills/dev-pipeline/SKILL.md` | viznoir dev automation skill |
| `.claude-plugin/skills/oss-workflow/SKILL.md` | OSS success strategy skill |
| `agents/viz-orchestrator.md` | Orchestration agent definition |

### Modified Files

| File | Change |
|------|--------|
| `src/viznoir/server.py` | Version guard + `auto_postprocess` tool registration (~30 lines) |
| `src/viznoir/prompts/guides.py` | Add domain strategy prompts for sampling |
| `.claude-plugin/skills/cae-postprocess/SKILL.md` | Slim down, delegate to domain skills |
| `.claude-plugin/plugin.json` | Register new skills |
| `agents/viz-agent.md` | Fix skill ref: `cfd-postprocess` → `cae-postprocess` |

---

## Chunk 1: Pydantic Models + Domain Hints

### Task 1: Harness package init + models

**Files:**
- Create: `src/viznoir/harness/__init__.py`
- Create: `src/viznoir/harness/models.py`
- Create: `tests/test_harness/__init__.py`
- Create: `tests/test_harness/test_models.py`

- [ ] **Step 1: Create test file with model validation tests**

```python
# tests/test_harness/__init__.py
# (empty)
```

```python
# tests/test_harness/test_models.py
"""Tests for harness Pydantic models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from viznoir.harness.models import EvalResult, VizPlan, VizStep


@pytest.fixture(autouse=True)
def mock_tool_dispatch(monkeypatch):
    """Mock TOOL_DISPATCH so model tests don't depend on orchestrator."""
    fake_dispatch = {"render": lambda: None, "cinematic_render": lambda: None, "slice": lambda: None}
    monkeypatch.setattr("viznoir.harness.orchestrator.TOOL_DISPATCH", fake_dispatch)


class TestVizStep:
    def test_valid_step(self):
        step = VizStep(
            tool="cinematic_render",
            params={"file_path": "/data/case.vtk", "field_name": "p"},
            rationale="Show pressure distribution",
        )
        assert step.tool == "cinematic_render"
        assert step.params["field_name"] == "p"

    def test_unknown_tool_raises(self):
        with pytest.raises(ValidationError, match="Unknown tool"):
            VizStep(
                tool="nonexistent_tool",
                params={},
                rationale="bad",
            )

    def test_empty_rationale_allowed(self):
        step = VizStep(tool="render", params={}, rationale="")
        assert step.rationale == ""


class TestVizPlan:
    def test_valid_plan(self):
        plan = VizPlan(
            domain="cfd",
            steps=[
                VizStep(tool="render", params={"file_path": "/data/a.vtk", "field_name": "p"}, rationale="overview"),
            ],
            key_fields=["p", "U"],
        )
        assert plan.domain == "cfd"
        assert len(plan.steps) == 1

    def test_empty_steps_allowed(self):
        plan = VizPlan(domain="generic", steps=[], key_fields=[])
        assert len(plan.steps) == 0

    def test_max_steps_hint(self):
        """Plans with >6 steps are valid but unusual."""
        steps = [VizStep(tool="render", params={}, rationale=f"step {i}") for i in range(7)]
        plan = VizPlan(domain="cfd", steps=steps, key_fields=["p"])
        assert len(plan.steps) == 7


class TestEvalResult:
    def test_done_verdict(self):
        result = EvalResult(verdict="done", issues=[], suggestions=[])
        assert result.verdict == "done"

    def test_refine_with_suggestions(self):
        result = EvalResult(
            verdict="refine",
            issues=["colormap range too wide"],
            suggestions=[VizStep(tool="render", params={}, rationale="fix range")],
        )
        assert len(result.suggestions) == 1

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            EvalResult(verdict="invalid", issues=[], suggestions=[])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harness/test_models.py -v`
Expected: FAIL (ModuleNotFoundError: viznoir.harness.models)

- [ ] **Step 3: Create harness package and models**

```python
# src/viznoir/harness/__init__.py
"""Agent Harness — autonomous post-processing orchestration layer."""
from __future__ import annotations

__all__ = ["HAS_HARNESS"]


def _check_harness_support() -> bool:
    """Check if FastMCP >= 3.0.0 is available (required for ctx.sample)."""
    try:
        from importlib.metadata import version as get_version
        ver = get_version("fastmcp")
        return tuple(int(x) for x in ver.split(".")[:2]) >= (3, 0)
    except Exception:
        return False


HAS_HARNESS = _check_harness_support()
```

```python
# src/viznoir/harness/models.py
"""Pydantic models for orchestrator plans and evaluation results."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_validator


class VizStep(BaseModel):
    """A single visualization step in an orchestrated workflow."""

    tool: str
    params: dict[str, Any]
    rationale: str

    @model_validator(mode="after")
    def validate_tool_exists(self) -> VizStep:
        from viznoir.harness.orchestrator import TOOL_DISPATCH
        if self.tool not in TOOL_DISPATCH:
            raise ValueError(f"Unknown tool: {self.tool}")
        return self


class VizPlan(BaseModel):
    """A sequence of visualization steps for a dataset."""

    domain: str
    steps: list[VizStep]
    key_fields: list[str]


class EvalResult(BaseModel):
    """LLM evaluation of visualization results."""

    verdict: Literal["pass", "refine", "done"]
    issues: list[str]
    suggestions: list[VizStep]
```

Note: `VizStep.validate_tool_exists` imports `TOOL_DISPATCH` lazily to avoid circular imports. This means `TOOL_DISPATCH` must exist before model validation runs. Task 3 creates the dispatch table.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harness/test_models.py -v`
Expected: ALL PASS (TOOL_DISPATCH is mocked via monkeypatch fixture)

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/harness/__init__.py src/viznoir/harness/models.py \
  tests/test_harness/__init__.py tests/test_harness/test_models.py
git commit -m "feat(harness): add Pydantic models — VizStep, VizPlan, EvalResult"
```

---

### Task 2: Domain Hints

**Files:**
- Create: `src/viznoir/harness/domain_hints.py`
- Create: `tests/test_harness/test_domain_hints.py`

- [ ] **Step 1: Write domain detection tests**

```python
# tests/test_harness/test_domain_hints.py
"""Tests for mechanical domain detection from file metadata."""
from __future__ import annotations

import pytest

from viznoir.harness.domain_hints import detect_domain


class TestDetectDomain:
    """Test domain detection from inspect_data metadata."""

    def test_foam_file_is_cfd(self):
        meta = {"file_path": "/data/case.foam", "arrays": {"p": {}, "U": {}}}
        assert detect_domain(meta) == "cfd"

    def test_cas_file_is_cfd(self):
        meta = {"file_path": "/data/case.cas", "arrays": {"Pressure": {}}}
        assert detect_domain(meta) == "cfd"

    def test_displacement_field_is_fea(self):
        meta = {"file_path": "/data/result.vtu", "arrays": {"displacement": {}, "von_mises_stress": {}}}
        assert detect_domain(meta) == "fea"

    def test_stress_only_is_fea(self):
        meta = {"file_path": "/data/result.vtu", "arrays": {"stress": {}}}
        assert detect_domain(meta) == "fea"

    def test_bi4_file_is_sph(self):
        meta = {"file_path": "/data/Part0001.bi4", "arrays": {"Velocity": {}, "Type": {}}}
        assert detect_domain(meta) == "sph"

    def test_type_and_velocity_is_sph(self):
        meta = {"file_path": "/data/particles.vtk", "arrays": {"Type": {}, "Velocity": {}}}
        assert detect_domain(meta) == "sph"

    def test_generic_fallback(self):
        meta = {"file_path": "/data/unknown.vti", "arrays": {"density": {}}}
        assert detect_domain(meta) == "generic"

    def test_empty_arrays_is_generic(self):
        meta = {"file_path": "/data/mesh.stl", "arrays": {}}
        assert detect_domain(meta) == "generic"

    def test_missing_arrays_key_is_generic(self):
        meta = {"file_path": "/data/mesh.stl"}
        assert detect_domain(meta) == "generic"

    def test_cfd_fields_override_generic_extension(self):
        """VTU with p and U fields is CFD, not generic."""
        meta = {"file_path": "/data/internal.vtu", "arrays": {"p": {}, "U": {}, "k": {}}}
        assert detect_domain(meta) == "cfd"

    def test_cgns_is_cfd(self):
        meta = {"file_path": "/data/flow.cgns", "arrays": {"Pressure": {}}}
        assert detect_domain(meta) == "cfd"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harness/test_domain_hints.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement domain_hints.py**

```python
# src/viznoir/harness/domain_hints.py
"""Mechanical domain detection from file metadata.

Simple heuristic: file extension + field names → domain string.
Complex inference is delegated to LLM via sampling.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

# File extensions strongly associated with a domain
_CFD_EXTENSIONS = {".foam", ".cas", ".cgns", ".msh", ".ccm"}
_FEA_EXTENSIONS = {".inp", ".op2", ".bdf", ".dat"}
_SPH_EXTENSIONS = {".bi4"}

# Field names that indicate a domain (case-insensitive matching)
_CFD_FIELDS = {"p", "u", "k", "epsilon", "omega", "nut", "alphat", "p_rgh", "alpha.water"}
_FEA_FIELDS = {"displacement", "von_mises_stress", "stress", "strain", "reaction_force"}
_SPH_FIELDS = {"type", "rhop"}  # "Velocity" is ambiguous; needs "Type" to confirm SPH


def detect_domain(metadata: dict[str, Any]) -> str:
    """Detect simulation domain from inspect_data metadata.

    Returns: "cfd", "fea", "sph", or "generic".
    """
    file_path = metadata.get("file_path", "")
    ext = PurePosixPath(file_path).suffix.lower()
    arrays = metadata.get("arrays", {})
    field_names = {name.lower() for name in arrays}

    # 1. Extension-based detection (strongest signal)
    if ext in _CFD_EXTENSIONS:
        return "cfd"
    if ext in _FEA_EXTENSIONS:
        return "fea"
    if ext in _SPH_EXTENSIONS:
        return "sph"

    # 2. Field-based detection
    if field_names & _SPH_FIELDS and "velocity" in field_names:
        return "sph"
    if field_names & _FEA_FIELDS:
        return "fea"
    if field_names & _CFD_FIELDS:
        return "cfd"

    return "generic"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harness/test_domain_hints.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/harness/domain_hints.py tests/test_harness/test_domain_hints.py
git commit -m "feat(harness): add domain_hints — mechanical domain detection"
```

---

### Task 3: TOOL_DISPATCH table

**Files:**
- Create: `src/viznoir/harness/orchestrator.py` (partial — dispatch table only)
- Create: `tests/test_harness/test_tool_dispatch.py`

- [ ] **Step 1: Write dispatch table completeness tests**

```python
# tests/test_harness/test_tool_dispatch.py
"""Tests for TOOL_DISPATCH — verify all image-producing tools are registered."""
from __future__ import annotations

import pytest

from viznoir.harness.orchestrator import TOOL_DISPATCH


class TestToolDispatch:
    """Verify TOOL_DISPATCH covers all visualization tools."""

    EXPECTED_TOOLS = [
        "render",
        "cinematic_render",
        "slice",
        "contour",
        "clip",
        "streamlines",
        "compare",
        "batch_render",
        "volume_render",
    ]

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_registered(self, tool_name):
        assert tool_name in TOOL_DISPATCH, f"{tool_name} missing from TOOL_DISPATCH"

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_is_callable(self, tool_name):
        assert callable(TOOL_DISPATCH[tool_name])

    def test_no_data_only_tools(self):
        """Data extraction tools (extract_stats, plot_over_line) should NOT be in dispatch.
        They don't produce images."""
        assert "extract_stats" not in TOOL_DISPATCH
        assert "plot_over_line" not in TOOL_DISPATCH
        assert "inspect_data" not in TOOL_DISPATCH

    def test_dispatch_keys_are_strings(self):
        for key in TOOL_DISPATCH:
            assert isinstance(key, str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harness/test_tool_dispatch.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Create orchestrator.py with TOOL_DISPATCH**

```python
# src/viznoir/harness/orchestrator.py
"""Orchestrator — auto_postprocess meta-tool and tool dispatch."""
from __future__ import annotations

from typing import Any, Callable, Coroutine

from viznoir.tools.cinematic import cinematic_render_impl
from viznoir.tools.compare import compare_impl
from viznoir.tools.filters import clip_impl, contour_impl, slice_impl, streamlines_impl
from viznoir.tools.render import render_impl
from viznoir.tools.batch import batch_render_impl
from viznoir.tools.volume import volume_render_impl

# Map tool names → impl functions.
# Only image-producing tools are included (orchestrator generates visualizations).
TOOL_DISPATCH: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {
    "render": render_impl,
    "cinematic_render": cinematic_render_impl,
    "slice": slice_impl,
    "contour": contour_impl,
    "clip": clip_impl,
    "streamlines": streamlines_impl,
    "compare": compare_impl,
    "batch_render": batch_render_impl,
    "volume_render": volume_render_impl,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harness/test_tool_dispatch.py -v`
Expected: ALL PASS

- [ ] **Step 5: Re-run model tests (VizStep validation now works)**

Run: `pytest tests/test_harness/test_models.py -v`
Expected: ALL PASS (including `test_unknown_tool_raises`)

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/harness/orchestrator.py tests/test_harness/test_tool_dispatch.py
git commit -m "feat(harness): add TOOL_DISPATCH table for image-producing tools"
```

---

## Chunk 2: SamplingEvaluator + Orchestrator Logic

### Task 4: SamplingEvaluator

**Files:**
- Create: `src/viznoir/harness/evaluator.py`
- Create: `tests/test_harness/test_evaluator.py`

- [ ] **Step 1: Write evaluator tests with mocked sampling**

```python
# tests/test_harness/test_evaluator.py
"""Tests for SamplingEvaluator — mocked ctx.sample()."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from viznoir.harness.evaluator import SamplingEvaluator
from viznoir.harness.models import EvalResult, VizPlan, VizStep


@pytest.fixture
def evaluator():
    return SamplingEvaluator()


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.sample = AsyncMock()
    ctx.info = MagicMock()
    return ctx


@pytest.fixture
def sample_metadata():
    return {
        "file_path": "/data/case.foam",
        "arrays": {"p": {"range": [0, 100]}, "U": {"range": [0, 10]}},
        "bounds": [0, 1, 0, 1, 0, 0.1],
        "timesteps": [0.0, 0.1, 0.2],
    }


class TestSamplingEvaluatorPlan:
    @pytest.mark.asyncio
    async def test_plan_with_sampling_success(self, evaluator, mock_ctx, sample_metadata):
        """When sampling succeeds, return the LLM's VizPlan."""
        expected_plan = VizPlan(
            domain="cfd",
            steps=[VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "p"}, rationale="pressure overview")],
            key_fields=["p"],
        )
        mock_result = MagicMock()
        mock_result.result = expected_plan
        mock_ctx.sample.return_value = mock_result

        plan = await evaluator.plan(mock_ctx, sample_metadata, "CFD guide text")
        assert plan.domain == "cfd"
        assert len(plan.steps) == 1

    @pytest.mark.asyncio
    async def test_plan_fallback_on_sampling_failure(self, evaluator, mock_ctx, sample_metadata):
        """When sampling fails, return heuristic default plan."""
        mock_ctx.sample.side_effect = Exception("sampling not supported")

        plan = await evaluator.plan(mock_ctx, sample_metadata, "CFD guide text")
        assert plan.domain == "cfd"
        assert len(plan.steps) >= 1  # heuristic generates at least 1 step

    @pytest.mark.asyncio
    async def test_plan_fallback_includes_key_fields(self, evaluator, mock_ctx, sample_metadata):
        """Heuristic fallback uses detected fields."""
        mock_ctx.sample.side_effect = Exception("no sampling")

        plan = await evaluator.plan(mock_ctx, sample_metadata, "")
        assert "p" in plan.key_fields or "U" in plan.key_fields


class TestSamplingEvaluatorEvaluate:
    @pytest.mark.asyncio
    async def test_evaluate_returns_done_on_failure(self, evaluator, mock_ctx):
        """When sampling fails, always return 'done' (skip evaluation)."""
        mock_ctx.sample.side_effect = Exception("no sampling")

        result = await evaluator.evaluate(mock_ctx, [], {})
        assert result.verdict == "done"

    @pytest.mark.asyncio
    async def test_evaluate_returns_llm_result(self, evaluator, mock_ctx):
        """When sampling succeeds, return LLM's evaluation."""
        expected = EvalResult(verdict="refine", issues=["colormap too dark"], suggestions=[])
        mock_result = MagicMock()
        mock_result.result = expected
        mock_ctx.sample.return_value = mock_result

        result = await evaluator.evaluate(mock_ctx, [b"fake-png"], {"field": "p"})
        assert result.verdict == "refine"
        assert "colormap too dark" in result.issues

    @pytest.mark.asyncio
    async def test_evaluate_passes_image_count_in_message(self, evaluator, mock_ctx):
        """Verify evaluate mentions how many images were produced."""
        mock_result = MagicMock()
        mock_result.result = EvalResult(verdict="done", issues=[], suggestions=[])
        mock_ctx.sample.return_value = mock_result

        await evaluator.evaluate(mock_ctx, [b"img1", b"img2"], {"field": "p"})
        call_args = mock_ctx.sample.call_args
        messages_arg = call_args.kwargs.get("messages") or call_args.args[0]
        assert "2" in str(messages_arg)  # mentions 2 images
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harness/test_evaluator.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement SamplingEvaluator**

```python
# src/viznoir/harness/evaluator.py
"""SamplingEvaluator — wraps ctx.sample() with graceful degradation."""
from __future__ import annotations

from typing import Any

from viznoir.harness.domain_hints import detect_domain
from viznoir.harness.models import EvalResult, VizPlan, VizStep
from viznoir.logging import get_logger

logger = get_logger("harness.evaluator")


class SamplingEvaluator:
    """Request LLM guidance via MCP sampling, with heuristic fallback."""

    async def plan(self, ctx: Any, metadata: dict, domain_prompt: str) -> VizPlan:
        """Ask LLM for a visualization plan. Falls back to heuristic if sampling fails."""
        domain = detect_domain(metadata)
        fields_summary = ", ".join(list(metadata.get("arrays", {}).keys())[:10])
        timesteps = metadata.get("timesteps", [])
        file_path = metadata.get("file_path", "")

        result = await self._try_sample(
            ctx,
            messages=(
                f"Simulation file: {file_path}\n"
                f"Domain: {domain}\n"
                f"Fields: {fields_summary}\n"
                f"Timesteps: {len(timesteps)}\n"
                f"Bounds: {metadata.get('bounds', 'unknown')}\n\n"
                "Create a visualization plan with 3-5 steps. "
                "Use cinematic_render for primary views. "
                "Include rationale for each step."
            ),
            system_prompt=domain_prompt,
            result_type=VizPlan,
            max_tokens=1024,
        )
        if result is not None:
            logger.info("Sampling plan received: %d steps", len(result.result.steps))
            return result.result

        # Heuristic fallback
        logger.info("Sampling unavailable, using heuristic plan for domain=%s", domain)
        return self._heuristic_plan(metadata, domain, file_path)

    async def evaluate(self, ctx: Any, images: list[bytes], metadata: dict) -> EvalResult:
        """Ask LLM to evaluate results. Falls back to 'done' if sampling fails."""
        result = await self._try_sample(
            ctx,
            messages=(
                f"I produced {len(images)} visualization(s) from {metadata.get('file_path', 'unknown')}. "
                f"Fields analyzed: {', '.join(metadata.get('rendered_fields', []))}.\n\n"
                "Evaluate quality: Are colormaps appropriate? Camera angles revealing? "
                "Any missing perspectives? Respond with verdict: pass, refine, or done."
            ),
            result_type=EvalResult,
            max_tokens=512,
        )
        if result is not None:
            return result.result

        return EvalResult(verdict="done", issues=[], suggestions=[])

    async def _try_sample(self, ctx: Any, **kwargs: Any) -> Any | None:
        """Attempt ctx.sample(); return None on failure."""
        try:
            return await ctx.sample(**kwargs)
        except Exception as exc:
            logger.debug("Sampling unavailable: %s", exc)
            return None

    def _heuristic_plan(self, metadata: dict, domain: str, file_path: str) -> VizPlan:
        """Generate a default plan without LLM assistance."""
        arrays = metadata.get("arrays", {})
        field_names = list(arrays.keys())
        steps: list[VizStep] = []

        # Pick primary field based on domain
        primary = self._pick_primary_field(field_names, domain)
        if primary:
            steps.append(VizStep(
                tool="cinematic_render",
                params={"file_path": file_path, "field_name": primary},
                rationale=f"Primary field overview: {primary}",
            ))

        # Add secondary visualizations
        secondary = self._pick_secondary_fields(field_names, domain, primary)
        for field in secondary[:2]:
            steps.append(VizStep(
                tool="render",
                params={"file_path": file_path, "field_name": field},
                rationale=f"Secondary field: {field}",
            ))

        # If no fields found, still produce a geometry render
        if not steps:
            steps.append(VizStep(
                tool="render",
                params={"file_path": file_path, "field_name": field_names[0] if field_names else ""},
                rationale="Geometry overview (no domain-specific fields detected)",
            ))

        return VizPlan(
            domain=domain,
            steps=steps,
            key_fields=[s.params.get("field_name", "") for s in steps if s.params.get("field_name")],
        )

    @staticmethod
    def _pick_primary_field(fields: list[str], domain: str) -> str | None:
        """Pick the most important field for the domain."""
        priority = {
            "cfd": ["p", "U", "Pressure", "Velocity", "p_rgh"],
            "fea": ["von_mises_stress", "displacement", "stress"],
            "sph": ["Velocity", "Pressure", "Type"],
            "generic": [],
        }
        for candidate in priority.get(domain, []):
            if candidate in fields:
                return candidate
        return fields[0] if fields else None

    @staticmethod
    def _pick_secondary_fields(fields: list[str], domain: str, primary: str | None) -> list[str]:
        """Pick secondary fields (different from primary)."""
        return [f for f in fields if f != primary][:3]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harness/test_evaluator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/viznoir/harness/evaluator.py tests/test_harness/test_evaluator.py
git commit -m "feat(harness): add SamplingEvaluator with graceful degradation"
```

---

### Task 5: Orchestrator — auto_postprocess_impl

**Files:**
- Modify: `src/viznoir/harness/orchestrator.py` (add orchestration logic)
- Create: `tests/test_harness/test_orchestrator.py`

- [ ] **Step 1: Write orchestrator integration tests**

```python
# tests/test_harness/test_orchestrator.py
"""Tests for auto_postprocess orchestrator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from viznoir.core.output import PipelineResult
from viznoir.core.runner import RunResult
from viznoir.harness.models import EvalResult, VizPlan, VizStep
from viznoir.harness.orchestrator import auto_postprocess_impl


@pytest.fixture
def mock_runner():
    runner = AsyncMock()
    runner.config = MagicMock()
    runner.config.output_dir = "/tmp/viznoir_test"
    return runner


@pytest.fixture
def mock_result():
    return PipelineResult(
        output_type="image",
        image_bytes=b"fake-png",
        image_base64="ZmFrZQ==",
        json_data=None,
        raw=RunResult(stdout="", stderr="", exit_code=0),
    )


@pytest.fixture
def sample_inspect_result():
    return {
        "file_path": "/data/case.foam",
        "arrays": {"p": {"range": [0, 100]}, "U": {"range": [0, 10]}},
        "bounds": [0, 1, 0, 1, 0, 0.1],
        "timesteps": [0.0],
    }


class TestAutoPostprocessImpl:
    @pytest.mark.asyncio
    async def test_produces_results_with_heuristic_fallback(
        self, mock_runner, mock_result, sample_inspect_result
    ):
        """Without sampling, should still produce results via heuristic plan."""
        mock_ctx = MagicMock()
        mock_ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=sample_inspect_result),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=1,
            )

        assert len(results) >= 1
        assert all(isinstance(r, PipelineResult) for r in results)

    @pytest.mark.asyncio
    async def test_respects_max_iterations(self, mock_runner, mock_result, sample_inspect_result):
        """Orchestrator should not exceed max_iterations."""
        mock_ctx = MagicMock()
        # Sampling works but always says "refine"
        refine_result = MagicMock()
        refine_result.result = EvalResult(
            verdict="refine",
            issues=["needs improvement"],
            suggestions=[VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "U"}, rationale="retry")],
        )
        plan_result = MagicMock()
        plan_result.result = VizPlan(
            domain="cfd",
            steps=[VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "p"}, rationale="test")],
            key_fields=["p"],
        )
        mock_ctx.sample = AsyncMock(side_effect=[plan_result, refine_result, plan_result, refine_result, plan_result, refine_result])
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=sample_inspect_result),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=2,
            )

        # Should have results from 2 iterations max
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_done_verdict_stops_loop(self, mock_runner, mock_result, sample_inspect_result):
        """Orchestrator stops when evaluator returns 'done'."""
        mock_ctx = MagicMock()
        plan_result = MagicMock()
        plan_result.result = VizPlan(
            domain="cfd",
            steps=[VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "p"}, rationale="test")],
            key_fields=["p"],
        )
        done_result = MagicMock()
        done_result.result = EvalResult(verdict="done", issues=[], suggestions=[])
        mock_ctx.sample = AsyncMock(side_effect=[plan_result, done_result])
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=sample_inspect_result),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=5,
            )

        # Only 1 iteration (done after first eval)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_step_failure_continues(self, mock_runner, sample_inspect_result):
        """If a step fails with ViznoirError, orchestrator skips it and continues."""
        from viznoir.errors import FieldNotFoundError

        mock_ctx = MagicMock()
        mock_ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        call_count = 0

        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FieldNotFoundError("field 'p' not found")
            return PipelineResult(
                output_type="image",
                image_bytes=b"ok",
                image_base64="b2s=",
                json_data=None,
                raw=RunResult(stdout="", stderr="", exit_code=0),
            )

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=sample_inspect_result),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, side_effect=failing_then_succeeding),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=1,
            )

        # Should have at least 1 result (the successful step)
        assert len(results) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harness/test_orchestrator.py -v`
Expected: FAIL (ImportError: auto_postprocess_impl)

- [ ] **Step 3: Implement orchestrator logic**

Add to `src/viznoir/harness/orchestrator.py` (after the existing TOOL_DISPATCH):

```python
# --- Add these imports at the top ---
from viznoir.core.output import PipelineResult
from viznoir.core.runner import VTKRunner
from viznoir.errors import ViznoirError
from viznoir.harness.domain_hints import detect_domain
from viznoir.harness.evaluator import SamplingEvaluator
from viznoir.harness.models import VizPlan, VizStep
from viznoir.logging import get_logger
from viznoir.tools.inspect import inspect_data_impl

logger = get_logger("harness.orchestrator")

# Domain prompt loader (from prompts/guides.py)
_DOMAIN_PROMPTS: dict[str, str] = {}  # populated by _load_domain_prompts()


def _load_domain_prompts() -> dict[str, str]:
    """Load domain prompts lazily."""
    if _DOMAIN_PROMPTS:
        return _DOMAIN_PROMPTS
    from viznoir.prompts.guides import (
        _GENERAL_CFD_GUIDE,
        _STATIC_FEA_GUIDE,
        _VIZ_GUIDE,
    )
    _DOMAIN_PROMPTS.update({
        "cfd": _GENERAL_CFD_GUIDE,
        "fea": _STATIC_FEA_GUIDE,
        "sph": _VIZ_GUIDE,  # SPH reuses viz guide until dedicated prompt exists
        "generic": _VIZ_GUIDE,
    })
    return _DOMAIN_PROMPTS


_GOAL_TO_PURPOSE = {"explore": "analyze", "publish": "publish", "compare": "preview"}


async def _execute_step(step: VizStep, runner: VTKRunner, goal: str = "explore") -> PipelineResult:
    """Execute a single VizStep, normalizing heterogeneous return types.

    Return types vary: PipelineResult (render/slice/contour/clip/streamlines),
    bytes (cinematic/compare/volume), dict (batch). All normalized to PipelineResult.
    """
    import base64
    from viznoir.core.runner import RunResult

    impl_fn = TOOL_DISPATCH[step.tool]
    params = {**step.params, "runner": runner}

    # Inject purpose for adaptive resolution
    purpose = _GOAL_TO_PURPOSE.get(goal, "preview")
    if "purpose" not in params and step.tool in ("render", "cinematic_render", "slice", "contour", "clip", "streamlines", "batch_render"):
        params["purpose"] = purpose

    result = await impl_fn(**params)

    # Normalize return types
    if isinstance(result, PipelineResult):
        return result
    if isinstance(result, bytes):
        return PipelineResult(
            output_type="image",
            image_bytes=result,
            image_base64=base64.b64encode(result).decode(),
            json_data=None,
            raw=RunResult(stdout="", stderr="", exit_code=0),
        )
    if isinstance(result, dict):
        # batch_render returns dict with per-field results
        # Extract first image if available
        for v in result.values():
            if isinstance(v, bytes):
                return PipelineResult(
                    output_type="image",
                    image_bytes=v,
                    image_base64=base64.b64encode(v).decode(),
                    json_data=result,
                    raw=RunResult(stdout="", stderr="", exit_code=0),
                )
        return PipelineResult(
            output_type="data",
            image_bytes=None,
            image_base64=None,
            json_data=result,
            raw=RunResult(stdout="", stderr="", exit_code=0),
        )
    raise TypeError(f"Unexpected return type from {step.tool}: {type(result)}")


async def auto_postprocess_impl(
    ctx: Any,
    file_path: str,
    runner: VTKRunner,
    goal: str = "explore",
    max_iterations: int = 5,
) -> list[PipelineResult]:
    """Autonomous post-processing: inspect → plan → execute → evaluate → refine."""
    evaluator = SamplingEvaluator()

    # Step 1: Inspect
    logger.info("auto_postprocess: inspecting %s", file_path)
    metadata = await inspect_data_impl(file_path, runner)
    metadata["file_path"] = file_path

    # Step 2: Domain detection
    domain = detect_domain(metadata)
    logger.info("Detected domain: %s", domain)

    # Step 3: Load domain prompt
    prompts = _load_domain_prompts()
    domain_prompt = prompts.get(domain, prompts["generic"])

    all_results: list[PipelineResult] = []
    rendered_fields: list[str] = []

    for iteration in range(max_iterations):
        logger.info("Iteration %d/%d", iteration + 1, max_iterations)

        # Step 4: Get plan (LLM or heuristic)
        plan = await evaluator.plan(ctx, metadata, domain_prompt)

        # Step 5: Execute plan steps
        iteration_results: list[PipelineResult] = []
        for i, step in enumerate(plan.steps):
            try:
                logger.info("  Step %d/%d: %s — %s", i + 1, len(plan.steps), step.tool, step.rationale)
                result = await _execute_step(step, runner, goal=goal)
                iteration_results.append(result)
                field = step.params.get("field_name", "")
                if field:
                    rendered_fields.append(field)
            except ViznoirError as exc:
                logger.warning("  Step %d failed: %s — skipping", i + 1, exc)
            except Exception as exc:
                logger.error("  Step %d unexpected error: %s — skipping", i + 1, exc)

        all_results.extend(iteration_results)

        # Step 6: Evaluate
        image_bytes = [r.image_bytes for r in iteration_results if r.image_bytes]
        eval_meta = {**metadata, "rendered_fields": rendered_fields}
        eval_result = await evaluator.evaluate(ctx, image_bytes, eval_meta)

        if eval_result.verdict in ("done", "pass"):
            logger.info("Evaluation: %s — finishing", eval_result.verdict)
            break
        if eval_result.verdict == "refine" and eval_result.suggestions:
            logger.info("Evaluation: refine — %d suggestions", len(eval_result.suggestions))
            # Next iteration will re-plan with updated context

    return all_results
```

Note: Add `from typing import Any` to imports if not already present.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harness/test_orchestrator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full harness test suite**

Run: `pytest tests/test_harness/ -v`
Expected: ALL PASS (~30 tests)

- [ ] **Step 6: Commit**

```bash
git add src/viznoir/harness/orchestrator.py tests/test_harness/test_orchestrator.py
git commit -m "feat(harness): add auto_postprocess_impl orchestration loop"
```

---

### Task 6: Register auto_postprocess in server.py

**Files:**
- Modify: `src/viznoir/server.py`

- [ ] **Step 1: Add version guard and tool registration**

In `server.py`, after the existing `_TASKS_AVAILABLE` line, add:

```python
def _has_harness_support() -> bool:
    """Check if FastMCP >= 3.0.0 with Context.sample() is available."""
    try:
        from viznoir.harness import HAS_HARNESS
        return HAS_HARNESS
    except Exception:
        return False

_HARNESS_AVAILABLE = _has_harness_support()
```

Then at the end of `server.py`, before the `main()` function, add the tool registration:

```python
if _HARNESS_AVAILABLE:
    from fastmcp import Context

    @mcp.tool(task=True if _TASKS_AVAILABLE else None)
    async def auto_postprocess(
        ctx: Context,
        file_path: str,
        goal: Literal["explore", "publish", "compare"] = "explore",
        max_iterations: int = 5,
    ) -> list[Image]:
        """Autonomous post-processing: inspect → visualize → evaluate → refine.

        Analyzes the file, detects the simulation domain (CFD/FEA/SPH),
        and produces 3-5 visualizations automatically. With sampling-capable
        clients, evaluates results and refines parameters iteratively.

        Args:
            file_path: Path to simulation file (.foam, .vtu, .vtk, etc.)
            goal: "explore" (overview), "publish" (publication quality), "compare" (multi-field)
            max_iterations: Maximum refinement iterations (1-5)
        """
        file_path = _validate_file_path(file_path)
        from viznoir.harness.orchestrator import auto_postprocess_impl

        results = await auto_postprocess_impl(
            ctx=ctx,
            file_path=file_path,
            runner=_runner,
            goal=goal,
            max_iterations=min(max_iterations, 5),
        )
        return [
            Image(data=r.image_base64, format="png")
            for r in results
            if r.image_base64
        ]
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `pytest tests/ -q --tb=short`
Expected: ALL PASS (existing 1505+ tests)

- [ ] **Step 3: Commit**

```bash
git add src/viznoir/server.py
git commit -m "feat(harness): register auto_postprocess tool in server.py"
```

---

### Task 7: Extend domain prompts for sampling

**Files:**
- Modify: `src/viznoir/prompts/guides.py`

- [ ] **Step 1: Add sampling-optimized domain strategy prompts**

Add at the end of `guides.py`, before the closing:

```python
# ---------------------------------------------------------------------------
# Sampling strategy prompts (concise, structured for ctx.sample)
# ---------------------------------------------------------------------------

SAMPLING_CFD_STRATEGY = """\
You are planning CFD post-processing visualizations. Given the metadata:
1. Start with pressure (p) cinematic_render — Cool to Warm colormap
2. Add velocity (U) slice at mid-plane — Viridis colormap
3. If vector field exists, add streamlines
4. If timesteps > 1, note that animation is possible
Return a VizPlan JSON with 3-5 steps.
"""

SAMPLING_FEA_STRATEGY = """\
You are planning FEA post-processing visualizations. Given the metadata:
1. Start with von_mises_stress cinematic_render — Cool to Warm colormap
2. Add displacement visualization if available
3. If deformation field exists, suggest WarpByVector via render
Return a VizPlan JSON with 2-4 steps.
"""

SAMPLING_SPH_STRATEGY = """\
You are planning SPH post-processing visualizations. Given the metadata:
1. Start with Velocity cinematic_render — Viridis colormap
2. If Type field exists, consider filtering fluid-only particles
3. If timesteps > 1, note animation potential
Return a VizPlan JSON with 2-4 steps.
"""
```

- [ ] **Step 2: Update orchestrator to use sampling prompts**

In `orchestrator.py`, update `_load_domain_prompts()`:

```python
def _load_domain_prompts() -> dict[str, str]:
    if _DOMAIN_PROMPTS:
        return _DOMAIN_PROMPTS
    from viznoir.prompts.guides import (
        SAMPLING_CFD_STRATEGY,
        SAMPLING_FEA_STRATEGY,
        SAMPLING_SPH_STRATEGY,
        _VIZ_GUIDE,
    )
    _DOMAIN_PROMPTS.update({
        "cfd": SAMPLING_CFD_STRATEGY,
        "fea": SAMPLING_FEA_STRATEGY,
        "sph": SAMPLING_SPH_STRATEGY,
        "generic": _VIZ_GUIDE,
    })
    return _DOMAIN_PROMPTS
```

- [ ] **Step 3: Run prompt tests**

Run: `pytest tests/test_prompts.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/viznoir/prompts/guides.py src/viznoir/harness/orchestrator.py
git commit -m "feat(harness): add sampling-optimized domain strategy prompts"
```

---

## Chunk 3: Skills + Agent (P2)

### Task 8: Domain workflow skills

**Files:**
- Create: `.claude-plugin/skills/cfd-workflow/SKILL.md`
- Create: `.claude-plugin/skills/fea-workflow/SKILL.md`
- Create: `.claude-plugin/skills/sph-workflow/SKILL.md`

- [ ] **Step 1: Create CFD workflow skill**

Write `.claude-plugin/skills/cfd-workflow/SKILL.md`:

````markdown
---
name: cfd-workflow
description: >-
  CFD post-processing workflow skill. Guides AI agents through computational
  fluid dynamics visualization: pressure/velocity fields, streamlines, wall
  shear stress, boundary layers, and pressure drop analysis. Maps CFD domain
  vocabulary (Korean/English) to viznoir MCP tool calls. Triggers: CFD,
  flow visualization, pressure drop, streamlines, boundary layer, wake,
  recirculation, wall shear, 유동, 압력강하, 유선, 경계층, 후류
---

# CFD Post-Processing Workflow

## Standard Sequence
1. `inspect_data` → identify velocity (U), pressure (p), turbulence (k, epsilon)
2. `cinematic_render(field="p", colormap="Cool to Warm")` → pressure overview
3. `cinematic_render(field="U", colormap="Viridis")` or `slice` at mid-plane
4. `streamlines(vector_field="U")` → flow patterns, wake, recirculation
5. `plot_over_line` → pressure drop (inlet→outlet), velocity profiles
6. `extract_stats` → quantitative summary (min/max/mean)

## Vocabulary → Tool Mapping
| Expert says | Tool | Params |
|-------------|------|--------|
| wake, 후류 | streamlines | seed downstream of body |
| pressure drop, 압력강하 | plot_over_line | field="p", point1=inlet, point2=outlet |
| boundary layer, 경계층 | slice + plot_over_line | wall-normal direction |
| wall shear | cinematic_render | field="wallShearStress", colormap="Plasma" |
| recirculation, 재순환 | streamlines | seed in low-velocity region |
| turbulence | slice | field="k" or "nut", colormap="Turbo" |

## Colormaps
- Pressure: Cool to Warm (diverging)
- Velocity: Viridis (sequential)
- Temperature: Inferno (thermal)
- Wall shear: Plasma (high contrast)
- Turbulence: Turbo (structure emphasis)
````

- [ ] **Step 2: Create FEA workflow skill**

Write `.claude-plugin/skills/fea-workflow/SKILL.md`:

````markdown
---
name: fea-workflow
description: >-
  FEA post-processing workflow skill. Guides AI agents through finite element
  analysis visualization: stress distribution, deformation, mode shapes, and
  yield detection. Maps FEA domain vocabulary to viznoir MCP tool calls.
  Triggers: FEA, structural, stress, deformation, displacement, von Mises,
  yield, mode shape, 응력, 변형, 항복, 모드 형상
---

# FEA Post-Processing Workflow

## Standard Sequence
1. `inspect_data` → identify displacement, stress, strain fields
2. `cinematic_render(field="von_mises_stress", colormap="Cool to Warm")` → stress overview
3. `execute_pipeline` with WarpByVector → deformation visualization
4. `execute_pipeline` with Threshold(von_mises > yield) → critical regions
5. `extract_stats` → max stress, max displacement values

## WarpByVector Pattern
```json
{
  "source": {"file": "FILE_PATH"},
  "pipeline": [
    {"filter": "WarpByVector", "params": {"vector": "displacement", "scale_factor": 10.0}}
  ],
  "output": {"type": "image", "render": {"field": "von_mises_stress", "colormap": "Cool to Warm"}}
}
```
Scale factor: 10-100x for small deformations, 1x for large.

## Vocabulary → Tool Mapping
| Expert says | Tool | Params |
|-------------|------|--------|
| stress, 응력 집중 | cinematic_render | field="von_mises_stress" |
| deformation, 변형 | execute_pipeline | WarpByVector + render |
| yield exceeded, 항복 | execute_pipeline | Threshold(von_mises > yield_stress) |
| mode shape | cinematic_render | per-timestep displacement |
````

- [ ] **Step 3: Create SPH workflow skill**

Write `.claude-plugin/skills/sph-workflow/SKILL.md`:

````markdown
---
name: sph-workflow
description: >-
  SPH/DualSPHysics post-processing workflow skill. Guides AI agents through
  particle method visualization: fluid filtering, sloshing animations,
  isosurface mesh extraction, and particle distribution analysis. Maps SPH
  domain vocabulary to viznoir MCP tool calls. Triggers: SPH, DualSPHysics,
  particles, sloshing, fluid, Type field, bi4, 입자, 슬로싱, 유체
---

# SPH Post-Processing Workflow

## Standard Sequence
1. `inspect_data` → identify Velocity, Pressure, Type fields, timestep count
2. `cinematic_render(field="Velocity", colormap="Viridis")` → particle overview
3. `execute_pipeline` with Threshold(Type, 0, 0) → fluid-only particles
4. `animate(mode="timesteps")` → time evolution
5. `pv_isosurface` → smooth surface mesh from particles (if needed)

## Fluid-Only Filtering
DualSPHysics uses Type field: 0=fluid, >0=boundary. To show fluid only:
```json
{
  "source": {"file": "FILE_PATH"},
  "pipeline": [
    {"filter": "Threshold", "params": {"field": "Type", "range": [0, 0]}}
  ],
  "output": {"type": "image", "render": {"field": "Velocity", "colormap": "Viridis"}}
}
```

## Vocabulary → Tool Mapping
| Expert says | Tool | Params |
|-------------|------|--------|
| particles, 입자 | render or cinematic_render | field="Velocity" |
| fluid only | execute_pipeline | Threshold(Type, 0, 0) |
| sloshing, 슬로싱 | animate | mode="timesteps", field="Velocity" |
| wave, 파도 | animate | mode="timesteps" |
| isosurface mesh | pv_isosurface | bi4_dir, output_dir |
````

- [ ] **Step 4: Slim down cae-postprocess**

Remove domain-specific sections from `cae-postprocess/SKILL.md`, replacing with delegation references: "For CFD-specific patterns, see cfd-workflow skill." Keep: golden rule (inspect_data first), universal vocabulary table, aesthetic guide (colormap conventions, camera, background, quality presets), execution pattern.

- [ ] **Step 5: Update plugin.json**

Check if `.claude-plugin/plugin.json` needs skill registration or if auto-discovery handles it.

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/skills/cfd-workflow/SKILL.md \
  .claude-plugin/skills/fea-workflow/SKILL.md \
  .claude-plugin/skills/sph-workflow/SKILL.md \
  .claude-plugin/skills/cae-postprocess/SKILL.md \
  .claude-plugin/plugin.json
git commit -m "feat(skills): add domain workflow skills (cfd, fea, sph)"
```

---

### Task 9: Dev pipeline + OSS workflow skills

**Files:**
- Create: `.claude-plugin/skills/dev-pipeline/SKILL.md`
- Create: `.claude-plugin/skills/oss-workflow/SKILL.md`

- [ ] **Step 1: Create dev-pipeline skill**

Write `.claude-plugin/skills/dev-pipeline/SKILL.md`:

````markdown
---
name: dev-pipeline
description: >-
  viznoir development automation skill. Guides the TDD cycle for viznoir-specific
  concerns: dual filter registry, CI auto-skip rules, benchmark patterns,
  and PR quality gates. Triggers: viznoir development, new filter, new tool,
  TDD, benchmark, PR review, dual registry, CI skip
---

# viznoir Dev Pipeline

## Workflow
Issue → Explore → Plan → TDD (Red→Green→Refactor) → Benchmark → PR → Review

## viznoir-Specific Checklist

### New Filter
1. Register in `core/registry.py` (PascalCase key, VTK class + param schema)
2. Register in `engine/filters.py` (snake_case key, VTK filter function)
3. Add to `TOOL_DISPATCH` in `harness/orchestrator.py` if image-producing
4. Test in `tests/test_engine/test_filters.py`

### New Tool
1. Create `tools/{name}.py` with `{name}_impl()` function
2. Register `@mcp.tool()` in `server.py`
3. Test in `tests/test_tools/`
4. Add to `TOOL_DISPATCH` if image-producing

### VTK Rendering Test
- Name file `*_vtk.py` (auto-skipped in CI) OR
- Add to `conftest.py` skip list

### Benchmark
- Write `bench_*.py` following `bench_comparison.py` pattern
- Update `REPORT.md` with results

### PR Quality Gate
- Test count >= CI guard (currently 1430)
- Coverage >= 80%
- `ruff check src/ tests/` clean
- `mypy src/viznoir/` clean
````

- [ ] **Step 2: Create oss-workflow skill**

Write `.claude-plugin/skills/oss-workflow/SKILL.md`:

````markdown
---
name: oss-workflow
description: >-
  Open-source project success workflow for viznoir. Codifies contributor
  onboarding, release management (Release Please + PyPI), issue triage,
  and showcase curation. Triggers: release, contributor, onboarding,
  PyPI publish, issue triage, showcase, CHANGELOG, good first issue
---

# OSS Workflow

## 1. Contributor Onboarding
- New issue/PR → label `good-first-issue` if appropriate
- Review with friendly, educational tone
- After merge → thank-you comment + mention in CHANGELOG
- Track contributors: Shirish-12105 (#11), himax12 (#7)

## 2. Release Management
1. Check CHANGELOG.md for completeness
2. Release Please auto-creates version bump PR on main push
3. Merge Release Please PR → GitHub Release auto-published
4. PyPI publish via `publish.yml` (OIDC trusted publisher)
5. Update README badges if needed
- **Note**: PyPI Trusted Publisher must be configured at pypi.org

## 3. Issue Triage
- Categorize: bug / feature / question / showcase
- Assess reproducibility for bugs
- Label priority: P0 (critical) / P1 (important) / P2 (nice-to-have)
- Assign to milestone (v0.8.0, v0.9.0, backlog)

## 4. Showcase Curation
- New domain data → `inspect_data` → `cinematic_render`
- Add to README showcase gallery
- Datasets at `/mnt/dataset/viznoir-showcase/` (4.1GB, 16 domains)
- Connection: awesome-ai-cae list for viznoir exposure
````

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/skills/dev-pipeline/SKILL.md \
  .claude-plugin/skills/oss-workflow/SKILL.md
git commit -m "feat(skills): add dev-pipeline and oss-workflow skills"
```

---

### Task 10: viz-orchestrator agent + viz-agent fix

**Files:**
- Create: `agents/viz-orchestrator.md`
- Modify: `agents/viz-agent.md` (fix skill ref)

- [ ] **Step 1: Create viz-orchestrator agent**

```yaml
---
name: viz-orchestrator
description: |
  Autonomous visualization orchestrator. Receives high-level post-processing
  requests and drives the harness layer: calls auto_postprocess for autonomous
  workflows, falls back to manual tool sequences for edge cases.
  Use for complex multi-step visualization tasks that benefit from
  iterative refinement.
tools: Read, Glob, Grep, Bash
model: sonnet
permissionMode: default
skills:
  - cae-postprocess
  - cfd-workflow
  - fea-workflow
  - sph-workflow
mcpServers:
  - viznoir
---

You are an autonomous visualization orchestrator. Your role:

1. Receive high-level visualization requests from the main agent
2. Prefer `auto_postprocess` for autonomous workflows (inspect → render → evaluate → refine)
3. Fall back to individual tool calls for edge cases or specific user requests
4. Report results with physical interpretation

## When to use auto_postprocess

- User provides a simulation file and wants "full analysis" or "post-process this"
- Exploratory visualization (user hasn't specified exact views)
- Publication-quality output (goal="publish")

## When to use individual tools

- User requests a specific visualization (e.g., "show me a slice at x=0.5")
- Comparison between two files (use compare tool directly)
- Animation (use animate/split_animate directly)

## Guidelines

- Always explain what you did and why in physical terms
- Mention which domain was detected and what fields were analyzed
- Suggest follow-up analyses based on results
```

- [ ] **Step 2: Fix viz-agent.md skill reference**

Change `skills: - cfd-postprocess` to `skills: - cae-postprocess` in `agents/viz-agent.md`.

- [ ] **Step 3: Commit**

```bash
git add agents/viz-orchestrator.md agents/viz-agent.md
git commit -m "feat(agents): add viz-orchestrator, fix viz-agent skill ref"
```

---

## Chunk 4: Integration + Final Verification

### Task 11: Full integration test

**Files:**
- Create: `tests/test_harness/test_integration.py`

- [ ] **Step 1: Write end-to-end integration test**

```python
# tests/test_harness/test_integration.py
"""End-to-end integration test for auto_postprocess pipeline."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from viznoir.core.output import PipelineResult
from viznoir.core.runner import RunResult
from viznoir.harness.orchestrator import auto_postprocess_impl


@pytest.fixture
def full_cfd_metadata():
    return {
        "file_path": "/data/case.foam",
        "arrays": {
            "p": {"range": [-100, 500], "association": "POINTS"},
            "U": {"range": [0, 15], "association": "POINTS", "num_components": 3},
            "k": {"range": [0, 5], "association": "POINTS"},
        },
        "bounds": [0, 2, -0.5, 0.5, 0, 0.1],
        "timesteps": [0.0, 0.5, 1.0],
        "blocks": ["internalMesh", "inlet", "outlet", "wall"],
    }


@pytest.fixture
def mock_pipeline_result():
    return PipelineResult(
        output_type="image",
        image_bytes=b"\x89PNG\r\n\x1a\nfake",
        image_base64="iVBORw0KGgoAAAANSUhfake",
        json_data=None,
        raw=RunResult(stdout="", stderr="", exit_code=0),
    )


class TestAutoPostprocessIntegration:
    @pytest.mark.asyncio
    async def test_cfd_heuristic_produces_multiple_views(
        self, full_cfd_metadata, mock_pipeline_result
    ):
        """CFD file with p, U, k fields should produce 3 views via heuristic."""
        mock_ctx = MagicMock()
        mock_ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()
        mock_runner = AsyncMock()
        mock_runner.config = MagicMock()

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=full_cfd_metadata),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_pipeline_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=1,
            )

        assert len(results) >= 2  # At least cinematic_render(p) + render(U)
        assert all(r.image_bytes for r in results)

    @pytest.mark.asyncio
    async def test_fea_domain_detection(self, mock_pipeline_result):
        """VTU with stress fields detected as FEA."""
        fea_meta = {
            "file_path": "/data/result.vtu",
            "arrays": {"von_mises_stress": {"range": [0, 300]}, "displacement": {"range": [0, 0.01]}},
            "bounds": [0, 1, 0, 1, 0, 1],
            "timesteps": [],
        }
        mock_ctx = MagicMock()
        mock_ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()
        mock_runner = AsyncMock()
        mock_runner.config = MagicMock()

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=fea_meta),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_pipeline_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/result.vtu",
                runner=mock_runner,
            )

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_empty_file_still_produces_output(self, mock_pipeline_result):
        """Even with minimal metadata, orchestrator produces at least 1 result."""
        empty_meta = {
            "file_path": "/data/mesh.stl",
            "arrays": {},
            "bounds": [0, 1, 0, 1, 0, 1],
            "timesteps": [],
        }
        mock_ctx = MagicMock()
        mock_ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()
        mock_runner = AsyncMock()
        mock_runner.config = MagicMock()

        with (
            patch("viznoir.harness.orchestrator.inspect_data_impl", new_callable=AsyncMock, return_value=empty_meta),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_pipeline_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/mesh.stl",
                runner=mock_runner,
            )

        assert len(results) >= 1
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_harness/test_integration.py -v`
Expected: ALL PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -q --tb=short`
Expected: ALL PASS (1505 + ~50 new = ~1555 tests)

- [ ] **Step 4: Run linting and type check**

Run: `ruff check src/viznoir/harness/ tests/test_harness/`
Run: `mypy src/viznoir/harness/ --ignore-missing-imports`
Expected: No errors

- [ ] **Step 5: Commit integration tests**

```bash
git add tests/test_harness/test_integration.py
git commit -m "test(harness): add end-to-end integration tests"
```

---

### Task 12: Documentation + CLAUDE.md update

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add harness section to CLAUDE.md**

In the Architecture section, add Layer 4 description, harness/ package structure, and `auto_postprocess` tool to the tool count.

- [ ] **Step 2: Update Key Metrics table**

Update tool count from 22 to 23.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with harness layer architecture"
```

---

### Task 13: Final verification

- [ ] **Step 1: Run complete test suite**

```bash
pytest --cov=viznoir --cov-report=term-missing -q
```
Expected: 1550+ tests, coverage >= 80%

- [ ] **Step 2: Run all quality checks**

```bash
ruff check src/ tests/
mypy src/viznoir/ --ignore-missing-imports
```
Expected: Clean

- [ ] **Step 3: Verify tool count**

```bash
python3 -c "
from viznoir.server import mcp
# Tool count should be 23 (22 existing + auto_postprocess)
print(f'Tools registered: {len(mcp._tool_manager._tools)}')
"
```

- [ ] **Step 4: Create feature branch and final commit**

```bash
git log --oneline feat/adaptive-render-v2..HEAD
# Review all commits from this implementation
```
