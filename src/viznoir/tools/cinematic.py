"""Cinematic render tool implementation."""

from __future__ import annotations

from viznoir.core.runner import VTKRunner


async def cinematic_render_impl(
    file_path: str,
    runner: VTKRunner,
    *,
    field_name: str | None = None,
    colormap: str = "Cool to Warm",
    quality: str = "standard",
    lighting: str | None = "cinematic",
    background: str | None = "dark_gradient",
    azimuth: float | None = None,
    elevation: float | None = None,
    fill_ratio: float = 0.75,
    metallic: float = 0.0,
    roughness: float = 0.5,
    ground_plane: bool = False,
    ssao: bool = True,
    fxaa: bool = True,
    width: int | None = None,
    height: int | None = None,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    output_filename: str = "cinematic.png",
) -> bytes:
    """Execute cinematic rendering via direct VTK API (no subprocess).

    Returns PNG bytes.
    """
    import asyncio

    def _run() -> bytes:
        from viznoir.engine.readers import get_timesteps, read_dataset
        from viznoir.engine.renderer import RenderConfig
        from viznoir.engine.renderer_cine import CinematicConfig
        from viznoir.engine.renderer_cine import cinematic_render as _cine_render

        # Resolve timestep
        ts = timestep
        if ts == "latest":
            steps = get_timesteps(file_path)
            ts = steps[-1] if steps else None
        elif isinstance(ts, str):
            ts = float(ts)

        # Read data
        data = read_dataset(file_path, timestep=ts)

        # Build config
        rc = RenderConfig(
            colormap=colormap.lower(),
            array_name=field_name,
            scalar_range=(float(scalar_range[0]), float(scalar_range[1])) if scalar_range else None,
        )

        if width is not None:
            rc.width = width
        if height is not None:
            rc.height = height

        config = CinematicConfig(
            render=rc,
            quality=quality,
            lighting_preset=lighting,
            background_preset=background,
            azimuth=azimuth,
            elevation=elevation,
            fill_ratio=fill_ratio,
            metallic=metallic,
            roughness=roughness,
            ground_plane=ground_plane,
            ssao=ssao,
            fxaa=fxaa,
        )

        return _cine_render(data, config)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)
