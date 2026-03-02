"""Tests for pipeline validation (no Docker needed)."""

from __future__ import annotations

from typing import Any

import pytest

from parapilot.pipeline.engine import validate_pipeline
from parapilot.pipeline.models import (
    DataOutputDef,
    FilterStep,
    OutputDef,
    PipelineDefinition,
    RenderDef,
    SourceDef,
)


class TestValidatePipeline:
    def test_valid_render_pipeline(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Slice", params={"origin": [0, 0, 0]}),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert errors == []

    def test_valid_data_pipeline(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtu"),
            pipeline=[],
            output=OutputDef(
                type="data",
                data=DataOutputDef(fields=["p"]),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert errors == []

    def test_invalid_format(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.xyz"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        errors = validate_pipeline(pipeline)
        assert len(errors) == 1
        assert "Unsupported" in errors[0]

    def test_unknown_filter(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="FakeFilter")],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        errors = validate_pipeline(pipeline)
        assert len(errors) == 1
        assert "Unknown filter" in errors[0]

    def test_missing_required_param(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="Contour", params={"field": "p"})],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        errors = validate_pipeline(pipeline)
        assert any("isovalues" in e for e in errors)

    def test_image_without_render(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="image"),
        )
        errors = validate_pipeline(pipeline)
        assert any("render" in e.lower() for e in errors)

    def test_export_without_format(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="export"),
        )
        errors = validate_pipeline(pipeline)
        assert any("export_format" in e for e in errors)

    def test_empty_pipeline_valid(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="data",
                data=DataOutputDef(),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert errors == []


    def test_programmable_filter_blocked_by_default(self):
        """ProgrammableFilter should be rejected when PARAPILOT_ALLOW_PROGRAMMABLE is not set."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(
                    filter="ProgrammableFilter",
                    params={"script": "output.ShallowCopy(inputs[0].VTKObject)"},
                ),
            ],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        errors = validate_pipeline(pipeline)
        assert any("ProgrammableFilter is disabled" in e for e in errors)

    def test_programmable_filter_allowed_with_env(self, monkeypatch):
        """ProgrammableFilter should be accepted when PARAPILOT_ALLOW_PROGRAMMABLE=1."""
        monkeypatch.setenv("PARAPILOT_ALLOW_PROGRAMMABLE", "1")
        import importlib
        import parapilot.pipeline.engine as eng
        importlib.reload(eng)
        try:
            pipeline = PipelineDefinition(
                source=SourceDef(file="/data/case.vtk"),
                pipeline=[
                    FilterStep(
                        filter="ProgrammableFilter",
                        params={"script": "output.ShallowCopy(inputs[0].VTKObject)"},
                    ),
                ],
                output=OutputDef(type="image", render=RenderDef(field="p")),
            )
            errors = eng.validate_pipeline(pipeline)
            assert not any("ProgrammableFilter" in e for e in errors)
        finally:
            monkeypatch.delenv("PARAPILOT_ALLOW_PROGRAMMABLE", raising=False)
            importlib.reload(eng)


class TestCompileVideo:
    """Tests for compile_video function (P0-2)."""

    @pytest.mark.asyncio
    async def test_compile_video_no_ffmpeg(self, monkeypatch: Any):
        """compile_video should return error when ffmpeg is not available."""
        import shutil as _shutil

        from parapilot.pipeline.engine import compile_video

        monkeypatch.setattr(_shutil, "which", lambda _cmd: None)
        video_bytes, error = await compile_video(
            {"frame_000000.png": b"fake"}, fps=24.0
        )
        assert video_bytes is None
        assert error is not None
        assert "ffmpeg not found" in error

    @pytest.mark.asyncio
    async def test_compile_video_no_frames(self):
        """compile_video should return error when no frame files found."""
        from parapilot.pipeline.engine import compile_video

        video_bytes, error = await compile_video(
            {"result.json": b"{}"}, fps=24.0
        )
        assert video_bytes is None
        assert error is not None
        assert "No frame files" in error


class TestPipelineModels:
    def test_pipeline_from_json(self):
        data = {
            "source": {"file": "/data/case.foam", "timestep": "latest"},
            "pipeline": [
                {"filter": "Slice", "params": {"origin": [0, 0, 0], "normal": [1, 0, 0]}},
                {"filter": "Calculator", "params": {"expression": "mag(U)", "result_name": "Umag"}},
            ],
            "output": {
                "type": "image",
                "render": {"field": "Umag", "colormap": "Viridis"},
            },
        }
        pipeline = PipelineDefinition.model_validate(data)
        assert pipeline.source.file == "/data/case.foam"
        assert pipeline.source.timestep == "latest"
        assert len(pipeline.pipeline) == 2
        assert pipeline.pipeline[0].filter == "Slice"
        assert pipeline.output.type == "image"
        assert pipeline.output.render is not None
        assert pipeline.output.render.colormap == "Viridis"

    def test_pipeline_defaults(self):
        data = {
            "source": {"file": "/data/case.vtk"},
            "output": {"type": "data", "data": {}},
        }
        pipeline = PipelineDefinition.model_validate(data)
        assert pipeline.pipeline == []
        assert pipeline.source.timestep is None
        assert pipeline.output.data is not None
        assert pipeline.output.data.format == "json"
        assert pipeline.output.data.statistics_only is False
