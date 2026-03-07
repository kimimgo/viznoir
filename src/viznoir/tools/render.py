"""render tool — create field visualization screenshots."""

from __future__ import annotations

from typing import Literal

from viznoir.core.compiler import ScriptCompiler
from viznoir.core.output import OutputHandler, PipelineResult
from viznoir.core.runner import VTKRunner
from viznoir.pipeline.engine import execute_pipeline
from viznoir.pipeline.models import (
    CameraDef,
    OutputDef,
    PipelineDefinition,
    RenderDef,
    SourceDef,
)


async def render_impl(
    file_path: str,
    field_name: str,
    runner: VTKRunner,
    association: Literal["POINTS", "CELLS"] = "POINTS",
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    scalar_range: list[float] | None = None,
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
    blocks: list[str] | None = None,
    zoom: float | None = None,
    background: list[float] | None = None,
    output_filename: str = "render.png",
) -> PipelineResult:
    """Render a field visualization and return the image."""
    cam = CameraDef(preset=camera)
    if zoom is not None:
        cam.zoom = zoom
    render = RenderDef(
        field=field_name,
        association=association,
        colormap=colormap,
        scalar_range=scalar_range,
        camera=cam,
        resolution=[width, height],
        output_filename=output_filename,
    )
    if background is not None:
        render.background = background
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep, blocks=blocks),
        pipeline=[],
        output=OutputDef(type="image", render=render),
    )
    return await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())
