"""animate tool — create animations from time series or orbit."""

from __future__ import annotations

from typing import Literal

from parapilot.core.compiler import ScriptCompiler
from parapilot.core.output import OutputHandler, PipelineResult
from parapilot.core.runner import VTKRunner
from parapilot.pipeline.engine import execute_pipeline
from parapilot.pipeline.models import (
    AnimationDef,
    CameraDef,
    OutputDef,
    PipelineDefinition,
    RenderDef,
    SourceDef,
)


async def animate_impl(
    file_path: str,
    field_name: str,
    runner: VTKRunner,
    mode: Literal["timesteps", "orbit"] = "timesteps",
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    fps: int = 24,
    time_range: list[float] | None = None,
    speed_factor: float = 1.0,
    orbit_duration: float = 10.0,
    width: int = 1920,
    height: int = 1080,
    files: list[str] | None = None,
    file_pattern: str | None = None,
    output_format: Literal["frames", "mp4", "webm", "gif"] = "frames",
    video_quality: int = 23,
    text_overlay: str | None = None,
) -> PipelineResult:
    """Create an animation (timestep series or camera orbit)."""
    pipeline_def = PipelineDefinition(
        source=SourceDef(
            file=file_path,
            files=files,
            file_pattern=file_pattern,
        ),
        pipeline=[],
        output=OutputDef(
            type="animation",
            animation=AnimationDef(
                render=RenderDef(
                    field=field_name,
                    colormap=colormap,
                    camera=CameraDef(preset=camera),
                    resolution=[width, height],
                ),
                fps=fps,
                time_range=time_range,
                speed_factor=speed_factor,
                mode=mode,
                orbit_duration=orbit_duration,
                output_format=output_format,
                video_quality=video_quality,
                text_overlay=text_overlay,
            ),
        ),
    )
    return await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())
