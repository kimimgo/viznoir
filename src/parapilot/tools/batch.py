"""batch_render tool — render multiple fields/views in one call."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from parapilot.core.runner import VTKRunner
from parapilot.engine.readers import get_timesteps, read_dataset
from parapilot.engine.renderer import RenderConfig
from parapilot.engine.renderer_cine import CinematicConfig, cinematic_render


async def batch_render_impl(
    file_path: str,
    fields: list[str],
    runner: VTKRunner,
    *,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
    quality: str = "standard",
) -> dict[str, Any]:
    """Render multiple fields from the same dataset in parallel.

    Returns dict with images list (field_name, base64, size_bytes).
    """

    def _render_field(field: str) -> dict[str, Any]:

        ts = timestep
        if ts == "latest":
            steps = get_timesteps(file_path)
            ts = steps[-1] if steps else None
        elif isinstance(ts, str):
            ts = float(ts)

        data = read_dataset(file_path, timestep=ts)

        rc = RenderConfig(
            width=width,
            height=height,
            colormap=colormap.lower(),
            array_name=field,
        )

        config = CinematicConfig(
            render=rc,
            quality=quality,
            ssao=quality != "draft",
            fxaa=True,
        )

        png_bytes = cinematic_render(data, config)
        return {
            "field": field,
            "base64": base64.b64encode(png_bytes).decode("ascii"),
            "size_bytes": len(png_bytes),
        }

    loop = asyncio.get_event_loop()
    results = await asyncio.gather(
        *[loop.run_in_executor(None, _render_field, f) for f in fields]
    )

    return {
        "images": list(results),
        "count": len(results),
        "fields": fields,
    }
