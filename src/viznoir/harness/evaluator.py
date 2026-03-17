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
            plan: VizPlan = result.result
            logger.info("Sampling plan received: %d steps", len(plan.steps))
            return plan

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
            eval_result: EvalResult = result.result
            return eval_result

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
            steps.append(
                VizStep(
                    tool="cinematic_render",
                    params={"file_path": file_path, "field_name": primary},
                    rationale=f"Primary field overview: {primary}",
                )
            )

        # Add secondary visualizations
        secondary = self._pick_secondary_fields(field_names, domain, primary)
        for field in secondary[:2]:
            steps.append(
                VizStep(
                    tool="render",
                    params={"file_path": file_path, "field_name": field},
                    rationale=f"Secondary field: {field}",
                )
            )

        # If no fields found, still produce a geometry render
        if not steps:
            steps.append(
                VizStep(
                    tool="render",
                    params={"file_path": file_path, "field_name": field_names[0] if field_names else ""},
                    rationale="Geometry overview (no domain-specific fields detected)",
                )
            )

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
