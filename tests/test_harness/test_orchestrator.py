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
    async def test_produces_results_with_heuristic_fallback(self, mock_runner, mock_result, sample_inspect_result):
        """Without sampling, should still produce results via heuristic plan."""
        mock_ctx = MagicMock()
        mock_ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=sample_inspect_result,
            ),
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
        refine_result = MagicMock()
        refine_result.result = EvalResult(
            verdict="refine",
            issues=["needs improvement"],
            suggestions=[
                VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "U"}, rationale="retry")
            ],
        )
        plan_result = MagicMock()
        plan_result.result = VizPlan(
            domain="cfd",
            steps=[
                VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "p"}, rationale="test")
            ],
            key_fields=["p"],
        )
        mock_ctx.sample = AsyncMock(
            side_effect=[plan_result, refine_result, plan_result, refine_result, plan_result, refine_result]
        )
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=sample_inspect_result,
            ),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=2,
            )

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_done_verdict_stops_loop(self, mock_runner, mock_result, sample_inspect_result):
        """Orchestrator stops when evaluator returns 'done'."""
        mock_ctx = MagicMock()
        plan_result = MagicMock()
        plan_result.result = VizPlan(
            domain="cfd",
            steps=[
                VizStep(tool="render", params={"file_path": "/data/case.foam", "field_name": "p"}, rationale="test")
            ],
            key_fields=["p"],
        )
        done_result = MagicMock()
        done_result.result = EvalResult(verdict="done", issues=[], suggestions=[])
        mock_ctx.sample = AsyncMock(side_effect=[plan_result, done_result])
        mock_ctx.info = MagicMock()
        mock_ctx.report_progress = AsyncMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=sample_inspect_result,
            ),
            patch("viznoir.harness.orchestrator._execute_step", new_callable=AsyncMock, return_value=mock_result),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=5,
            )

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
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=sample_inspect_result,
            ),
            patch(
                "viznoir.harness.orchestrator._execute_step",
                new_callable=AsyncMock,
                side_effect=failing_then_succeeding,
            ),
        ):
            results = await auto_postprocess_impl(
                ctx=mock_ctx,
                file_path="/data/case.foam",
                runner=mock_runner,
                goal="explore",
                max_iterations=1,
            )

        assert len(results) >= 1
