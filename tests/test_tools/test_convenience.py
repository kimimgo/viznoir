"""Tests for L3 convenience tools — verify they build correct PipelineDefinitions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from viznoir.core.output import PipelineResult
from viznoir.core.runner import ParaViewRunner, RunResult


@pytest.fixture
def mock_runner():
    runner = AsyncMock(spec=ParaViewRunner)
    runner.config = None
    return runner


@pytest.fixture
def mock_result():
    return PipelineResult(
        output_type="image",
        image_bytes=b"fake-png-data",
        image_base64="ZmFrZS1wbmctZGF0YQ==",
        json_data={"type": "image", "path": "/output/render.png"},
        raw=RunResult(stdout="", stderr="", exit_code=0),
    )


class TestSliceImpl:
    @pytest.mark.asyncio
    async def test_builds_correct_pipeline(self, mock_runner, mock_result):
        with patch("viznoir.tools.filters.execute_pipeline", return_value=mock_result) as mock_exec:
            from viznoir.tools.filters import slice_impl

            await slice_impl(
                file_path="/data/case.vtk",
                field_name="p",
                runner=mock_runner,
                origin=[0.05, 0, 0],
                normal=[1, 0, 0],
            )

            mock_exec.assert_called_once()
            pipeline_def = mock_exec.call_args[0][0]
            assert pipeline_def.source.file == "/data/case.vtk"
            assert len(pipeline_def.pipeline) == 1
            assert pipeline_def.pipeline[0].filter == "Slice"
            assert pipeline_def.pipeline[0].params["origin"] == [0.05, 0, 0]
            assert pipeline_def.output.type == "image"


class TestRenderImpl:
    @pytest.mark.asyncio
    async def test_builds_correct_pipeline(self, mock_runner, mock_result):
        with patch("viznoir.tools.render.execute_pipeline", return_value=mock_result):
            from viznoir.tools.render import render_impl

            result = await render_impl(
                file_path="/data/case.foam",
                field_name="U",
                runner=mock_runner,
                colormap="Viridis",
                timestep="latest",
            )

            assert result.image_bytes == b"fake-png-data"


class TestExtractStatsImpl:
    @pytest.mark.asyncio
    async def test_builds_correct_pipeline(self, mock_runner):
        data_result = PipelineResult(
            output_type="data",
            json_data={"type": "data", "fields": {"p": {"min": 0, "max": 100}}},
            raw=RunResult(stdout="", stderr="", exit_code=0),
        )
        with patch("viznoir.tools.extract.execute_pipeline", return_value=data_result) as mock_exec:
            from viznoir.tools.extract import extract_stats_impl

            await extract_stats_impl(
                file_path="/data/case.vtk",
                fields=["p", "U"],
                runner=mock_runner,
            )

            pipeline_def = mock_exec.call_args[0][0]
            assert pipeline_def.output.type == "data"
            assert pipeline_def.output.data is not None
            assert pipeline_def.output.data.statistics_only is True
            assert pipeline_def.output.data.fields == ["p", "U"]


class TestExecutePipelineImpl:
    @pytest.mark.asyncio
    async def test_parses_json_definition(self, mock_runner, mock_result):
        with patch("viznoir.tools.pipeline.execute_pipeline", return_value=mock_result):
            from viznoir.tools.pipeline import execute_pipeline_impl

            result = await execute_pipeline_impl(
                pipeline_json={
                    "source": {"file": "/data/case.vtk"},
                    "pipeline": [
                        {"filter": "Slice", "params": {"origin": [0, 0, 0]}},
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "p"},
                    },
                },
                runner=mock_runner,
            )

            assert result.output_type == "image"
