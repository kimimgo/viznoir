"""split_animate tool — create split-pane synchronized animations."""

from __future__ import annotations

from typing import Any

from viznoir.core.compiler import ScriptCompiler
from viznoir.core.output import OutputHandler, PipelineResult
from viznoir.core.runner import VTKRunner
from viznoir.pipeline.engine import execute_split_animation
from viznoir.pipeline.models import (
    OutputDef,
    PipelineDefinition,
    SourceDef,
    SplitAnimationDef,
)


async def split_animate_impl(
    file_path: str,
    panes: list[dict[str, Any]],
    runner: VTKRunner,
    layout: dict[str, Any] | None = None,
    fps: int = 24,
    time_range: list[float] | None = None,
    speed_factor: float = 1.0,
    resolution: list[int] | None = None,
    gif: bool = True,
    gif_loop: int = 0,
) -> PipelineResult:
    """Create a split-pane synchronized animation."""
    split_anim_data: dict[str, Any] = {
        "panes": panes,
        "fps": fps,
        "speed_factor": speed_factor,
        "gif": gif,
        "gif_loop": gif_loop,
    }
    if layout is not None:
        split_anim_data["layout"] = layout
    if time_range is not None:
        split_anim_data["time_range"] = time_range
    if resolution is not None:
        split_anim_data["resolution"] = resolution

    split_anim = SplitAnimationDef.model_validate(split_anim_data)

    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path),
        pipeline=[],
        output=OutputDef(
            type="split_animation",
            split_animation=split_anim,
        ),
    )

    return await execute_split_animation(pipeline_def, runner, ScriptCompiler(), OutputHandler())
