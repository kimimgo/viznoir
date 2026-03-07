"""Compare tool implementation — side-by-side visualization of two datasets."""

from __future__ import annotations

from typing import Any

from viznoir.core.runner import VTKRunner


async def compare_impl(
    file_a: str,
    file_b: str,
    runner: VTKRunner,
    *,
    field_name: str | None = None,
    mode: str = "side_by_side",
    colormap: str = "Cool to Warm",
    quality: str = "standard",
    width: int | None = None,
    height: int | None = None,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    label_a: str = "A",
    label_b: str = "B",
    output_filename: str = "compare.png",
) -> bytes:
    """Compare two datasets side-by-side or as a diff.

    Returns PNG bytes of the comparison image.
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
            steps_a = get_timesteps(file_a)
            ts = steps_a[-1] if steps_a else None
        elif isinstance(ts, str):
            ts = float(ts)

        # Read both datasets
        data_a = read_dataset(file_a, timestep=ts)
        data_b = read_dataset(file_b, timestep=ts)

        # Determine shared scalar range for consistent coloring
        shared_range = scalar_range
        if shared_range is None and field_name:
            from viznoir.engine.renderer import _get_scalar_range, _resolve_array, _resolve_renderable
            rd_a = _resolve_renderable(data_a)
            rd_b = _resolve_renderable(data_b)
            if rd_a and rd_b:
                _, assoc_a = _resolve_array(rd_a, field_name)
                _, assoc_b = _resolve_array(rd_b, field_name)
                lo_a, hi_a = _get_scalar_range(rd_a, field_name, assoc_a, -1)
                lo_b, hi_b = _get_scalar_range(rd_b, field_name, assoc_b, -1)
                shared_range = [min(lo_a, lo_b), max(hi_a, hi_b)]

        # Render settings
        half_w = (width or 1920) // 2
        h = height or 1080

        rc = RenderConfig(
            width=half_w,
            height=h,
            colormap=colormap.lower(),
            array_name=field_name,
            scalar_range=(float(shared_range[0]), float(shared_range[1])) if shared_range else None,
        )

        config = CinematicConfig(
            render=rc,
            quality=quality,
            ssao=quality != "draft",
            fxaa=True,
        )

        # Render both
        png_a = _cine_render(data_a, config)
        png_b = _cine_render(data_b, config)

        if mode == "side_by_side":
            return _compose_side_by_side(png_a, png_b, label_a, label_b, half_w, h)
        elif mode == "diff":
            return bytes(_compose_diff(data_a, data_b, field_name or "", config))
        else:
            return _compose_side_by_side(png_a, png_b, label_a, label_b, half_w, h)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


def _compose_side_by_side(
    png_a: bytes, png_b: bytes,
    label_a: str, label_b: str,
    half_w: int, h: int,
) -> bytes:
    """Compose two PNG images side by side with labels."""
    import io

    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont

    img_a = PILImage.open(io.BytesIO(png_a))
    img_b = PILImage.open(io.BytesIO(png_b))

    combined = PILImage.new("RGB", (half_w * 2, h))
    combined.paste(img_a, (0, 0))
    combined.paste(img_b, (half_w, 0))

    # Add labels
    draw = ImageDraw.Draw(combined)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()  # type: ignore[assignment]

    # White text with dark outline for visibility
    for label, x_offset in [(label_a, 20), (label_b, half_w + 20)]:
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            draw.text((x_offset + dx, 20 + dy), label, fill=(0, 0, 0), font=font)
        draw.text((x_offset, 20), label, fill=(255, 255, 255), font=font)

    # Divider line
    draw.line([(half_w, 0), (half_w, h)], fill=(255, 255, 255), width=2)

    buf = io.BytesIO()
    combined.save(buf, format="PNG")
    return buf.getvalue()


def _compose_diff(data_a: Any, data_b: Any, field_name: str, config: Any) -> bytes:
    """Compute and render field difference between two datasets."""
    import numpy as np
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

    from viznoir.engine.renderer import _resolve_array, _resolve_renderable
    from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render

    rd_a = _resolve_renderable(data_a)
    rd_b = _resolve_renderable(data_b)

    if rd_a is None or rd_b is None:
        from viznoir.engine.renderer_cine import cinematic_render as _cine_render
        return _cine_render(data_a or data_b, config)

    name_a, assoc_a = _resolve_array(rd_a, field_name)
    if name_a is None:
        from viznoir.engine.renderer_cine import cinematic_render as _cine_render
        return _cine_render(rd_a, config)

    attrs_a = rd_a.GetPointData() if assoc_a == "point" else rd_a.GetCellData()
    attrs_b = rd_b.GetPointData() if assoc_a == "point" else rd_b.GetCellData()

    arr_a = attrs_a.GetArray(name_a)
    arr_b = attrs_b.GetArray(name_a)

    if arr_a is None or arr_b is None:
        from viznoir.engine.renderer_cine import cinematic_render as _cine_render
        return _cine_render(rd_a, config)

    np_a = vtk_to_numpy(arr_a)
    np_b = vtk_to_numpy(arr_b)

    # Compute difference (handle size mismatch)
    min_len = min(len(np_a), len(np_b))
    diff = np.abs(np_a[:min_len] - np_b[:min_len])

    # Create diff array
    diff_vtk = numpy_to_vtk(diff)
    diff_vtk.SetName(f"diff_{name_a}")

    # Add to copy of dataset A
    output = vtk.vtkUnstructuredGrid()
    output.DeepCopy(rd_a)

    if assoc_a == "point":
        output.GetPointData().AddArray(diff_vtk)
    else:
        output.GetCellData().AddArray(diff_vtk)

    # Render the diff
    diff_config = CinematicConfig(
        render=config.render,
        quality=config.quality,
    )
    diff_config.render.array_name = f"diff_{name_a}"
    diff_config.render.colormap = "plasma"

    return cinematic_render(output, diff_config)
