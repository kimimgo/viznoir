# src/viznoir/core/profiles.py
"""Render profiles — resolution + encoding presets for MCP image tools."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RenderProfile", "PROFILES", "resolve_profile"]


@dataclass(frozen=True)
class RenderProfile:
    """Resolution and encoding settings for a single render call."""

    width: int
    height: int
    png_compress_level: int  # 0-9 (0=fastest/largest, 9=slowest/smallest)
    label: str


PROFILES: dict[str, RenderProfile] = {
    "analyze": RenderProfile(854, 480, 6, "analyze"),
    "preview": RenderProfile(1280, 720, 6, "preview"),
    "publish": RenderProfile(1920, 1080, 9, "publish"),
}


def resolve_profile(
    purpose: str = "analyze",
    width: int | None = None,
    height: int | None = None,
) -> RenderProfile:
    """Resolve a RenderProfile from purpose preset with optional overrides.

    Args:
        purpose: Preset name — "analyze" (480p), "preview" (720p), "publish" (1080p).
        width: Override width (must provide both or neither).
        height: Override height (must provide both or neither).

    Returns:
        Resolved RenderProfile.

    Raises:
        ValueError: One-sided override, out-of-bounds, or unknown purpose.
    """
    if (width is None) != (height is None):
        raise ValueError(f"Specify both width and height, or neither. Got width={width}, height={height}")
    if width is not None and height is not None:
        if not (1 <= width <= 8192 and 1 <= height <= 8192):
            raise ValueError(f"width and height must be 1-8192. Got {width}x{height}")
        base = PROFILES.get(purpose, PROFILES["analyze"])
        return RenderProfile(width, height, base.png_compress_level, "custom")
    profile = PROFILES.get(purpose)
    if profile is None:
        raise ValueError(f"Unknown purpose '{purpose}'. Available: {list(PROFILES)}")
    return profile
