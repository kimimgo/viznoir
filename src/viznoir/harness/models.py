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
        from viznoir.harness.registry import TOOL_DISPATCH

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
