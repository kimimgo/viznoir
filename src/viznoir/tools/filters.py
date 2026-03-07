"""Filter-based visualization tools — slice, contour, clip, streamlines."""

from __future__ import annotations

from viznoir.core.compiler import ScriptCompiler
from viznoir.core.output import OutputHandler, PipelineResult
from viznoir.core.runner import VTKRunner
from viznoir.pipeline.engine import execute_pipeline
from viznoir.pipeline.models import (
    CameraDef,
    FilterStep,
    OutputDef,
    PipelineDefinition,
    RenderDef,
    SourceDef,
)


async def slice_impl(
    file_path: str,
    field_name: str,
    runner: VTKRunner,
    origin: list[float] | None = None,
    normal: list[float] | None = None,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
    zoom: float | None = None,
) -> PipelineResult:
    """Create a slice visualization."""
    cam = CameraDef(preset=camera)
    if zoom is not None:
        cam.zoom = zoom
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep),
        pipeline=[
            FilterStep(
                filter="Slice",
                params={
                    **({"origin": origin} if origin else {}),
                    **({"normal": normal} if normal else {}),
                },
            ),
        ],
        output=OutputDef(
            type="image",
            render=RenderDef(
                field=field_name,
                colormap=colormap,
                camera=cam,
                resolution=[width, height],
            ),
        ),
    )
    return await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())


async def contour_impl(
    file_path: str,
    field_name: str,
    isovalues: list[float],
    runner: VTKRunner,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
) -> PipelineResult:
    """Create an iso-surface visualization."""
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep),
        pipeline=[
            FilterStep(
                filter="Contour",
                params={
                    "field": field_name,
                    "isovalues": isovalues,
                },
            ),
        ],
        output=OutputDef(
            type="image",
            render=RenderDef(
                field=field_name,
                colormap=colormap,
                camera=CameraDef(preset=camera),
                resolution=[width, height],
            ),
        ),
    )
    return await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())


async def clip_impl(
    file_path: str,
    field_name: str,
    runner: VTKRunner,
    origin: list[float] | None = None,
    normal: list[float] | None = None,
    invert: bool = False,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
) -> PipelineResult:
    """Create a clipped visualization."""
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep),
        pipeline=[
            FilterStep(
                filter="Clip",
                params={
                    **({"origin": origin} if origin else {}),
                    **({"normal": normal} if normal else {}),
                    "invert": invert,
                },
            ),
        ],
        output=OutputDef(
            type="image",
            render=RenderDef(
                field=field_name,
                colormap=colormap,
                camera=CameraDef(preset=camera),
                resolution=[width, height],
            ),
        ),
    )
    return await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())


async def streamlines_impl(
    file_path: str,
    vector_field: str,
    runner: VTKRunner,
    seed_point1: list[float] | None = None,
    seed_point2: list[float] | None = None,
    seed_resolution: int = 20,
    max_length: float = 0.0,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
    zoom: float | None = None,
) -> PipelineResult:
    """Create a streamline visualization."""
    cam = CameraDef(preset=camera)
    if zoom is not None:
        cam.zoom = zoom
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep),
        pipeline=[
            FilterStep(
                filter="StreamTracer",
                params={
                    "vectors": ["POINTS", vector_field],
                    **({"seed_point1": seed_point1} if seed_point1 else {}),
                    **({"seed_point2": seed_point2} if seed_point2 else {}),
                    "seed_resolution": seed_resolution,
                    "max_length": max_length,
                },
            ),
        ],
        output=OutputDef(
            type="image",
            render=RenderDef(
                field=vector_field,
                representation="Wireframe",
                line_width=4.0,
                colormap=colormap,
                camera=cam,
                resolution=[width, height],
            ),
        ),
    )
    return await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())
