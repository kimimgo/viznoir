"""execute_pipeline tool — direct Layer 2 access for advanced users."""

from __future__ import annotations

from typing import Any

from parapilot.core.compiler import ScriptCompiler
from parapilot.core.output import OutputHandler, PipelineResult
from parapilot.core.runner import VTKRunner
from parapilot.pipeline.engine import execute_pipeline
from parapilot.pipeline.models import PipelineDefinition


async def execute_pipeline_impl(
    pipeline_json: dict[str, Any],
    runner: VTKRunner,
) -> PipelineResult:
    """Execute a pipeline from raw JSON definition. This is the L2 direct exposure."""
    definition = PipelineDefinition.model_validate(pipeline_json)
    return await execute_pipeline(definition, runner, ScriptCompiler(), OutputHandler())
