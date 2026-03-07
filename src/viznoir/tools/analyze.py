"""analyze_data tool — VTK data insight extraction."""

from __future__ import annotations

from typing import Any

from viznoir.core.runner import VTKRunner
from viznoir.engine.readers import read_dataset


async def analyze_data_impl(
    file_path: str,
    runner: VTKRunner,
    *,
    focus: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Load VTK file and run full analysis. Returns Level 2 insight report."""
    import asyncio

    def _run() -> dict[str, Any]:
        dataset = read_dataset(file_path)
        from viznoir.engine.analysis import analyze_dataset
        return analyze_dataset(dataset, focus=focus, domain=domain)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)
