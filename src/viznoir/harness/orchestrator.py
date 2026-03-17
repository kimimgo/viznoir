"""Orchestrator — auto_postprocess meta-tool and tool dispatch."""

from __future__ import annotations

import base64
from typing import Any

from viznoir.core.output import PipelineResult
from viznoir.core.runner import RunResult, VTKRunner
from viznoir.errors import ViznoirError
from viznoir.harness.domain_hints import detect_domain
from viznoir.harness.evaluator import SamplingEvaluator
from viznoir.harness.models import VizStep
from viznoir.harness.registry import TOOL_DISPATCH
from viznoir.logging import get_logger
from viznoir.tools.batch import batch_render_impl
from viznoir.tools.cinematic import cinematic_render_impl
from viznoir.tools.compare import compare_impl
from viznoir.tools.filters import clip_impl, contour_impl, slice_impl, streamlines_impl
from viznoir.tools.inspect import inspect_data_impl
from viznoir.tools.render import render_impl
from viznoir.tools.volume import volume_render_impl

logger = get_logger("harness.orchestrator")

# Populate the shared registry (used by models.py for validation).
TOOL_DISPATCH.update(
    {
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
)

# Map goal → purpose for adaptive resolution
_GOAL_TO_PURPOSE = {"explore": "analyze", "publish": "publish", "compare": "preview"}

# Domain prompt cache
_DOMAIN_PROMPTS: dict[str, str] = {}


def _load_domain_prompts() -> dict[str, str]:
    """Load domain prompts lazily."""
    if _DOMAIN_PROMPTS:
        return _DOMAIN_PROMPTS
    from viznoir.prompts.guides import (
        _VIZ_GUIDE,
        SAMPLING_CFD_STRATEGY,
        SAMPLING_FEA_STRATEGY,
        SAMPLING_SPH_STRATEGY,
    )

    _DOMAIN_PROMPTS.update(
        {
            "cfd": SAMPLING_CFD_STRATEGY,
            "fea": SAMPLING_FEA_STRATEGY,
            "sph": SAMPLING_SPH_STRATEGY,
            "generic": _VIZ_GUIDE,
        }
    )
    return _DOMAIN_PROMPTS


async def _execute_step(step: VizStep, runner: VTKRunner, goal: str = "explore") -> PipelineResult:
    """Execute a single VizStep, normalizing heterogeneous return types.

    Return types vary: PipelineResult (render/slice/contour/clip/streamlines),
    bytes (cinematic/compare/volume), dict (batch). All normalized to PipelineResult.
    """
    impl_fn = TOOL_DISPATCH[step.tool]
    params = {**step.params, "runner": runner}

    # Inject purpose for adaptive resolution
    purpose = _GOAL_TO_PURPOSE.get(goal, "preview")
    purpose_tools = {"render", "cinematic_render", "slice", "contour", "clip", "streamlines", "batch_render"}
    if "purpose" not in params and step.tool in purpose_tools:
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
    msg = f"Unexpected return type from {step.tool}: {type(result)}"
    raise TypeError(msg)


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
            logger.info("Evaluation: refine — executing %d suggestions", len(eval_result.suggestions))
            for i, step in enumerate(eval_result.suggestions):
                try:
                    result = await _execute_step(step, runner, goal=goal)
                    all_results.append(result)
                    field = step.params.get("field_name", "")
                    if field:
                        rendered_fields.append(field)
                except ViznoirError as exc:
                    logger.warning("  Suggestion %d failed: %s — skipping", i + 1, exc)
                except Exception as exc:
                    logger.error("  Suggestion %d unexpected error: %s — skipping", i + 1, exc)

    return all_results
