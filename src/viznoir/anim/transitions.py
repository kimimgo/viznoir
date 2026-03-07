"""Scene transitions — fade, dissolve, wipe effects."""

from __future__ import annotations

from collections.abc import Callable

from PIL import Image


def fade_in(img: Image.Image, t: float) -> Image.Image:
    """Fade from transparent to opaque. Uses Image.blend for C-level speed."""
    t = max(0.0, min(1.0, t))
    transparent = Image.new("RGBA", img.size, (0, 0, 0, 0))
    return Image.blend(transparent, img.convert("RGBA"), t)


def fade_out(img: Image.Image, t: float) -> Image.Image:
    """Fade from opaque to transparent."""
    return fade_in(img, 1.0 - t)


def dissolve(src: Image.Image, dst: Image.Image, t: float) -> Image.Image:
    """Cross-dissolve between two images."""
    t = max(0.0, min(1.0, t))
    return Image.blend(src.convert("RGBA"), dst.convert("RGBA"), t)


def wipe(
    src: Image.Image,
    dst: Image.Image,
    t: float,
    direction: str = "left",
) -> Image.Image:
    """Wipe transition between two images."""
    t = max(0.0, min(1.0, t))
    w, h = src.size
    result = src.copy().convert("RGBA")
    dst_rgba = dst.convert("RGBA")

    if direction == "left":
        cut = int(w * t)
        if cut > 0:
            result.paste(dst_rgba.crop((0, 0, cut, h)), (0, 0))
    elif direction == "right":
        cut = int(w * (1 - t))
        if cut < w:
            result.paste(dst_rgba.crop((cut, 0, w, h)), (cut, 0))
    elif direction == "down":
        cut = int(h * t)
        if cut > 0:
            result.paste(dst_rgba.crop((0, 0, w, cut)), (0, 0))
    elif direction == "up":
        cut = int(h * (1 - t))
        if cut < h:
            result.paste(dst_rgba.crop((0, cut, w, h)), (0, cut))

    return result


_TRANSITIONS: dict[str, Callable] = {
    "fade_in": fade_in,
    "fade_out": fade_out,
    "dissolve": dissolve,
    "wipe_left": lambda src, dst, t: wipe(src, dst, t, "left"),
    "wipe_right": lambda src, dst, t: wipe(src, dst, t, "right"),
    "wipe_down": lambda src, dst, t: wipe(src, dst, t, "down"),
    "wipe_up": lambda src, dst, t: wipe(src, dst, t, "up"),
}


def get_transition(name: str) -> Callable:
    """Get a transition function by name."""
    if name not in _TRANSITIONS:
        raise KeyError(f"Unknown transition: {name}. Available: {list(_TRANSITIONS.keys())}")
    return _TRANSITIONS[name]
