"""inspect_data tool — extract metadata from simulation files."""

from __future__ import annotations

from typing import Any

from parapilot.core.compiler import ScriptCompiler
from parapilot.core.output import OutputHandler
from parapilot.core.runner import ParaViewRunner


async def inspect_data_impl(
    file_path: str,
    runner: ParaViewRunner,
) -> dict[str, Any]:
    """Inspect a simulation file and return metadata (bounds, arrays, timesteps, blocks)."""
    compiler = ScriptCompiler()
    output_handler = OutputHandler()

    script = compiler.compile_inspect(file_path)
    run_result = await runner.execute(script)
    result = output_handler.parse(run_result, "inspect")

    return result.json_data or {"error": "No metadata returned"}
