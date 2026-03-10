"""compose_assets tool — Compose multiple assets into a deliverable format."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from PIL import Image


async def compose_assets_impl(
    assets: list[dict[str, Any]],
    *,
    layout: str = "story",
    title: str | None = None,
    width: int = 1920,
    height: int = 1080,
    scenes: list[dict[str, Any]] | None = None,
    fps: int = 30,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Compose multiple assets into a deliverable format.

    Parameters
    ----------
    assets : list[dict]
        Each dict has ``type`` (render/latex/plot/text) and type-specific keys.
    layout : str
        One of: story, grid, slides, video.
    title : str | None
        Optional title for story layout.
    width, height : int
        Output dimensions in pixels.
    scenes : list[dict] | None
        Scene definitions for video layout (asset_indices, duration, transition).
    fps : int
        Frames per second for video export.
    output_dir : str | None
        Output directory. Defaults to VIZNOIR_OUTPUT_DIR or /tmp.

    Returns
    -------
    dict
        Result with output paths and metadata.
    """
    if output_dir is None:
        output_dir = os.environ.get("VIZNOIR_OUTPUT_DIR", "/tmp")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_event_loop()

    # Resolve asset images
    images = await loop.run_in_executor(None, _resolve_assets, assets)
    labels = [a.get("label", "") for a in assets]

    if layout == "story":
        result_img = await loop.run_in_executor(
            None,
            _render_story,
            images,
            labels,
            title,
            width,
            height,
        )
        filename = f"story_{uuid.uuid4().hex[:8]}.png"
        save_path = out_path / filename
        await loop.run_in_executor(None, result_img.save, str(save_path))
        return {
            "output_path": str(save_path),
            "layout": "story",
            "width": width,
            "height": height,
            "asset_count": len(images),
        }

    elif layout == "grid":
        from viznoir.anim.compositor import render_grid_layout

        result_img = await loop.run_in_executor(
            None,
            lambda: render_grid_layout(images, cols=2, width=width, height=height),
        )
        filename = f"grid_{uuid.uuid4().hex[:8]}.png"
        save_path = out_path / filename
        await loop.run_in_executor(None, result_img.save, str(save_path))
        return {
            "output_path": str(save_path),
            "layout": "grid",
            "width": width,
            "height": height,
            "asset_count": len(images),
        }

    elif layout == "slides":
        from viznoir.anim.compositor import render_slides_layout

        slide_imgs = await loop.run_in_executor(
            None,
            lambda: render_slides_layout(images, labels, width=width, height=height),
        )
        paths: list[str] = []
        batch_id = uuid.uuid4().hex[:8]

        def _save_slides() -> list[str]:
            saved: list[str] = []
            for i, slide in enumerate(slide_imgs):
                filename = f"slide_{batch_id}_{i:03d}.png"
                sp = out_path / filename
                slide.save(str(sp))
                saved.append(str(sp))
            return saved

        paths = await loop.run_in_executor(None, _save_slides)
        return {
            "output_paths": paths,
            "layout": "slides",
            "width": width,
            "height": height,
            "slide_count": len(slide_imgs),
        }

    elif layout == "video":
        result = await loop.run_in_executor(
            None,
            _render_video,
            images,
            labels,
            scenes,
            width,
            height,
            fps,
            str(out_path),
        )
        return result

    else:
        raise ValueError(f"Unknown layout: {layout}. Expected: story, grid, slides, video")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_assets(assets: list[dict[str, Any]]) -> list[Image.Image]:
    """Convert asset dicts to PIL Images."""
    images: list[Image.Image] = []
    for asset in assets:
        asset_type = asset.get("type", "render")

        if asset_type == "render" or asset_type == "plot":
            path = asset.get("path", "")
            if path and Path(path).exists():
                resolved = Path(path).resolve()
                data_dir = os.environ.get("VIZNOIR_DATA_DIR")
                if data_dir and not str(resolved).startswith(str(Path(data_dir).resolve())):
                    output_dir_env = os.environ.get("VIZNOIR_OUTPUT_DIR", "/tmp")
                    if not str(resolved).startswith(str(Path(output_dir_env).resolve())):
                        raise ValueError(f"Path '{path}' is outside allowed directories")
                images.append(Image.open(str(resolved)).convert("RGBA"))
            else:
                # Placeholder for missing files
                images.append(Image.new("RGBA", (400, 300), (80, 80, 80, 255)))

        elif asset_type == "latex":
            from viznoir.anim.latex import render_latex

            tex = asset.get("tex", "")
            color = asset.get("color", "FFFFFF")
            images.append(render_latex(tex, color=color))

        elif asset_type == "text":
            content = asset.get("content", "")
            img = _text_to_image(content)
            images.append(img)

        else:
            # Unknown type — grey placeholder
            images.append(Image.new("RGBA", (400, 300), (80, 80, 80, 255)))

    return images


def _text_to_image(text: str, width: int = 600, height: int = 200) -> Image.Image:
    """Render plain text content to an RGBA image."""
    from viznoir.anim.compositor import BG_COLOR, TEXT_WHITE, _get_font

    img = Image.new("RGBA", (width, height), BG_COLOR)
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    draw.text((20, 20), text, fill=TEXT_WHITE, font=font)
    return img


def _render_story(
    images: list[Image.Image],
    labels: list[str],
    title: str | None,
    width: int,
    height: int,
) -> Image.Image:
    """Wrapper for render_story_layout (needed for run_in_executor)."""
    from viznoir.anim.compositor import render_story_layout

    return render_story_layout(images, labels, title=title, width=width, height=height)


def _render_video(
    images: list[Image.Image],
    labels: list[str],
    scenes_dicts: list[dict[str, Any]] | None,
    width: int,
    height: int,
    fps: int,
    output_dir: str,
) -> dict[str, Any]:
    """Build timeline from scene dicts, render frames, and export video."""
    from viznoir.anim.compositor import export_video, render_story_layout
    from viznoir.anim.timeline import Scene, Timeline
    from viznoir.anim.transitions import get_transition

    # Build scenes
    if scenes_dicts:
        scene_objs = [
            Scene(
                asset_indices=s.get("asset_indices", [0]),
                duration=s.get("duration", 3.0),
                transition=s.get("transition", "fade_in"),
            )
            for s in scenes_dicts
        ]
    else:
        # Default: one scene per asset, 3 seconds each
        scene_objs = [Scene(asset_indices=[i], duration=3.0, transition="fade_in") for i in range(len(images))]

    tl = Timeline(scene_objs, fps=fps)
    frames: list[Image.Image] = []

    # Pre-render each scene's layout (avoid re-rendering per frame)
    scene_renders: dict[int, Image.Image] = {}
    for idx, scene in enumerate(scene_objs):
        scene_assets = [images[i] for i in scene.asset_indices if i < len(images)]
        scene_labels_list = [labels[i] for i in scene.asset_indices if i < len(labels)]
        scene_renders[idx] = render_story_layout(
            scene_assets,
            scene_labels_list,
            title=None,
            width=width,
            height=height,
        )

    prev_scene_idx = -1
    for global_t in tl.frame_times():
        scene_idx, local_t = tl.scene_at(global_t)
        base = scene_renders[scene_idx]

        # Apply transition effect (only in first 20% of scene)
        transition_duration = 0.2
        if local_t < transition_duration:
            t_norm = local_t / transition_duration
            try:
                tfn = get_transition(tl.scenes[scene_idx].transition)
                # fade_in/fade_out take (img, t); dissolve/wipe take (src, dst, t)
                if tl.scenes[scene_idx].transition in ("fade_in", "fade_out"):
                    base = tfn(base, t_norm)
                elif prev_scene_idx >= 0 and prev_scene_idx in scene_renders:
                    base = tfn(scene_renders[prev_scene_idx], base, t_norm)
                else:
                    base = tfn(base, t_norm)  # fallback to fade_in-like
            except (KeyError, TypeError):
                pass  # Unknown transition — skip

        frames.append(base)
        prev_scene_idx = scene_idx

    filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
    video_path = str(Path(output_dir) / filename)
    export_video(frames, video_path, fps=fps)

    return {
        "output_path": video_path,
        "layout": "video",
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": len(frames),
        "duration": tl.total_duration,
        "scene_count": len(scene_objs),
    }
