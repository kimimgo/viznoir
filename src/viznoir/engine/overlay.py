"""Pillow-based 2D overlay compositing for VTK renders.

VTK handles 3D rendering; this module handles all 2D annotations:
title, subtitle, scalar bar, watermark.

All dimensions auto-scale with image resolution — designed at 1280x720
and proportionally scaled for any output size (e.g., 1920x1080 → 1.5x).

Usage::

    from viznoir.engine.overlay import compose, ScalarBarConfig

    raw_png = vtk_renderer.render(data, camera)  # 3D only, no text
    final_png = compose(
        raw_png,
        title="Pressure Distribution",
        scalar_bar=ScalarBarConfig(colormap="coolwarm", range=(-1.19, 0.49)),
    )
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

__all__: list[str] = [
    "OverlayTheme",
    "ScalarBarConfig",
    "compose",
    "compose_image",
    "draw_scalar_bar",
    "draw_title",
    "draw_watermark",
    "THEMES",
]

# Reference resolution for all base dimensions (720p).
_REF_DIAG: float = sqrt(1280**2 + 720**2)  # ~1468.6


def _scale(img: Image.Image) -> float:
    """Compute scale factor relative to 1280x720 reference."""
    w: int
    h: int
    w, h = img.size
    return sqrt(w * w + h * h) / _REF_DIAG


# ======================================================================
# Font management
# ======================================================================

_FONT_SEARCH_PATHS: list[str] = [
    # Korean
    "/usr/share/fonts/NanumFont/NanumGothicBold.ttf",
    "/usr/share/fonts/NanumFont/NanumGothic.ttf",
    # Mono (for labels)
    "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    # Sans
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _find_font(style: str = "sans", bold: bool = False) -> str | None:
    """Find a system font path by style."""
    patterns: dict[str, list[str]] = {
        "sans": ["NanumGothic", "DejaVuSans", "LiberationSans"],
        "mono": ["NotoSansMono", "DejaVuSansMono"],
    }
    names: list[str] = patterns.get(style, patterns["sans"])
    bold_suffix: str = "Bold"

    for path_str in _FONT_SEARCH_PATHS:
        p: Path = Path(path_str)
        if not p.exists():
            continue
        stem: str = p.stem
        for name in names:
            if name in stem:
                if bold and bold_suffix in stem:
                    return str(p)
                if not bold and bold_suffix not in stem:
                    return str(p)
    for path_str in _FONT_SEARCH_PATHS:
        if Path(path_str).exists():
            return path_str
    return None


def get_font(size: int, style: str = "sans", bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a cached font. Falls back to Pillow default if no TTF found."""
    key: tuple[str, int] = (f"{style}_{bold}", size)
    if key in _font_cache:
        return _font_cache[key]

    path: str | None = _find_font(style, bold)
    font: ImageFont.FreeTypeFont
    if path is not None:
        font = ImageFont.truetype(path, size)
    else:
        font = ImageFont.load_default(size=size)  # type: ignore[assignment]

    _font_cache[key] = font
    return font


# ======================================================================
# Theme
# ======================================================================

@dataclass(frozen=True, slots=True)
class OverlayTheme:
    """Color scheme for overlay elements."""

    name: str
    bg: tuple[int, int, int, int]           # background panel (RGBA)
    text_primary: tuple[int, int, int]       # title, bar title
    text_secondary: tuple[int, int, int]     # subtitle, watermark
    text_muted: tuple[int, int, int]         # tick labels
    bar_outline: tuple[int, int, int, int]   # scalar bar border
    bar_height_ratio: float = 0.55           # bar height / image height

    # --- Base sizes at 1280x720 (auto-scaled at render time) ---
    base_margin: int = 28
    base_bar_width: int = 30
    base_title_size: int = 32
    base_subtitle_size: int = 18
    base_label_size: int = 18
    base_bar_title_size: int = 18
    base_watermark_size: int = 15


THEMES: dict[str, OverlayTheme] = {
    "dark": OverlayTheme(
        name="dark",
        bg=(15, 15, 20, 220),
        text_primary=(240, 240, 245),
        text_secondary=(160, 160, 170),
        text_muted=(200, 200, 210),
        bar_outline=(90, 90, 100, 200),
    ),
    "light": OverlayTheme(
        name="light",
        bg=(255, 255, 255, 220),
        text_primary=(25, 25, 30),
        text_secondary=(90, 90, 100),
        text_muted=(50, 50, 60),
        bar_outline=(180, 180, 190, 200),
    ),
    "paper": OverlayTheme(
        name="paper",
        bg=(250, 248, 245, 230),
        text_primary=(20, 20, 20),
        text_secondary=(70, 70, 70),
        text_muted=(40, 40, 40),
        bar_outline=(120, 120, 120, 200),
        base_margin=36,
        base_bar_width=26,
    ),
    "transparent": OverlayTheme(
        name="transparent",
        bg=(0, 0, 0, 0),
        text_primary=(255, 255, 255),
        text_secondary=(180, 180, 180),
        text_muted=(200, 200, 200),
        bar_outline=(100, 100, 100, 160),
    ),
}


# ======================================================================
# Scalar bar config
# ======================================================================

@dataclass(frozen=True, slots=True)
class ScalarBarConfig:
    """Configuration for a Pillow-drawn scalar bar."""

    colormap: str = "cool to warm"
    range: tuple[float, float] = (0.0, 1.0)
    title: str = ""
    n_labels: int = 5
    log_scale: bool = False
    position: str = "right"     # "right" or "left"
    label_format: str = ".3g"   # Python format spec


# ======================================================================
# Colormap sampling
# ======================================================================

def _sample_colormap(name: str, n: int = 256) -> list[tuple[int, int, int]]:
    """Sample colormap into n RGB tuples (0-255)."""
    from .colormaps import COLORMAP_REGISTRY

    key: str = name.lower().strip()
    pts: list[tuple[float, float, float, float]] | None = COLORMAP_REGISTRY.get(key)
    if pts is None:
        pts = COLORMAP_REGISTRY.get(
            "cool to warm", [(0.0, 0.5, 0.5, 0.5), (1.0, 0.5, 0.5, 0.5)],
        )

    # Note: pts is now guaranteed to be a list due to the fallback
    valid_pts: list[tuple[float, float, float, float]] = pts

    colors: list[tuple[int, int, int]] = []
    for i in range(n):
        t: float = i / max(n - 1, 1)
        lo_idx: int = 0
        for j in range(len(valid_pts) - 1):
            if valid_pts[j + 1][0] >= t:
                lo_idx = j
                break
        else:
            lo_idx = len(valid_pts) - 2

        p0, r0, g0, b0 = valid_pts[lo_idx]
        p1, r1, g1, b1 = valid_pts[lo_idx + 1]
        frac: float = max(0.0, min(1.0, (t - p0) / max(p1 - p0, 1e-10)))
        r: float = r0 + (r1 - r0) * frac
        g: float = g0 + (g1 - g0) * frac
        b: float = b0 + (b1 - b0) * frac
        colors.append((int(r * 255), int(g * 255), int(b * 255)))

    return colors


# ======================================================================
# Drawing functions (all sizes auto-scaled)
# ======================================================================

def _s(base: int | float, scale: float) -> int:
    """Scale a base dimension."""
    return max(1, int(base * scale))


def draw_scalar_bar(
    img: Image.Image,
    config: ScalarBarConfig,
    theme: OverlayTheme,
    *,
    y_top: int | None = None,
    y_bottom: int | None = None,
) -> int:
    """Draw vertical scalar bar. Returns panel width."""
    w: int
    h: int
    w, h = img.size
    sc: float = _scale(img)

    margin: int = _s(theme.base_margin, sc)
    bar_w: int = _s(theme.base_bar_width, sc)
    bar_h: int = int(h * theme.bar_height_ratio)

    if y_top is None:
        y_top = margin + _s(12, sc)
    if y_bottom is None:
        y_bottom = y_top + bar_h
    bar_h = y_bottom - y_top

    # Scaled fonts
    label_font: ImageFont.FreeTypeFont = get_font(_s(theme.base_label_size, sc), "mono")
    title_font: ImageFont.FreeTypeFont = get_font(_s(theme.base_bar_title_size, sc), "sans", bold=True)

    # Measure label width
    lo: float
    hi: float
    lo, hi = config.range
    samples: list[str] = [format(v, config.label_format) for v in (lo, hi, (lo + hi) / 2)]
    label_w: int = max(int(label_font.getlength(s)) for s in samples)

    gap: int = _s(10, sc)
    pad: int = _s(16, sc)
    title_h: int = _s(28, sc) if config.title else 0

    panel_w: int = pad + label_w + gap + bar_w + pad

    panel_x: int
    if config.position == "right":
        panel_x = w - margin - panel_w
    else:
        panel_x = margin

    bar_x: int = panel_x + pad + label_w + gap
    label_x_right: int = bar_x - gap

    # Background panel
    overlay: Image.Image = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(overlay, "RGBA")

    draw.rounded_rectangle(
        [panel_x, y_top - pad - title_h, panel_x + panel_w, y_bottom + pad],
        radius=_s(10, sc),
        fill=theme.bg,
    )

    # Gradient strip — bulk pixel write (much faster than per-row draw.line)
    colors: list[tuple[int, int, int]] = _sample_colormap(config.colormap, bar_h)
    grad: Image.Image = Image.new("RGB", (1, bar_h))
    grad.putdata([colors[bar_h - 1 - i] for i in range(bar_h)])
    grad = grad.resize((bar_w, bar_h), Image.Resampling.NEAREST)
    overlay.paste(grad, (bar_x, y_top))

    # Border
    draw.rectangle(
        [bar_x - 1, y_top - 1, bar_x + bar_w, y_bottom],
        outline=theme.bar_outline,
        width=max(1, _s(1.5, sc)),
    )

    # Tick labels
    label_half_h: int = _s(9, sc)
    tick_w: int = _s(5, sc)
    for i in range(config.n_labels):
        frac: float = i / max(config.n_labels - 1, 1)
        val: float = lo + frac * (hi - lo)
        label: str = format(val, config.label_format)
        y_tick: int = y_bottom - int(frac * bar_h)

        tw: int = int(label_font.getlength(label))
        lx: int = label_x_right - tw
        draw.text((lx, y_tick - label_half_h), label, fill=theme.text_muted, font=label_font)
        draw.line(
            [(bar_x - tick_w, y_tick), (bar_x, y_tick)],
            fill=theme.bar_outline,
            width=max(1, _s(1.5, sc)),
        )

    # Title above bar
    if config.title:
        tw = int(title_font.getlength(config.title))
        tx: int = panel_x + (panel_w - tw) // 2
        draw.text(
            (tx, y_top - pad - title_h + _s(4, sc)),
            config.title,
            fill=theme.text_primary,
            font=title_font,
        )

    img.alpha_composite(overlay)
    return panel_w


def draw_title(
    img: Image.Image,
    title: str,
    theme: OverlayTheme,
    subtitle: str = "",
    position: str = "top_left",
) -> int:
    """Draw title + subtitle. Returns height consumed."""
    sc: float = _scale(img)
    margin: int = _s(theme.base_margin, sc)

    title_font: ImageFont.FreeTypeFont = get_font(_s(theme.base_title_size, sc), "sans", bold=True)
    sub_font: ImageFont.FreeTypeFont = get_font(_s(theme.base_subtitle_size, sc), "mono")

    title_bbox: tuple[float, float, float, float] | tuple[int, int, int, int] = (
        title_font.getbbox(title) if title else (0, 0, 0, 0)
    )
    sub_bbox: tuple[float, float, float, float] | tuple[int, int, int, int] = (
        sub_font.getbbox(subtitle) if subtitle else (0, 0, 0, 0)
    )

    title_h: int = int(title_bbox[3] - title_bbox[1]) if title else 0
    sub_h: int = int(sub_bbox[3] - sub_bbox[1]) if subtitle else 0

    title_w: int = int(title_font.getlength(title)) if title else 0
    sub_w: int = int(sub_font.getlength(subtitle)) if subtitle else 0
    max_w: int = max(title_w, sub_w)
    gap: int = _s(10, sc)
    total_h: int = title_h + (sub_h + gap if subtitle else 0)

    w: int = img.size[0]
    pad: int = _s(14, sc)

    x: int
    if "right" in position:
        x = w - margin - max_w - pad
    elif "center" in position:
        x = (w - max_w) // 2
    else:
        x = margin

    y: int = margin

    overlay: Image.Image = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(overlay, "RGBA")

    draw.rounded_rectangle(
        [x - pad, y - pad, x + max_w + pad, y + total_h + pad],
        radius=_s(10, sc),
        fill=theme.bg,
    )

    cy: int = y
    if title:
        draw.text((x, cy), title, fill=theme.text_primary, font=title_font)
        cy += int(title_h) + gap
    if subtitle:
        draw.text((x, cy), subtitle, fill=theme.text_secondary, font=sub_font)

    img.alpha_composite(overlay)
    return int(total_h) + pad * 2


def draw_watermark(
    img: Image.Image,
    text: str,
    theme: OverlayTheme,
) -> None:
    """Draw subtle watermark at bottom-right."""
    sc: float = _scale(img)
    margin: int = _s(theme.base_margin, sc)
    font: ImageFont.FreeTypeFont = get_font(_s(theme.base_watermark_size, sc), "mono")
    w: int
    h: int
    w, h = img.size

    tw: int = int(font.getlength(text))
    pad: int = _s(6, sc)
    x: int = w - margin - tw
    y: int = h - margin

    overlay: Image.Image = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(overlay, "RGBA")

    draw.rounded_rectangle(
        [x - pad, y - pad, x + tw + pad, y + _s(22, sc)],
        radius=_s(5, sc),
        fill=(0, 0, 0, 120),
    )
    draw.text((x, y - _s(1, sc)), text, fill=theme.text_secondary, font=font)

    img.alpha_composite(overlay)


# ======================================================================
# Main compose
# ======================================================================

def compose_image(
    raw_png: bytes | Image.Image,
    *,
    title: str = "",
    subtitle: str = "",
    scalar_bar: ScalarBarConfig | None = None,
    watermark: str = "",
    theme: str | OverlayTheme = "dark",
    title_position: str = "top_left",
) -> Image.Image:
    """Compose overlays and return a PIL RGB Image (no PNG encoding).

    Use this for animation pipelines to avoid intermediate PNG serialization.
    For single images, use :func:`compose` which returns PNG bytes.
    """
    base: Image.Image
    if isinstance(raw_png, Image.Image):
        base = raw_png
    else:
        base = Image.open(io.BytesIO(raw_png))

    img: Image.Image
    if base.mode == "RGBA":
        opaque: Image.Image = Image.new("RGB", base.size, (0, 0, 0))
        opaque.paste(base, mask=base.split()[3])
        img = opaque.convert("RGBA")
    else:
        img = base.convert("RGBA")

    th: OverlayTheme = THEMES.get(theme, THEMES["dark"]) if isinstance(theme, str) else theme

    if scalar_bar is not None:
        draw_scalar_bar(img, scalar_bar, th)

    if title or subtitle:
        draw_title(img, title, th, subtitle=subtitle, position=title_position)

    if watermark:
        draw_watermark(img, watermark, th)

    return img.convert("RGB")


def compose(
    raw_png: bytes | Image.Image,
    *,
    title: str = "",
    subtitle: str = "",
    scalar_bar: ScalarBarConfig | None = None,
    watermark: str = "",
    theme: str | OverlayTheme = "dark",
    title_position: str = "top_left",
) -> bytes:
    """Compose VTK render with Pillow-drawn overlays.

    All dimensions auto-scale with image resolution.
    Reference: 1280x720 → scale=1.0, 1920x1080 → scale=1.5.

    Args:
        raw_png: Raw PNG bytes from VTK or a PIL Image.
        title: Main title text.
        subtitle: Smaller subtitle below title.
        scalar_bar: Scalar bar config. None to skip.
        watermark: Small text at bottom-right.
        theme: "dark", "light", "paper", "transparent", or OverlayTheme.
        title_position: "top_left", "top_right", or "top_center".

    Returns:
        Final composited PNG as bytes.
    """
    img: Image.Image = compose_image(
        raw_png,
        title=title,
        subtitle=subtitle,
        scalar_bar=scalar_bar,
        watermark=watermark,
        theme=theme,
        title_position=title_position,
    )
    buf: io.BytesIO = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
