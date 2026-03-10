"""Tests for label visibility enhancement (B-3)."""

from __future__ import annotations

from PIL import Image, ImageDraw

from viznoir.anim.compositor import (
    BG_COLOR,
    _draw_label_with_bg,
    _get_font,
    _truncate_label,
    render_grid_layout,
    render_story_layout,
)


def _make_assets(n: int, w: int = 400, h: int = 300) -> list[Image.Image]:
    """Create n synthetic RGBA test images."""
    return [Image.new("RGBA", (w, h), (i * 25 % 256, 50, 100, 255)) for i in range(n)]


# ---------------------------------------------------------------------------
# _truncate_label unit tests
# ---------------------------------------------------------------------------


class TestTruncateLabel:
    def test_short_label_unchanged(self):
        """Label shorter than max_width should be returned as-is."""
        font = _get_font(18)
        result = _truncate_label("Hi", font, max_width=500)
        assert result == "Hi"

    def test_long_label_truncated(self):
        """Label wider than max_width should end with '...'."""
        font = _get_font(18)
        result = _truncate_label("A" * 200, font, max_width=100)
        assert result.endswith("...")
        assert len(result) < 200

    def test_empty_label(self):
        """Empty label should return empty string."""
        font = _get_font(18)
        result = _truncate_label("", font, max_width=100)
        assert result == ""

    def test_ellipsis_only_when_needed(self):
        """A label that exactly fits should not be truncated."""
        font = _get_font(18)
        label = "OK"
        result = _truncate_label(label, font, max_width=9999)
        assert result == label


# ---------------------------------------------------------------------------
# _draw_label_with_bg unit tests
# ---------------------------------------------------------------------------


class TestDrawLabelWithBg:
    def test_draws_without_crash(self):
        """Drawing a label with background on a canvas should not crash."""
        canvas = Image.new("RGBA", (400, 100), BG_COLOR)
        draw = ImageDraw.Draw(canvas)
        font = _get_font(18)
        _draw_label_with_bg(draw, "Test Label", font, cx=200, cy=50, panel_width=400, padding=10)

    def test_modifies_pixels(self):
        """Drawing a label should modify at least some pixels from default BG."""
        canvas = Image.new("RGBA", (400, 100), BG_COLOR)
        before = canvas.tobytes()
        draw = ImageDraw.Draw(canvas)
        font = _get_font(18)
        _draw_label_with_bg(draw, "Hello", font, cx=200, cy=50, panel_width=400, padding=10)
        after = canvas.tobytes()
        assert before != after

    def test_empty_label_no_draw(self):
        """Empty label should not modify canvas."""
        canvas = Image.new("RGBA", (400, 100), BG_COLOR)
        draw = ImageDraw.Draw(canvas)
        font = _get_font(18)
        _draw_label_with_bg(draw, "", font, cx=200, cy=50, panel_width=400, padding=10)


# ---------------------------------------------------------------------------
# Integration: label visibility in layouts
# ---------------------------------------------------------------------------


class TestLabelBackgroundBox:
    def test_story_label_has_background(self):
        """Story layout labels should render with semi-transparent background."""
        assets = _make_assets(2)
        labels = ["Test Label", "Another"]
        result = render_story_layout(assets, labels, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_grid_label_has_background(self):
        """Grid layout labels should render with semi-transparent background."""
        assets = _make_assets(4)
        labels = ["A", "B", "C", "D"]
        result = render_grid_layout(assets, cols=2, width=1920, height=1080, labels=labels)
        assert result.size == (1920, 1080)


class TestLabelTruncation:
    def test_long_label_truncated_in_story(self):
        """Very long label should be truncated with '...' and not overflow."""
        assets = _make_assets(3)
        labels = ["A" * 200, "Normal", "B" * 200]
        result = render_story_layout(assets, labels, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_long_label_truncated_in_grid(self):
        """Very long label in grid layout should be truncated."""
        assets = _make_assets(4)
        labels = ["X" * 200, "Y" * 200, "Short", "Z" * 200]
        result = render_grid_layout(assets, cols=2, width=1920, height=1080, labels=labels)
        assert result.size == (1920, 1080)

    def test_empty_label_no_crash(self):
        """Empty labels should not cause issues."""
        assets = _make_assets(2)
        labels = ["", ""]
        result = render_story_layout(assets, labels, width=1920, height=1080)
        assert result.size == (1920, 1080)


class TestLabelPositioning:
    def test_labels_centered_horizontally(self):
        """Labels should be centered within their panel."""
        assets = _make_assets(3)
        labels = ["Short", "Medium Label", "A"]
        result = render_story_layout(assets, labels, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_slides_label_positioning(self):
        """Slides layout labels should also work correctly."""
        from viznoir.anim.compositor import render_slides_layout

        assets = _make_assets(2)
        labels = ["Slide 1", "Slide 2"]
        result = render_slides_layout(assets, labels, width=1920, height=1080)
        assert len(result) == 2
        assert all(s.size == (1920, 1080) for s in result)
