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
            steps=[
                VizStep(
                    tool="render",
                    params={"file_path": "/data/case.foam", "field_name": "p"},
                    rationale="pressure overview",
                )
            ],
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
