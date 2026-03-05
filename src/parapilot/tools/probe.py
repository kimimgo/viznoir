"""probe_timeseries tool — sample field values at a point over time."""

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


async def probe_timeseries_impl(
    file_path: str,
    field_name: str,
    point: list[float],
    runner: VTKRunner,
    *,
    files: list[str] | None = None,
    file_pattern: str | None = None,
    time_range: list[float] | None = None,
) -> dict[str, Any]:
    """Sample a field value at a fixed point across timesteps.

    Returns dict with times and values arrays for plotting.
    """
    pipeline_def = PipelineDefinition(
        source=SourceDef(
            file=file_path,
            files=files,
            file_pattern=file_pattern,
        ),
        pipeline=[
            FilterStep(
                filter="ProbePoint",
                params={
                    "point": point,
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
