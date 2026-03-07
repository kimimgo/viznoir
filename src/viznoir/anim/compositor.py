"""viznoir.anim.compositor — Frame compositor with layout rendering + video export.

Provides three layout modes for compositing multiple asset images:
  - story: row of panels with title bar and bottom labels
  - grid: N x M grid with padding
  - slides: one slide per asset, centered with label

Also provides ffmpeg-based video export from frame sequences.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Color palette (dark cinematic theme)
# ---------------------------------------------------------------------------

BG_COLOR: tuple[int, int, int, int] = (0x1C, 0x1C, 0x2E, 255)
TEXT_WHITE: tuple[int, int, int, int] = (255, 255, 255, 255)
TEXT_DIM: tuple[int, int, int, int] = (0x88, 0x92, 0xB0, 255)
ACCENT_TEAL: tuple[int, int, int, int] = (0x00, 0xD4, 0xAA, 255)

# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

_FONT_CANDIDATES = [
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font, fall back to Pillow's built-in default."""
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    # Fallback: Pillow built-in bitmap font (cannot be resized, but won't crash)
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Layout: story
# ---------------------------------------------------------------------------


def render_story_layout(
    assets: list[Image.Image],
    labels: list[str],
    *,
    title: str | None = None,
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Compose assets in a horizontal row with optional title and bottom labels.

    Parameters
    ----------
    assets : list[Image.Image]
        Asset images to arrange in a row.
    labels : list[str]
        Label text for each panel (padded with "" if shorter than assets).
    title : str | None
        Optional title text drawn at the top.
    width, height : int
        Output canvas dimensions.

    Returns
    -------
    Image.Image
        Composited RGBA image.
    """
    canvas = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Pad labels to match asset count
    while len(labels) < len(assets):
        labels.append("")

    n = len(assets)
    if n == 0:
        return canvas

    # Layout geometry
    title_h = 60 if title else 0
    label_h = 40
    padding = 20
    panel_area_y = title_h + padding
    panel_area_h = height - panel_area_y - label_h - padding
    panel_w = (width - padding * (n + 1)) // n

    # Draw title
    if title:
        title_font = _get_font(32)
        bbox = draw.textbbox((0, 0), title, font=title_font)
        tw = bbox[2] - bbox[0]
        tx = (width - tw) // 2
        draw.text((tx, 16), title, fill=TEXT_WHITE, font=title_font)
        # Accent underline
        draw.line(
            [(tx, title_h - 8), (tx + tw, title_h - 8)],
            fill=ACCENT_TEAL,
            width=2,
        )

    # Draw panels
    label_font = _get_font(18)
    for i, (asset, label) in enumerate(zip(assets, labels)):
        # Target panel region
        px = padding + i * (panel_w + padding)
        py = panel_area_y

        # Resize asset to fit within panel, preserving aspect ratio
        thumb = _fit_resize(asset, panel_w, panel_area_h)
        # Center within panel region
        ox = px + (panel_w - thumb.width) // 2
        oy = py + (panel_area_h - thumb.height) // 2
        canvas.paste(thumb, (ox, oy), thumb)

        # Draw label below panel
        if label:
            lbbox = draw.textbbox((0, 0), label, font=label_font)
            lw = lbbox[2] - lbbox[0]
            lx = px + (panel_w - lw) // 2
            ly = py + panel_area_h + 4
            draw.text((lx, ly), label, fill=TEXT_DIM, font=label_font)

    return canvas


# ---------------------------------------------------------------------------
# Layout: grid
# ---------------------------------------------------------------------------


def render_grid_layout(
    assets: list[Image.Image],
    cols: int = 2,
    *,
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Arrange assets in an N x M grid with uniform padding.

    Parameters
    ----------
    assets : list[Image.Image]
        Asset images to tile.
    cols : int
        Number of columns.
    width, height : int
        Output canvas dimensions.

    Returns
    -------
    Image.Image
        Composited RGBA image.
    """
    canvas = Image.new("RGBA", (width, height), BG_COLOR)

    n = len(assets)
    if n == 0:
        return canvas

    padding = 10
    rows = math.ceil(n / cols)

    cell_w = (width - padding * (cols + 1)) // cols
    cell_h = (height - padding * (rows + 1)) // rows

    for idx, asset in enumerate(assets):
        row = idx // cols
        col = idx % cols

        cx = padding + col * (cell_w + padding)
        cy = padding + row * (cell_h + padding)

        thumb = _fit_resize(asset, cell_w, cell_h)
        ox = cx + (cell_w - thumb.width) // 2
        oy = cy + (cell_h - thumb.height) // 2
        canvas.paste(thumb, (ox, oy), thumb)

    return canvas


# ---------------------------------------------------------------------------
# Layout: slides
# ---------------------------------------------------------------------------


def render_slides_layout(
    assets: list[Image.Image],
    labels: list[str],
    *,
    width: int = 1920,
    height: int = 1080,
) -> list[Image.Image]:
    """Create one slide per asset, centered with label at the bottom.

    Parameters
    ----------
    assets : list[Image.Image]
        One image per slide.
    labels : list[str]
        Label for each slide (padded with "" if shorter than assets).
    width, height : int
        Slide dimensions.

    Returns
    -------
    list[Image.Image]
        List of slide images.
    """
    # Pad labels
    while len(labels) < len(assets):
        labels.append("")

    slides: list[Image.Image] = []
    label_font = _get_font(24)

    for asset, label in zip(assets, labels):
        slide = Image.new("RGBA", (width, height), BG_COLOR)
        draw = ImageDraw.Draw(slide)

        # Fit asset in the center region (leave 80px at bottom for label)
        label_h = 80
        max_w = width - 80  # 40px padding each side
        max_h = height - label_h - 40

        thumb = _fit_resize(asset, max_w, max_h)
        ox = (width - thumb.width) // 2
        oy = (height - label_h - thumb.height) // 2
        slide.paste(thumb, (ox, oy), thumb)

        # Draw label at bottom center
        if label:
            bbox = draw.textbbox((0, 0), label, font=label_font)
            lw = bbox[2] - bbox[0]
            lx = (width - lw) // 2
            ly = height - label_h + 10
            draw.text((lx, ly), label, fill=TEXT_DIM, font=label_font)

        slides.append(slide)

    return slides


# ---------------------------------------------------------------------------
# Video export via ffmpeg
# ---------------------------------------------------------------------------


def export_video(
    frames: list[Image.Image],
    output_path: str,
    *,
    fps: int = 30,
    preset: str = "medium",
) -> None:
    """Export a sequence of PIL Image frames to an MP4 video via ffmpeg pipe.

    Uses rawvideo RGBA input piped to ffmpeg stdin, encoded with libx264 yuv420p.

    Parameters
    ----------
    frames : list[Image.Image]
        Frame images (must all have the same size).
    output_path : str
        Path to the output .mp4 file.
    fps : int
        Frames per second.
    preset : str
        x264 encoding preset (ultrafast/fast/medium/slow/veryslow).

    Raises
    ------
    ValueError
        If frames list is empty.
    RuntimeError
        If ffmpeg exits with a non-zero return code.
    """
    if not frames:
        raise ValueError("No frames provided for video export")

    w, h = frames[0].size
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                       # overwrite
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{w}x{h}",
        "-r", str(fps),
        "-i", "pipe:0",             # read from stdin
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        "-preset", preset,
        "-movflags", "+faststart",
        output_path,
    ]

    with subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        for frame in frames:
            rgba = frame.convert("RGBA")
            proc.stdin.write(rgba.tobytes())  # type: ignore[union-attr]
        _, stderr = proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fit_resize(
    img: Image.Image,
    max_w: int,
    max_h: int,
) -> Image.Image:
    """Resize image to fit within max_w x max_h, preserving aspect ratio.

    Uses LANCZOS resampling for high quality.
    """
    if max_w <= 0 or max_h <= 0:
        return img

    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        return img

    scale = min(max_w / src_w, max_h / src_h)
    if scale >= 1.0:
        # No upscale needed — return as-is
        return img

    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
