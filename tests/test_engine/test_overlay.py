"""Tests for Pillow overlay compositing."""

from __future__ import annotations

import io
from unittest.mock import patch

from PIL import Image

from parapilot.engine.overlay import (
    THEMES,
    OverlayTheme,
    ScalarBarConfig,
    _find_font,
    _sample_colormap,
    compose,
    draw_scalar_bar,
    draw_title,
    draw_watermark,
    get_font,
)


def _blank_png(w: int = 400, h: int = 300, color: tuple = (50, 50, 60)) -> bytes:
    """Create a blank PNG in memory."""
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _blank_image(w: int = 400, h: int = 300) -> Image.Image:
    return Image.new("RGBA", (w, h), (50, 50, 60, 255))


# ── Font management ───────────────────────────────────────────────────

class TestFontManagement:
    def test_get_font_sans(self):
        f = get_font(16, "sans")
        assert f is not None
        assert f.size == 16

    def test_get_font_mono(self):
        f = get_font(14, "mono")
        assert f is not None

    def test_get_font_bold(self):
        f = get_font(18, "sans", bold=True)
        assert f is not None

    def test_font_caching(self):
        f1 = get_font(20, "sans")
        f2 = get_font(20, "sans")
        assert f1 is f2  # same object from cache

    def test_different_sizes_not_cached_together(self):
        f1 = get_font(12, "sans")
        f2 = get_font(14, "sans")
        assert f1 is not f2

    def test_find_font_no_ttf_returns_none(self):
        """_find_font returns None when no font files exist."""
        with patch("parapilot.engine.overlay._FONT_SEARCH_PATHS", ["/nonexistent/a.ttf"]):
            result = _find_font("sans", bold=False)
        assert result is None

    def test_find_font_fallback_to_any_existing(self, tmp_path):
        """_find_font falls back to any existing TTF when preferred names don't match."""
        # Create a font file that exists but doesn't match preferred name patterns
        fake_font = tmp_path / "UnknownFont.ttf"
        fake_font.write_bytes(b"fake")
        with patch("parapilot.engine.overlay._FONT_SEARCH_PATHS", [str(fake_font)]):
            result = _find_font("sans", bold=False)
        assert result == str(fake_font)

    def test_get_font_load_default_fallback(self):
        """get_font falls back to load_default when no TTF found."""
        import parapilot.engine.overlay as overlay_mod
        # Clear cache and mock _find_font to return None
        old_cache = overlay_mod._font_cache.copy()
        overlay_mod._font_cache.clear()
        try:
            with patch.object(overlay_mod, "_find_font", return_value=None):
                f = overlay_mod.get_font(16, "sans")
            assert f is not None
        finally:
            overlay_mod._font_cache.clear()
            overlay_mod._font_cache.update(old_cache)


# ── Themes ────────────────────────────────────────────────────────────

class TestThemes:
    def test_all_themes_present(self):
        assert set(THEMES.keys()) == {"dark", "light", "paper", "transparent"}

    def test_theme_has_required_fields(self):
        for name, th in THEMES.items():
            assert len(th.bg) == 4, f"{name}.bg must be RGBA"
            assert len(th.text_primary) == 3
            assert len(th.text_secondary) == 3
            assert th.base_margin > 0
            assert th.base_bar_width > 0
            assert 0 < th.bar_height_ratio <= 1.0

    def test_dark_theme_values(self):
        d = THEMES["dark"]
        assert d.bg[3] > 0  # not fully transparent
        assert d.text_primary[0] > 200  # bright text on dark


# ── ScalarBarConfig ───────────────────────────────────────────────────

class TestScalarBarConfig:
    def test_defaults(self):
        c = ScalarBarConfig()
        assert c.colormap == "cool to warm"
        assert c.n_labels == 5
        assert c.position == "right"

    def test_custom(self):
        c = ScalarBarConfig(colormap="viridis", range=(0, 100), title="Speed", n_labels=10)
        assert c.title == "Speed"
        assert c.range == (0, 100)


# ── draw_scalar_bar ───────────────────────────────────────────────────

class TestDrawScalarBar:
    def test_returns_width(self):
        img = _blank_image()
        w = draw_scalar_bar(img, ScalarBarConfig(), THEMES["dark"])
        assert w > 0

    def test_right_position(self):
        img = _blank_image(800, 600)
        draw_scalar_bar(img, ScalarBarConfig(position="right"), THEMES["dark"])
        # The panel is inside the right margin area — sample center of bar
        # bar is at roughly x=730, y=38..398 for 800x600 with margin=28
        # Check that some pixels in the right half changed
        changed = False
        for x in range(650, 770, 10):
            px = img.getpixel((x, 200))
            if px != (50, 50, 60, 255):
                changed = True
                break
        assert changed, "Scalar bar should modify pixels in the right region"

    def test_left_position(self):
        img = _blank_image(800, 600)
        draw_scalar_bar(img, ScalarBarConfig(position="left"), THEMES["dark"])
        px = img.getpixel((40, 300))
        assert px != (50, 50, 60, 255)

    def test_colormap_gradient_rendered(self):
        """Gradient should produce different colors at top vs bottom."""
        img = _blank_image(600, 600)
        th = THEMES["dark"]
        draw_scalar_bar(img, ScalarBarConfig(colormap="viridis"), th)
        # Scan the right side for pixels that differ from base color
        unique_colors = set()
        for y in range(50, 400, 20):
            for x in range(450, 580, 5):
                px = img.getpixel((x, y))
                if px != (50, 50, 60, 255):
                    unique_colors.add(px)
        # Gradient should produce at least several distinct colors
        assert len(unique_colors) >= 3, f"Expected gradient colors, got {len(unique_colors)}"


# ── draw_title ────────────────────────────────────────────────────────

class TestDrawTitle:
    def test_returns_height(self):
        img = _blank_image()
        h = draw_title(img, "Test Title", THEMES["dark"])
        assert h > 0

    def test_with_subtitle(self):
        img = _blank_image()
        h = draw_title(img, "Title", THEMES["dark"], subtitle="Sub")
        assert h > 10  # auto-scaled: smaller on 400x300

    def test_top_left_position(self):
        img = _blank_image(800, 600)
        draw_title(img, "Hello", THEMES["dark"], position="top_left")
        # Top-left area should have overlay
        px = img.getpixel((40, 30))
        assert px != (50, 50, 60, 255)

    def test_top_right_position(self):
        img = _blank_image(800, 600)
        h = draw_title(img, "Right", THEMES["dark"], position="top_right")
        assert h > 0

    def test_top_center_position(self):
        img = _blank_image(800, 600)
        h = draw_title(img, "Center", THEMES["dark"], position="top_center")
        assert h > 0


# ── draw_watermark ────────────────────────────────────────────────────

class TestDrawWatermark:
    def test_watermark_drawn(self):
        img = _blank_image(800, 600)
        draw_watermark(img, "test watermark", THEMES["dark"])
        # Scan bottom-right area for modified pixels
        changed = False
        for x in range(600, 780, 5):
            for y in range(565, 595, 3):
                px = img.getpixel((x, y))
                if px != (50, 50, 60, 255):
                    changed = True
                    break
            if changed:
                break
        assert changed, "Watermark should modify pixels in bottom-right"


# ── compose (integration) ────────────────────────────────────────────

class TestCompose:
    def test_returns_bytes(self):
        raw = _blank_png()
        result = compose(raw, title="Test")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_png(self):
        raw = _blank_png()
        result = compose(raw, title="Test", theme="dark")
        img = Image.open(io.BytesIO(result))
        assert img.mode == "RGB"  # final output is RGB (no alpha)
        assert img.size == (400, 300)

    def test_all_overlays(self):
        raw = _blank_png(800, 600)
        result = compose(
            raw,
            title="Full Test",
            subtitle="with all overlays",
            scalar_bar=ScalarBarConfig(
                colormap="coolwarm",
                range=(-1.0, 1.0),
                title="Value",
                n_labels=5,
            ),
            watermark="parapilot",
            theme="dark",
        )
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 600)

    def test_pil_image_input(self):
        """compose() should accept PIL Image directly."""
        img = Image.new("RGB", (400, 300), (100, 100, 100))
        result = compose(img, title="From PIL")
        assert isinstance(result, bytes)

    def test_rgba_input_no_tinting(self):
        """RGBA input should be flattened to opaque — no alpha tinting."""
        img = Image.new("RGBA", (400, 300), (100, 100, 100, 128))
        result = compose(img, title="RGBA Test")
        out = Image.open(io.BytesIO(result))
        # Center pixel should not be pure black (alpha tinting) or pure (100,100,100)
        px = out.getpixel((200, 150))
        assert px[0] > 0  # not black

    def test_theme_string(self):
        raw = _blank_png()
        for theme_name in ("dark", "light", "paper", "transparent"):
            result = compose(raw, title=theme_name, theme=theme_name)
            assert len(result) > 0

    def test_unknown_colormap_fallback(self):
        """Unknown colormap falls back to 'cool to warm' or inline default."""
        colors = _sample_colormap("totally_nonexistent_map_xyz", n=5)
        assert len(colors) == 5
        assert all(len(c) == 3 for c in colors)

    def test_sample_colormap_else_branch(self):
        """Colormap with control points not reaching t=1.0 hits the else branch."""
        import parapilot.engine.colormaps as cm_mod
        # Control points stop at t=0.3, so for t>0.3 the for loop's else fires
        mock_pts = [(0.0, 0.0, 0.0, 0.0), (0.3, 1.0, 0.0, 0.0)]
        cm_mod.COLORMAP_REGISTRY["_test_short"] = mock_pts
        try:
            colors = _sample_colormap("_test_short", n=10)
            assert len(colors) == 10
        finally:
            del cm_mod.COLORMAP_REGISTRY["_test_short"]

    def test_custom_theme(self):
        raw = _blank_png()
        custom = OverlayTheme(
            name="custom",
            bg=(0, 100, 0, 200),
            text_primary=(255, 255, 0),
            text_secondary=(200, 200, 0),
            text_muted=(150, 150, 0),
            bar_outline=(0, 200, 0, 200),
        )
        result = compose(raw, title="Custom Theme", theme=custom)
        assert len(result) > 0
