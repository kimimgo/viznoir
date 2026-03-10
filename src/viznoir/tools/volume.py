"""volume_render tool — volume rendering with transfer function presets."""

from __future__ import annotations

from viznoir.core.runner import VTKRunner
from viznoir.engine.transfer_functions import TRANSFER_PRESETS
from viznoir.tools.cinematic import cinematic_render_impl


async def volume_render_impl(
    file_path: str,
    runner: VTKRunner,
    *,
    field_name: str | None = None,
    transfer_preset: str = "generic",
    colormap: str = "viridis",
    quality: str = "standard",
    lighting: str | None = "cinematic",
    background: str | None = "dark_gradient",
    width: int | None = None,
    height: int | None = None,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    output_filename: str = "volume.png",
) -> bytes:
    """Render volumetric data with transfer function presets. Returns PNG bytes."""
    if transfer_preset not in TRANSFER_PRESETS:
        raise KeyError(f"Unknown transfer function preset: {transfer_preset}")

    return await cinematic_render_impl(
        file_path,
        runner,
        field_name=field_name,
        colormap=colormap,
        quality=quality,
        lighting=lighting,
        background=background,
        width=width,
        height=height,
        scalar_range=scalar_range,
        timestep=timestep,
        output_filename=output_filename,
    )
