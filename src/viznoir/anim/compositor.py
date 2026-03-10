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

from PIL import Image, ImageDraw, ImageFont

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
    # Linux
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNSText.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    # Windows
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\segoeui.ttf",
    # CJK (Noto Sans)
    "NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/Supplemental/NotoSansCJK-Regular.ttc",
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


def _get_scaled_font(
    base_size: int, canvas_width: int, reference_width: int = 1920
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a font scaled proportionally to canvas width.

    Parameters
    ----------
    base_size : int
        Font size at *reference_width*.
    canvas_width : int
        Actual canvas width in pixels.
    reference_width : int
        Reference width for base_size (default 1920).
    """
    scale = canvas_width / reference_width
    scaled_size = max(12, int(base_size * scale))
    return _get_font(scaled_size)


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

LABEL_BG: tuple[int, int, int, int] = (0x1C, 0x1C, 0x2E, 180)


def _truncate_label(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> str:
    """Truncate *text* with '...' if it exceeds *max_width* pixels."""
    if not text:
        return text
    bbox = font.getbbox(text)
    if (bbox[2] - bbox[0]) <= max_width:
        return text
    ellipsis = "..."
    for end in range(len(text), 0, -1):
        candidate = text[:end] + ellipsis
        bbox = font.getbbox(candidate)
        if (bbox[2] - bbox[0]) <= max_width:
            return candidate
    return ellipsis


def _draw_label_with_bg(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    cx: int,
    cy: int,
    panel_width: int,
    padding: int = 10,
) -> None:
    """Draw *text* centered at *cx* with a semi-transparent rounded background.

    Parameters
    ----------
    draw : ImageDraw.ImageDraw
        Draw context (must belong to an RGBA canvas).
    text : str
        Label text to render.
    font : ImageFont
        Font to use.
    cx : int
        Horizontal center of the label area.
    cy : int
        Top y-coordinate of the label area.
    panel_width : int
        Width of the panel (used for truncation).
    padding : int
        Horizontal padding inside the background box.
    """
    if not text:
        return

    # Truncate if needed
    max_text_w = panel_width - 2 * padding
    text = _truncate_label(text, font, max_text_w)

    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Background box (centered horizontally at cx)
    box_pad = 6
    bx0 = cx - tw // 2 - box_pad
    by0 = cy - 2
    bx1 = cx + tw // 2 + box_pad
    by1 = cy + th + 4
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=4, fill=LABEL_BG)

    # Text (centered)
    tx = cx - tw // 2
    draw.text((tx, cy), text, fill=TEXT_DIM, font=font)


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
    min_panel_width: int = 200,
) -> Image.Image:
    """Compose assets in rows with optional title and bottom labels.

    If panels would be narrower than *min_panel_width*, assets are split
    across multiple rows automatically.

    Parameters
    ----------
    assets : list[Image.Image]
        Asset images to arrange.
    labels : list[str]
        Label text for each panel (padded with "" if shorter than assets).
    title : str | None
        Optional title text drawn at the top.
    width, height : int
        Output canvas dimensions.
    min_panel_width : int
        Minimum panel width before wrapping to a new row (default 200).

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

    # Responsive title/label heights
    title_h = max(40, int(60 * height / 1080)) if title else 0
    label_h = max(24, int(40 * height / 1080))
    padding = 20

    # Determine how many columns per row based on min_panel_width
    max_cols = max(1, (width - padding) // (min_panel_width + padding))
    cols_per_row = min(n, max_cols)
    num_rows = math.ceil(n / cols_per_row)

    panel_w = max(1, (width - padding * (cols_per_row + 1)) // cols_per_row)
    panel_area_y = title_h + padding
    row_h = max(1, (height - panel_area_y - padding) // num_rows)
    panel_area_h = row_h - label_h - padding

    # Draw title
    if title:
        title_font = _get_scaled_font(32, width)
        bbox = draw.textbbox((0, 0), title, font=title_font)
        tw = bbox[2] - bbox[0]
        tx = (width - tw) // 2
        draw.text((tx, max(8, int(16 * height / 1080))), title, fill=TEXT_WHITE, font=title_font)
        # Accent underline
        draw.line(
            [(tx, title_h - 8), (tx + tw, title_h - 8)],
            fill=ACCENT_TEAL,
            width=2,
        )

    # Draw panels
    label_font = _get_scaled_font(18, width)
    for i, (asset, label) in enumerate(zip(assets, labels)):
        row = i // cols_per_row
        col = i % cols_per_row

        px = padding + col * (panel_w + padding)
        py = panel_area_y + row * row_h

        # Resize asset to fit within panel, preserving aspect ratio
        thumb = _fit_resize(asset, panel_w, panel_area_h)
        # Center within panel region
        ox = px + (panel_w - thumb.width) // 2
        oy = py + (panel_area_h - thumb.height) // 2
        canvas.paste(thumb, (ox, oy), thumb)

        # Draw label below panel
        if label:
            label_cx = px + panel_w // 2
            label_cy = py + panel_area_h + 4
            _draw_label_with_bg(draw, label, label_font, label_cx, label_cy, panel_w, padding=10)

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
    labels: list[str] | None = None,
) -> Image.Image:
    """Arrange assets in an N x M grid with uniform padding and optional labels.

    Parameters
    ----------
    assets : list[Image.Image]
        Asset images to tile.
    cols : int
        Number of columns. Use 0 for auto (ceil(sqrt(n))).
    width, height : int
        Output canvas dimensions.
    labels : list[str] | None
        Optional label for each cell (padded with "" if shorter than assets).

    Returns
    -------
    Image.Image
        Composited RGBA image.
    """
    canvas = Image.new("RGBA", (width, height), BG_COLOR)

    n = len(assets)
    if n == 0:
        return canvas

    # Auto-calculate columns
    if cols <= 0:
        cols = math.ceil(math.sqrt(n))

    # Responsive padding
    padding = max(10, min(width, height) // 80)

    # Calculate rows from actual asset count
    rows = math.ceil(n / cols)

    # Label area
    label_h = max(20, int(30 * height / 1080)) if labels is not None else 0

    # Pad labels
    if labels is not None:
        while len(labels) < n:
            labels.append("")

    cell_w = max(1, (width - padding * (cols + 1)) // cols)
    cell_h = max(1, (height - padding * (rows + 1)) // rows)
    asset_h = cell_h - label_h

    draw = ImageDraw.Draw(canvas) if labels else None
    label_font = _get_scaled_font(16, width) if labels else None

    for idx, asset in enumerate(assets):
        row = idx // cols
        col = idx % cols

        cx = padding + col * (cell_w + padding)
        cy = padding + row * (cell_h + padding)

        thumb = _fit_resize(asset, cell_w, asset_h)
        ox = cx + (cell_w - thumb.width) // 2
        oy = cy + (asset_h - thumb.height) // 2
        canvas.paste(thumb, (ox, oy), thumb)

        # Draw label below cell
        if labels and draw and label_font:
            lbl = labels[idx]
            if lbl:
                label_cx = cx + cell_w // 2
                label_cy = cy + asset_h + 2
                _draw_label_with_bg(draw, lbl, label_font, label_cx, label_cy, cell_w, padding=8)

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
    label_font = _get_scaled_font(24, width)

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
            _draw_label_with_bg(draw, label, label_font, width // 2, height - label_h + 10, width, padding=40)

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
        "-y",  # overwrite
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{w}x{h}",
        "-r",
        str(fps),
        "-i",
        "pipe:0",  # read from stdin
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "23",
        "-preset",
        preset,
        "-movflags",
        "+faststart",
        "--",  # Prevent output_path from being interpreted as option
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
        raise RuntimeError(f"ffmpeg failed (exit {proc.returncode}): {stderr.decode(errors='replace')}")


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
