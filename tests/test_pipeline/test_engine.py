"""Tests for pipeline validation (no Docker needed)."""

from __future__ import annotations

from typing import Any

import pytest

from viznoir.pipeline.engine import validate_pipeline
from viznoir.pipeline.models import (
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
        """ProgrammableFilter should be rejected when VIZNOIR_ALLOW_PROGRAMMABLE is not set."""
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
        """ProgrammableFilter should be accepted when VIZNOIR_ALLOW_PROGRAMMABLE=1."""
        monkeypatch.setenv("VIZNOIR_ALLOW_PROGRAMMABLE", "1")
        import importlib

        import viznoir.pipeline.engine as eng
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
            monkeypatch.delenv("VIZNOIR_ALLOW_PROGRAMMABLE", raising=False)
            importlib.reload(eng)


    def test_animation_without_animation_def(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="animation"),
        )
        errors = validate_pipeline(pipeline)
        assert any("animation" in e.lower() for e in errors)

    def test_split_animation_without_def(self):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="split_animation"),
        )
        errors = validate_pipeline(pipeline)
        assert any("split_animation" in e for e in errors)

    def test_split_animation_valid(self):
        from viznoir.pipeline.models import (
            GraphPaneDef,
            GraphSeriesDef,
            LayoutDef,
            PaneDef,
            RenderPaneDef,
            SplitAnimationDef,
        )
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(type="render", row=0, col=0,
                                render_pane=RenderPaneDef(render=RenderDef(field="p"))),
                        PaneDef(type="graph", row=0, col=1,
                                graph_pane=GraphPaneDef(series=[
                                    GraphSeriesDef(field="p", stat="mean"),
                                ])),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert errors == []

    def test_split_animation_row_out_of_range(self):
        from viznoir.pipeline.models import (
            LayoutDef,
            PaneDef,
            RenderPaneDef,
            SplitAnimationDef,
        )
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(type="render", row=5, col=0,
                                render_pane=RenderPaneDef(render=RenderDef(field="p"))),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert any("row 5 out of range" in e for e in errors)

    def test_split_animation_col_out_of_range(self):
        from viznoir.pipeline.models import (
            LayoutDef,
            PaneDef,
            RenderPaneDef,
            SplitAnimationDef,
        )
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(type="render", row=0, col=3,
                                render_pane=RenderPaneDef(render=RenderDef(field="p"))),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert any("col 3 out of range" in e for e in errors)

    def test_split_animation_render_without_render_pane(self):
        from viznoir.pipeline.models import (
            LayoutDef,
            PaneDef,
            SplitAnimationDef,
        )
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(type="render", row=0, col=0),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert any("render_pane" in e for e in errors)

    def test_split_animation_graph_without_graph_pane(self):
        from viznoir.pipeline.models import (
            LayoutDef,
            PaneDef,
            RenderPaneDef,
            SplitAnimationDef,
        )
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(type="render", row=0, col=0,
                                render_pane=RenderPaneDef(render=RenderDef(field="p"))),
                        PaneDef(type="graph", row=0, col=1),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert any("graph_pane" in e for e in errors)

    def test_split_animation_no_render_pane_at_all(self):
        from viznoir.pipeline.models import (
            GraphPaneDef,
            GraphSeriesDef,
            LayoutDef,
            PaneDef,
            SplitAnimationDef,
        )
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(type="graph", row=0, col=0,
                                graph_pane=GraphPaneDef(series=[
                                    GraphSeriesDef(field="p", stat="mean"),
                                ])),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        errors = validate_pipeline(pipeline)
        assert any("at least one render pane" in e for e in errors)


class TestCompileVideo:
    """Tests for compile_video function (P0-2)."""

    @pytest.mark.asyncio
    async def test_compile_video_no_ffmpeg(self, monkeypatch: Any):
        """compile_video should return error when ffmpeg is not available."""
        import shutil as _shutil

        from viznoir.pipeline.engine import compile_video

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
        from viznoir.pipeline.engine import compile_video

        video_bytes, error = await compile_video(
            {"result.json": b"{}"}, fps=24.0
        )
        assert video_bytes is None
        assert error is not None
        assert "No frame files" in error or "ffmpeg not found" in error

    @pytest.mark.asyncio
    async def test_compile_video_mp4_success(self):
        """compile_video produces MP4 when ffmpeg is available."""
        import shutil

        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg not available")

        # Create minimal PNG frames (1x1 pixel, 3 frames)
        import io

        from PIL import Image

        from viznoir.pipeline.engine import compile_video

        frames: dict[str, bytes] = {}
        for i in range(3):
            img = Image.new("RGB", (64, 64), color=(i * 80, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            frames[f"frame_{i:06d}.png"] = buf.getvalue()

        video_bytes, error = await compile_video(frames, fps=10.0)
        assert error is None
        assert video_bytes is not None
        assert len(video_bytes) > 100

    @pytest.mark.asyncio
    async def test_compile_video_gif_format(self):
        """compile_video produces GIF output."""
        import shutil

        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg not available")

        import io

        from PIL import Image

        from viznoir.pipeline.engine import compile_video

        frames: dict[str, bytes] = {}
        for i in range(3):
            img = Image.new("RGB", (64, 64), color=(0, i * 80, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            frames[f"frame_{i:06d}.png"] = buf.getvalue()

        video_bytes, error = await compile_video(frames, fps=5.0, output_format="gif")
        assert error is None
        assert video_bytes is not None
        # GIF magic bytes
        assert video_bytes[:3] == b"GIF"

    @pytest.mark.asyncio
    async def test_compile_video_with_text_overlay(self):
        """compile_video with text overlay doesn't crash."""
        import shutil

        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg not available")

        import io

        from PIL import Image

        from viznoir.pipeline.engine import compile_video

        frames: dict[str, bytes] = {}
        for i in range(3):
            img = Image.new("RGB", (128, 128), color=(0, 0, i * 80))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            frames[f"frame_{i:06d}.png"] = buf.getvalue()

        video_bytes, error = await compile_video(
            frames, fps=10.0, text_overlay="Test Case"
        )
        # May fail if ffmpeg doesn't support drawtext, so allow either outcome
        assert video_bytes is not None or error is not None

    @pytest.mark.asyncio
    async def test_compile_video_timeout(self, monkeypatch: Any):
        """compile_video handles timeout gracefully."""
        import asyncio as _asyncio
        import io
        import shutil

        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg not available")

        from PIL import Image

        from viznoir.pipeline.engine import compile_video

        frames: dict[str, bytes] = {}
        for i in range(2):
            img = Image.new("RGB", (32, 32), color=(255, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            frames[f"frame_{i:06d}.png"] = buf.getvalue()

        # Monkeypatch asyncio.wait_for to raise TimeoutError
        async def fake_wait_for(coro, timeout):
            raise _asyncio.TimeoutError()

        monkeypatch.setattr(_asyncio, "wait_for", fake_wait_for)

        video_bytes, error = await compile_video(frames, fps=10.0)
        assert video_bytes is None
        assert error is not None
        assert "timed out" in error

    @pytest.mark.asyncio
    async def test_compile_video_webm_format(self):
        """compile_video produces WebM output."""
        import shutil

        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg not available")

        import io

        from PIL import Image

        from viznoir.pipeline.engine import compile_video

        frames: dict[str, bytes] = {}
        for i in range(3):
            img = Image.new("RGB", (64, 64), color=(i * 80, i * 40, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            frames[f"frame_{i:06d}.png"] = buf.getvalue()

        video_bytes, error = await compile_video(frames, fps=10.0, output_format="webm")
        assert error is None
        assert video_bytes is not None
        assert len(video_bytes) > 100


class TestExecutePipeline:
    """Tests for execute_pipeline and execute_split_animation (mock runner/compiler)."""

    @pytest.mark.asyncio
    async def test_execute_pipeline_basic(self):
        """execute_pipeline runs compile→execute→parse flow."""
        from unittest.mock import AsyncMock, MagicMock

        from viznoir.core.output import PipelineResult
        from viznoir.core.runner import RunResult
        from viznoir.pipeline.engine import execute_pipeline

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )

        mock_runner = MagicMock()
        run_result = RunResult(
            exit_code=0,
            stdout="",
            stderr="",
            output_file_data={"render.png": b"\x89PNG"},
            json_result=None,
        )
        mock_runner.execute = AsyncMock(return_value=run_result)

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = "print('hello')"

        mock_output = MagicMock()
        mock_output.parse.return_value = PipelineResult(
            output_type="image",
            image_bytes=b"\x89PNG",
            json_data={"type": "image"},
        )

        result = await execute_pipeline(pipeline, mock_runner, mock_compiler, mock_output)
        assert result.output_type == "image"
        assert result.image_bytes == b"\x89PNG"
        mock_compiler.compile.assert_called_once()
        mock_runner.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_pipeline_validation_error(self):
        """execute_pipeline raises ValueError on invalid pipeline."""
        from unittest.mock import MagicMock

        from viznoir.pipeline.engine import execute_pipeline

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.xyz"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )

        mock_runner = MagicMock()
        with pytest.raises(ValueError, match="Invalid pipeline"):
            await execute_pipeline(pipeline, mock_runner)

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_video_compilation(self):
        """execute_pipeline compiles video when animation output with frames."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from viznoir.core.output import PipelineResult
        from viznoir.core.runner import RunResult
        from viznoir.pipeline.engine import execute_pipeline
        from viznoir.pipeline.models import AnimationDef

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(
                    render=RenderDef(field="p"),
                    fps=10,
                    output_format="mp4",
                ),
                render=RenderDef(field="p"),
            ),
        )

        run_result = RunResult(
            exit_code=0, stdout="", stderr="",
            output_file_data={"frame_000000.png": b"\x89PNG", "frame_000001.png": b"\x89PNG"},
            json_result={"effective_fps": 10.0},
        )
        mock_runner = MagicMock()
        mock_runner.execute = AsyncMock(return_value=run_result)

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = "script"

        mock_output = MagicMock()
        mock_output.parse.return_value = PipelineResult(
            output_type="animation",
            image_bytes=None,
            json_data={"type": "animation"},
        )

        with patch(
            "viznoir.pipeline.engine.compile_video",
            new_callable=AsyncMock,
            return_value=(b"fake_video_data", None),
        ):
            result = await execute_pipeline(
                pipeline, mock_runner, mock_compiler, mock_output
            )
        assert result.image_bytes == b"fake_video_data"
        assert result.json_data["video_format"] == "mp4"

    @pytest.mark.asyncio
    async def test_execute_pipeline_video_error(self):
        """execute_pipeline records video_error when compile_video fails."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from viznoir.core.output import PipelineResult
        from viznoir.core.runner import RunResult
        from viznoir.pipeline.engine import execute_pipeline
        from viznoir.pipeline.models import AnimationDef

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), fps=10, output_format="mp4"),
                render=RenderDef(field="p"),
            ),
        )

        run_result = RunResult(
            exit_code=0, stdout="", stderr="",
            output_file_data={"frame_000000.png": b"x"},
            json_result=None,
        )
        mock_runner = MagicMock()
        mock_runner.execute = AsyncMock(return_value=run_result)
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = "s"
        mock_output = MagicMock()
        mock_output.parse.return_value = PipelineResult(
            output_type="animation", image_bytes=None, json_data=None,
        )

        with patch(
            "viznoir.pipeline.engine.compile_video",
            new_callable=AsyncMock,
            return_value=(None, "ffmpeg not found"),
        ):
            result = await execute_pipeline(
                pipeline, mock_runner, mock_compiler, mock_output
            )
        assert result.json_data["video_error"] == "ffmpeg not found"

    @pytest.mark.asyncio
    async def test_execute_split_animation(self):
        """execute_split_animation runs two-phase pipeline."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from viznoir.core.runner import RunResult
        from viznoir.pipeline.engine import execute_split_animation
        from viznoir.pipeline.models import (
            GraphPaneDef,
            GraphSeriesDef,
            LayoutDef,
            PaneDef,
            RenderPaneDef,
            SplitAnimationDef,
        )

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render", row=0, col=0,
                            render_pane=RenderPaneDef(
                                render=RenderDef(field="p")
                            ),
                        ),
                        PaneDef(
                            type="graph", row=0, col=1,
                            graph_pane=GraphPaneDef(
                                series=[GraphSeriesDef(field="p", stat="mean")]
                            ),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )

        run_result = RunResult(
            exit_code=0, stdout="", stderr="",
            output_file_data={
                "frame_000000.png": b"\x89PNG",
                "stats.json": b'{"p_mean": [1.0, 2.0]}',
            },
            json_result={"frame_count": 1, "effective_fps": 5.0},
        )
        mock_runner = MagicMock()
        mock_runner.execute = AsyncMock(return_value=run_result)
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = "script"

        mock_compositor = MagicMock()
        mock_compositor.compose_all.return_value = (
            [b"composed_frame"],
            b"GIF89a_fake",
        )

        with patch(
            "viznoir.core.compositor.Compositor",
            return_value=mock_compositor,
        ):
            result = await execute_split_animation(
                pipeline, mock_runner, mock_compiler
            )
        assert result.output_type == "split_animation"
        assert result.image_bytes == b"GIF89a_fake"
        assert result.json_data["frame_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_split_animation_no_split_def(self):
        """execute_split_animation raises on missing split_animation."""
        from unittest.mock import MagicMock

        from viznoir.pipeline.engine import execute_split_animation

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="split_animation"),
        )
        mock_runner = MagicMock()
        # Validation should catch this first
        with pytest.raises(ValueError):
            await execute_split_animation(pipeline, mock_runner)

    async def test_execute_split_animation_none_after_validation(self):
        """L107: split_animation is None after validation passes (defensive guard)."""
        from unittest.mock import MagicMock, patch

        from viznoir.pipeline.engine import execute_split_animation

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="split_animation"),
            # split_animation is None (no definition provided)
        )
        mock_runner = MagicMock()
        # Bypass validation to reach L107
        with patch("viznoir.pipeline.engine.validate_pipeline", return_value=[]):
            with pytest.raises(ValueError, match="split_animation definition is required"):
                await execute_split_animation(pipeline, mock_runner)


class TestCompileVideoEdgeCases:
    """Additional compile_video edge cases for coverage."""

    @pytest.mark.asyncio
    async def test_compile_video_ffmpeg_nonzero_exit(self):
        """compile_video returns error on ffmpeg non-zero exit."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from viznoir.pipeline.engine import compile_video

        frames = {"frame_000000.png": b"\x89PNG", "frame_000001.png": b"\x89PNG"}

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"encoding error"))
        mock_proc.kill = MagicMock()

        async def mock_create(*args, **kwargs):
            return mock_proc

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("asyncio.create_subprocess_exec", side_effect=mock_create):
            video_bytes, error = await compile_video(frames, fps=10.0)

        assert video_bytes is None
        assert error is not None
        assert "ffmpeg failed" in error

    @pytest.mark.asyncio
    async def test_compile_video_no_output_file(self):
        """compile_video returns error when ffmpeg produces no output."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from viznoir.pipeline.engine import compile_video

        frames = {"frame_000000.png": b"\x89PNG"}

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        async def mock_create(*args, **kwargs):
            return mock_proc

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("asyncio.create_subprocess_exec", side_effect=mock_create):
            video_bytes, error = await compile_video(frames, fps=10.0)

        assert video_bytes is None
        assert error is not None
        assert "no output" in error.lower()


class TestEffectiveFpsFromJsonData:
    """Cover line 285: effective_fps override from json_data."""

    @pytest.mark.asyncio
    async def test_effective_fps_used_from_json_data(self):
        """When result.json_data has effective_fps, use it for video compilation."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from viznoir.core.output import PipelineResult
        from viznoir.core.runner import RunResult
        from viznoir.pipeline.engine import execute_pipeline
        from viznoir.pipeline.models import AnimationDef

        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), fps=10, output_format="mp4"),
                render=RenderDef(field="p"),
            ),
        )

        run_result = RunResult(
            exit_code=0, stdout="", stderr="",
            output_file_data={"frame_000000.png": b"\x89PNG"},
            json_result=None,
        )
        mock_runner = MagicMock()
        mock_runner.execute = AsyncMock(return_value=run_result)
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = "s"
        mock_output = MagicMock()
        mock_output.parse.return_value = PipelineResult(
            output_type="animation", image_bytes=None,
            json_data={"effective_fps": 24.0},
        )

        with patch(
            "viznoir.pipeline.engine.compile_video",
            new_callable=AsyncMock,
            return_value=(b"video", None),
        ) as mock_compile:
            await execute_pipeline(pipeline, mock_runner, mock_compiler, mock_output)
            # effective_fps should be 24.0 (from json_data), not 10 (from AnimationDef)
            mock_compile.assert_called_once()
            call_kwargs = mock_compile.call_args
            assert call_kwargs[1]["fps"] == 24.0 or call_kwargs[0][1] == 24.0


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
