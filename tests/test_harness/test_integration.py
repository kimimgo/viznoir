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


def _make_ctx_no_sampling():
    ctx = MagicMock()
    ctx.sample = AsyncMock(side_effect=Exception("no sampling"))
    ctx.info = MagicMock()
    ctx.report_progress = AsyncMock()
    return ctx


class TestAutoPostprocessIntegration:
    @pytest.mark.asyncio
    async def test_cfd_heuristic_produces_multiple_views(self, full_cfd_metadata, mock_pipeline_result):
        """CFD file with p, U, k fields should produce 3 views via heuristic."""
        ctx = _make_ctx_no_sampling()
        runner = AsyncMock()
        runner.config = MagicMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=full_cfd_metadata,
            ),
            patch(
                "viznoir.harness.orchestrator._execute_step",
                new_callable=AsyncMock,
                return_value=mock_pipeline_result,
            ),
        ):
            results = await auto_postprocess_impl(
                ctx=ctx,
                file_path="/data/case.foam",
                runner=runner,
                goal="explore",
                max_iterations=1,
            )

        assert len(results) >= 2  # cinematic_render(p) + render(U) at minimum
        assert all(r.image_bytes for r in results)

    @pytest.mark.asyncio
    async def test_fea_domain_detection(self, mock_pipeline_result):
        """VTU with stress fields detected as FEA."""
        fea_meta = {
            "file_path": "/data/result.vtu",
            "arrays": {
                "von_mises_stress": {"range": [0, 300]},
                "displacement": {"range": [0, 0.01]},
            },
            "bounds": [0, 1, 0, 1, 0, 1],
            "timesteps": [],
        }
        ctx = _make_ctx_no_sampling()
        runner = AsyncMock()
        runner.config = MagicMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=fea_meta,
            ),
            patch(
                "viznoir.harness.orchestrator._execute_step",
                new_callable=AsyncMock,
                return_value=mock_pipeline_result,
            ),
        ):
            results = await auto_postprocess_impl(ctx=ctx, file_path="/data/result.vtu", runner=runner)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_sph_domain_detection(self, mock_pipeline_result):
        """VTK with Type + Velocity fields detected as SPH."""
        sph_meta = {
            "file_path": "/data/Part0001.bi4",
            "arrays": {
                "Velocity": {"range": [0, 5], "num_components": 3},
                "Type": {"range": [0, 3]},
                "Pressure": {"range": [0, 1000]},
            },
            "bounds": [0, 1, 0, 1, 0, 1],
            "timesteps": [0.0, 0.01, 0.02],
        }
        ctx = _make_ctx_no_sampling()
        runner = AsyncMock()
        runner.config = MagicMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=sph_meta,
            ),
            patch(
                "viznoir.harness.orchestrator._execute_step",
                new_callable=AsyncMock,
                return_value=mock_pipeline_result,
            ),
        ):
            results = await auto_postprocess_impl(ctx=ctx, file_path="/data/Part0001.bi4", runner=runner)

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
        ctx = _make_ctx_no_sampling()
        runner = AsyncMock()
        runner.config = MagicMock()

        with (
            patch(
                "viznoir.harness.orchestrator.inspect_data_impl",
                new_callable=AsyncMock,
                return_value=empty_meta,
            ),
            patch(
                "viznoir.harness.orchestrator._execute_step",
                new_callable=AsyncMock,
                return_value=mock_pipeline_result,
            ),
        ):
            results = await auto_postprocess_impl(ctx=ctx, file_path="/data/mesh.stl", runner=runner)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_goal_explore_vs_publish(self, full_cfd_metadata, mock_pipeline_result):
        """Both explore and publish goals produce results."""
        runner = AsyncMock()
        runner.config = MagicMock()

        for goal in ("explore", "publish"):
            ctx = _make_ctx_no_sampling()
            with (
                patch(
                    "viznoir.harness.orchestrator.inspect_data_impl",
                    new_callable=AsyncMock,
                    return_value=full_cfd_metadata,
                ),
                patch(
                    "viznoir.harness.orchestrator._execute_step",
                    new_callable=AsyncMock,
                    return_value=mock_pipeline_result,
                ),
            ):
                results = await auto_postprocess_impl(
                    ctx=ctx,
                    file_path="/data/case.foam",
                    runner=runner,
                    goal=goal,
                    max_iterations=1,
                )
            assert len(results) >= 1, f"goal={goal} produced no results"
