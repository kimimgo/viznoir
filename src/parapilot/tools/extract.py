"""Data extraction tools — plot_over_line, extract_stats, integrate_surface."""

from __future__ import annotations

from typing import Any

from parapilot.core.compiler import ScriptCompiler
from parapilot.core.output import OutputHandler
from parapilot.core.runner import VTKRunner
from parapilot.pipeline.engine import execute_pipeline
from parapilot.pipeline.models import (
    DataOutputDef,
    FilterStep,
    OutputDef,
    PipelineDefinition,
    SourceDef,
)


async def plot_over_line_impl(
    file_path: str,
    field_name: str,
    point1: list[float],
    point2: list[float],
    runner: VTKRunner,
    resolution: int = 100,
    timestep: float | str | None = None,
) -> dict[str, Any]:
    """Sample field values along a line."""
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep),
        pipeline=[
            FilterStep(
                filter="PlotOverLine",
                params={
                    "point1": point1,
                    "point2": point2,
                    "resolution": resolution,
                },
            ),
        ],
        output=OutputDef(
            type="data",
            data=DataOutputDef(
                fields=[field_name],
                include_coordinates=True,
            ),
        ),
    )
    result = await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())
    return result.json_data or {}


async def extract_stats_impl(
    file_path: str,
    fields: list[str],
    runner: VTKRunner,
    timestep: float | str | None = None,
    blocks: list[str] | None = None,
) -> dict[str, Any]:
    """Extract statistical summary (min/max/mean/std) for given fields."""
    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep, blocks=blocks),
        pipeline=[],
        output=OutputDef(
            type="data",
            data=DataOutputDef(
                fields=fields,
                statistics_only=True,
            ),
        ),
    )
    result = await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())
    return result.json_data or {}


async def integrate_surface_impl(
    file_path: str,
    field_name: str,
    runner: VTKRunner,
    boundary: str | None = None,
    timestep: float | str | None = None,
) -> dict[str, Any]:
    """Integrate a field over a surface (force, area, flux)."""
    steps: list[FilterStep] = []

    if boundary:
        steps.append(FilterStep(filter="ExtractBlock", params={"selector": boundary}))

    steps.append(FilterStep(filter="ExtractSurface"))
    steps.append(FilterStep(filter="IntegrateVariables"))

    pipeline_def = PipelineDefinition(
        source=SourceDef(file=file_path, timestep=timestep),
        pipeline=steps,
        output=OutputDef(
            type="data",
            data=DataOutputDef(fields=[field_name]),
        ),
    )
    result = await execute_pipeline(pipeline_def, runner, ScriptCompiler(), OutputHandler())
    return result.json_data or {}
