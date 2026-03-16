# Agent Harness — v0.8.0 Design Spec

**Date**: 2026-03-16
**Status**: Draft
**Branch**: `feat/agent-harness`

## Overview

Add an Agent Harness layer to viznoir that enables autonomous post-processing
workflows via a meta-tool (`auto_postprocess`) with MCP Sampling-based
evaluation, domain-specific Skills for workflow guidance, and optional C++
native VTK filters for hot-path optimization.

## Goals

1. **A-axis (MCP Workflow Orchestration)**: AI agents use viznoir more
   effectively through guided inspect → render → evaluate → refine loops.
2. **C1 (Dev Pipeline)**: Automate viznoir's development cycle with a
   project-specific skill.
3. **C2 (OSS Workflow)**: Codify open-source success strategies
   (contributor onboarding, release management, issue triage, showcase curation).
4. **C3 (C++ Native)**: Eliminate performance bottlenecks with custom VTK
   C++ filters exposed via pybind11.

## Non-Goals

- Replacing existing MCP tools (all 22 tools remain unchanged)
- Forcing a fixed workflow (users can still call individual tools)
- Supporting non-VTK rendering backends
- Real-time simulation steering

## Architecture

### Layer Addition

A new Layer 4 (Harness) sits above existing layers without modifying them.
Dependency direction: Harness → Tools (one-way). Tools layer has no knowledge
of Harness.

**FastMCP version requirement**: The harness module requires `fastmcp>=3.0.0`
for `ctx.sample()`. A runtime version guard (following the existing
`_has_mcp_tasks()` pattern) makes the harness conditionally available.
With `fastmcp>=2.0.0`, all existing tools work; the `auto_postprocess` tool
is simply not registered. The heuristic fallback path (non-sampling) also
requires 3.x since it still uses `Context` injection.

```
Layer 4: Harness (NEW)
  ├── orchestrator     — Meta-tool: auto_postprocess
  ├── evaluator        — Sampling gateway: ctx.sample() result evaluation
  ├── domain_hints     — File/field → domain mapping (mechanical)
  ├── models           — VizPlan, VizStep, EvalResult (Pydantic)
  └── native/          — C++ custom VTK filters (pybind11, optional)

Layer 3: Skills (.claude-plugin/)
  ├── cae-postprocess  (existing, slimmed)
  ├── cfd-workflow     (NEW)
  ├── fea-workflow     (NEW)
  ├── sph-workflow     (NEW)
  ├── dev-pipeline     (NEW)
  └── oss-workflow     (NEW)

Layer 2: Agents (agents/)
  ├── viz-agent        (existing)
  ├── mesh-agent       (existing)
  └── viz-orchestrator (NEW — drives harness)

Layer 1: MCP Server (src/viznoir/)
  server.py + tools/ + engine/ + core/  (existing — minimal changes)
```

### Package Structure

```
src/viznoir/
  harness/
    __init__.py
    orchestrator.py      — auto_postprocess tool implementation
    evaluator.py         — SamplingEvaluator (ctx.sample wrapper)
    domain_hints.py      — file extension/field → domain detection
    models.py            — VizPlan, VizStep, EvalResult Pydantic models
    native/
      __init__.py        — pybind11 import wrapper with fallback
      src/
        vortex_detect.cpp
        bindings.cpp
      include/
        viznoir_native.h
      CMakeLists.txt
```

## Detailed Design

### 1. Meta-Tool: `auto_postprocess`

New MCP tool registered in `server.py`.

```python
@mcp.tool()
async def auto_postprocess(
    ctx: Context,
    file_path: str,
    goal: Literal["explore", "publish", "compare"] = "explore",
    max_iterations: int = 5,
) -> list[Image]:
    """Autonomous post-processing: inspect → visualize → evaluate → refine."""
```

Note: `ctx: Context` must precede defaulted params (Python syntax).
FastMCP injects `Context` by type annotation — callers do not pass it.
This tool is only registered when `fastmcp>=3.0.0` is detected (see
`_has_sampling_support()` guard in Architecture section).

**Execution flow**:

1. `inspect_data(file_path)` → metadata
2. `domain_hints.detect(metadata)` → `"cfd" | "fea" | "sph" | "generic"`
3. Load domain prompt from `prompts/guides.py`
4. `ctx.sample(messages=..., system_prompt=domain_prompt, result_type=VizPlan)`
   → structured visualization plan
5. Execute `VizPlan.steps` by calling `*_impl` functions from `tools/`
   directly (Python-level, no MCP round-trip). A `TOOL_DISPATCH` dict
   maps tool names to impl functions (e.g., `"cinematic_render"` →
   `cinematic_impl`). The shared `_runner` and `_config` instances from
   `server.py` are passed to each impl call.
6. `ctx.sample(messages=[results], result_type=EvalResult)` → pass/refine/done
7. If `refine` and `iteration < max_iterations`: loop to step 4 with adjustments
8. Return final images

**Graceful degradation**: When client does not support sampling,
`SamplingEvaluator` returns a default `VizPlan` based on heuristics from
`domain_hints` and skips the evaluation loop (1-pass execution).

### 2. Pydantic Models

```python
class VizStep(BaseModel):
    tool: str                    # e.g. "cinematic_render", "slice"
    params: dict[str, Any]       # tool kwargs (validated against TOOL_DISPATCH)
    rationale: str               # why this visualization (for logging)

    @model_validator(mode="after")
    def validate_tool_exists(self) -> "VizStep":
        """Verify tool name exists in dispatch table."""
        from viznoir.harness.orchestrator import TOOL_DISPATCH
        if self.tool not in TOOL_DISPATCH:
            raise ValueError(f"Unknown tool: {self.tool}")
        return self

class VizPlan(BaseModel):
    domain: str                  # "cfd", "fea", "sph", "generic"
    steps: list[VizStep]         # 1-6 visualization steps
    key_fields: list[str]        # primary fields to analyze

class EvalResult(BaseModel):
    verdict: Literal["pass", "refine", "done"]
    issues: list[str]            # e.g. "colormap range too wide"
    suggestions: list[VizStep]   # replacement steps for refine
```

### 3. SamplingEvaluator

```python
class SamplingEvaluator:
    """Wraps ctx.sample() with graceful degradation."""

    async def plan(self, ctx, metadata, domain_prompt) -> VizPlan:
        """Request visualization plan from LLM.
        Falls back to default plan if sampling unavailable."""

    async def evaluate(self, ctx, images, metadata) -> EvalResult:
        """Request result evaluation from LLM.
        Falls back to EvalResult(verdict="done") if unavailable."""

    async def _try_sample(self, ctx, **kwargs):
        """Attempt ctx.sample(); return None on failure (graceful degradation).
        Uses try/except rather than capability pre-check for robustness."""
        try:
            return await ctx.sample(**kwargs)
        except Exception:
            return None
```

**Error handling**: Per-step execution failures (`ViznoirError` subtypes)
are caught, logged, and skipped. Failed steps are included in the evaluation
context so the refine loop can suggest alternatives.

Key behaviors:
- `max_tokens=1024` for plan, `512` for evaluate
- Structured output via `result_type` (Pydantic validation, auto-retry)
- Domain prompt injected as `system_prompt` in sampling calls

### 4. Domain Hints

Mechanical (non-LLM) domain detection from file metadata:

```python
def detect(metadata: dict) -> str:
    """Detect domain from file extension and field names."""
    # .foam, .cas → "cfd"
    # .vtu with displacement/stress fields → "fea"
    # .bi4, .vtk with Type/Velocity → "sph"
    # else → "generic"
```

This is intentionally simple. Complex domain inference is delegated to
LLM via sampling, using domain-specific prompts/skills as context.

### 5. Domain Strategy: Skills + MCP Prompts (Dual Channel)

Domain workflow knowledge lives in two complementary forms:

| Channel | Consumer | When |
|---------|----------|------|
| **Skills** (`.claude-plugin/skills/*-workflow/`) | Claude Code agent | Loaded into agent context on skill trigger |
| **MCP Prompts** (`prompts/guides.py`) | `ctx.sample()` calls | Injected as system_prompt during orchestration |

Skills contain richer, narrative workflow guidance. MCP Prompts contain
concise, structured instructions optimized for sampling calls.

**User extensibility**: Users add custom domain skills by creating
`.claude-plugin/skills/my-domain-workflow/SKILL.md`. The orchestrator
benefits indirectly — when the LLM has user's skill context loaded,
`ctx.sample()` responses reflect that domain knowledge.

### 6. C++ Native Filters

Optional dependency: `pip install mcp-server-viznoir[native]`

**Initial target**: VortexDetect (Q-criterion + lambda-2)

| Component | Current | Native | Expected Speedup |
|-----------|---------|--------|-----------------|
| VortexDetect | `topology.py` (numpy) | C++ with SIMD + OpenMP | 10-50x on 1M+ cells |

Future candidates (design TBD, not in v0.8.0 scope):
- **FieldSimilarity**: Timestep-to-timestep field diff with significance
  threshold. Use case: evaluator asks "what changed?" between iterations.
- **AdaptiveSampler**: Curvature-aware point decimation for LOD.
  Use case: reduce 10M-point dataset to visually representative 100K subset.

**Build**: CMake + pybind11 + VTK::CommonDataModel

**Fallback pattern**:
```python
try:
    from viznoir_native import vortex_detect
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

def vortex_detect_auto(dataset, method="q_criterion"):
    if HAS_NATIVE:
        return vortex_detect(dataset, method)
    from viznoir.engine.topology import detect_vortices
    return detect_vortices(dataset, field_name="velocity", threshold=0.0)
```

CI runs Python-only fallback tests. C++ build has a separate workflow.

### 7. Dev Pipeline Skill

viznoir-specific development automation (`.claude-plugin/skills/dev-pipeline/`).

Workflow: `Issue → Explore → Plan → TDD → Benchmark → PR → Review`

viznoir-specific checklist:
- New filter? → Register in both `core/registry.py` (PascalCase) AND
  `engine/filters.py` (snake_case)
- New tool? → Register in `server.py` + add test in `tests/test_tools/`
- VTK rendering test? → Name file `*_vtk.py` or add to conftest.py skip list
- Benchmark needed? → Write `bench_*.py`, update REPORT.md

### 8. OSS Workflow Skill

Open-source project success strategies (`.claude-plugin/skills/oss-workflow/`).

Four sub-workflows:
1. **Contributor Onboarding**: Issue/PR detection → labeling → friendly review
   → merge → thank-you comment
2. **Release Management**: CHANGELOG → version bump → Release Please →
   PyPI publish → GitHub Release → badge update
3. **Issue Triage**: Categorize (bug/feature/question/showcase) →
   reproducibility → priority → milestone
4. **Showcase Curation**: New domain data → inspect → cinematic_render →
   README gallery update → social image generation

### 9. viz-orchestrator Agent

New agent (`agents/viz-orchestrator.md`) that drives the harness layer.

```yaml
name: viz-orchestrator
model: sonnet
tools: Read, Glob, Grep, Bash
skills:
  - cae-postprocess
  - cfd-workflow
  - fea-workflow
  - sph-workflow
mcpServers:
  - viznoir
```

Responsibilities:
- Receive high-level visualization requests from main agent
- Call `auto_postprocess` for autonomous workflows
- Fall back to manual tool sequences for edge cases
- Report results with physical interpretation

## Phase Plan

### P1: Orchestrator Core (Required)

Deliverables:
- `harness/` module: orchestrator, evaluator, domain_hints, models
- `auto_postprocess` MCP tool registered in server.py
- Domain prompts extended in `prompts/guides.py`
- Unit tests in `tests/test_harness/`
- Heuristic fallback (non-sampling clients)

### P2: Skills + Agent (Required)

Deliverables:
- 3 domain workflow skills: cfd, fea, sph
- dev-pipeline skill
- oss-workflow skill
- viz-orchestrator agent
- cae-postprocess slimmed (delegates to domain skills)

### P3: C++ Native (Stretch)

Deliverables:
- VortexDetect C++ filter + pybind11 bindings
- `[native]` optional dependency in pyproject.toml
- Benchmark proving 10x+ speedup on 1M+ cells
- CI workflow for C++ build

**Dependencies**: P1 → P2, P1 → P3, P2 ╳ P3 (independent)

## File Changes

### New Files

| File | Phase | Purpose |
|------|-------|---------|
| `src/viznoir/harness/__init__.py` | P1 | Module init |
| `src/viznoir/harness/orchestrator.py` | P1 | auto_postprocess impl |
| `src/viznoir/harness/evaluator.py` | P1 | SamplingEvaluator |
| `src/viznoir/harness/domain_hints.py` | P1 | Domain detection |
| `src/viznoir/harness/models.py` | P1 | Pydantic models |
| `.claude-plugin/skills/cfd-workflow/SKILL.md` | P2 | CFD workflow |
| `.claude-plugin/skills/fea-workflow/SKILL.md` | P2 | FEA workflow |
| `.claude-plugin/skills/sph-workflow/SKILL.md` | P2 | SPH workflow |
| `.claude-plugin/skills/dev-pipeline/SKILL.md` | P2 | Dev automation |
| `.claude-plugin/skills/oss-workflow/SKILL.md` | P2 | OSS strategy |
| `agents/viz-orchestrator.md` | P2 | Orchestrator agent |
| `tests/test_harness/` | P1 | ~6 test files |
| `src/viznoir/harness/native/` | P3 | C++ filters (stretch) |

### Modified Files

| File | Change |
|------|--------|
| `src/viznoir/server.py` | Register auto_postprocess tool (~20 lines) |
| `src/viznoir/prompts/guides.py` | Add domain strategy prompts |
| `.claude-plugin/skills/cae-postprocess/SKILL.md` | Slim down, delegate to domain skills |
| `pyproject.toml` | Add `[native]` optional dep (P3) |

## Success Criteria

1. `auto_postprocess("case.foam")` produces 3-5 visualizations automatically
2. Sampling-capable client: evaluate → refine loop works (max 5 iterations)
3. Non-sampling client: heuristic 1-pass fallback produces reasonable results
   (80% quality vs manual tool calls)
4. User-added custom skill → orchestrator reflects domain knowledge via sampling
5. CI green: test count +50 (orchestrator ~15, evaluator ~10, domain_hints ~10,
   models ~8, integration ~7), coverage >= 80%
6. (P3) VortexDetect C++ vs numpy: 10x+ speedup on 1M+ cell datasets

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Claude Desktop sampling support inconsistent | Medium | Heuristic fallback always works |
| ctx.sample() token cost high in evaluate loop | Medium | max_iterations cap, max_tokens limits |
| Domain detection wrong for exotic formats | Low | LLM corrects via sampling; user can specify |
| C++ build complexity deters contributors | Medium | Optional dep, Python fallback, separate CI |
| Skill proliferation clutters plugin | Low | Clear naming convention, README index |

## Resolved Questions

1. **MCP Tasks for progress**: Yes. Use `task=True if _TASKS_AVAILABLE else None`
   consistent with existing `animate`/`split_animate`/`execute_pipeline` tools.
   `auto_postprocess` with up to 5 iterations is clearly long-running.

## Open Questions

1. Should the evaluator accept image inputs in `ctx.sample()` (multimodal)?
   Depends on client support for image content in sampling messages.
2. VortexDetect C++ filter: should it be a standalone PyPI package
   (`viznoir-native`) or bundled in the main package with build isolation?
