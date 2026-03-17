"""Tests for harness Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from viznoir.harness.models import EvalResult, VizPlan, VizStep


@pytest.fixture(autouse=True)
def mock_tool_dispatch(monkeypatch):
    """Mock TOOL_DISPATCH so model tests don't depend on orchestrator."""
    fake_dispatch = {"render": lambda: None, "cinematic_render": lambda: None, "slice": lambda: None}
    monkeypatch.setattr("viznoir.harness.registry.TOOL_DISPATCH", fake_dispatch)


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
