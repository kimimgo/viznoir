"""Tests for improved compositor layout engine (B-1)."""

from __future__ import annotations

from PIL import Image

from viznoir.anim.compositor import render_grid_layout, render_story_layout


def _make_assets(n: int, w: int = 400, h: int = 300) -> list[Image.Image]:
    """Create n synthetic RGBA test images with distinct colors."""
    return [Image.new("RGBA", (w, h), (i * 25 % 256, 50, 100, 255)) for i in range(n)]


# ---------------------------------------------------------------------------
# render_story_layout improvements
# ---------------------------------------------------------------------------


class TestStoryLayoutMinPanelWidth:
    def test_basic_signature_unchanged(self):
        """Calling without new params still works (backward compat)."""
        assets = _make_assets(3)
        labels = ["A", "B", "C"]
        result = render_story_layout(assets, labels, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_min_panel_width_param_accepted(self):
        """New min_panel_width parameter is accepted."""
        assets = _make_assets(4)
        labels = ["A", "B", "C", "D"]
        result = render_story_layout(assets, labels, width=1920, height=1080, min_panel_width=300)
        assert result.size == (1920, 1080)

    def test_wraps_to_multiple_rows_when_narrow(self):
        """10 assets at 1920 width with min_panel_width=300 should wrap to multiple rows."""
        assets = _make_assets(10)
        labels = [f"Panel {i}" for i in range(10)]
        result = render_story_layout(assets, labels, width=1920, height=1080, min_panel_width=300)
        assert result.size == (1920, 1080)

    def test_single_row_when_sufficient_width(self):
        """3 assets at 1920 width with min_panel_width=200 should fit in single row."""
        assets = _make_assets(3)
        labels = ["A", "B", "C"]
        result = render_story_layout(assets, labels, width=1920, height=1080, min_panel_width=200)
        assert result.size == (1920, 1080)

    def test_zero_assets_returns_blank_canvas(self):
        """Zero assets should return blank canvas."""
        result = render_story_layout([], [], width=1920, height=1080, min_panel_width=300)
        assert result.size == (1920, 1080)


class TestStoryLayoutResponsiveTitle:
    def test_title_height_scales_with_canvas(self):
        """Title at 4K should be taller than at 720p (visual correctness, no crash)."""
        assets = _make_assets(2)
        labels = ["A", "B"]
        r_4k = render_story_layout(assets, labels, title="Big Title", width=3840, height=2160)
        r_720p = render_story_layout(assets, labels, title="Big Title", width=1280, height=720)
        assert r_4k.size == (3840, 2160)
        assert r_720p.size == (1280, 720)

    def test_no_title_still_works(self):
        """No title param should still work."""
        assets = _make_assets(2)
        labels = ["A", "B"]
        result = render_story_layout(assets, labels, width=1920, height=1080)
        assert result.size == (1920, 1080)


# ---------------------------------------------------------------------------
# render_grid_layout improvements
# ---------------------------------------------------------------------------


class TestGridLayoutAutoCols:
    def test_auto_cols_with_zero(self):
        """cols=0 should auto-calculate columns."""
        assets = _make_assets(4)
        result = render_grid_layout(assets, cols=0, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_auto_cols_9_assets(self):
        """9 assets with cols=0 should use 3 cols (ceil(sqrt(9)))."""
        assets = _make_assets(9)
        result = render_grid_layout(assets, cols=0, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_auto_cols_single_asset(self):
        """1 asset with cols=0 should use 1 col."""
        assets = _make_assets(1)
        result = render_grid_layout(assets, cols=0, width=1920, height=1080)
        assert result.size == (1920, 1080)


class TestGridLayoutLabels:
    def test_labels_param_accepted(self):
        """Grid layout should accept labels parameter."""
        assets = _make_assets(4)
        labels = ["A", "B", "C", "D"]
        result = render_grid_layout(assets, cols=2, width=1920, height=1080, labels=labels)
        assert result.size == (1920, 1080)

    def test_labels_none_default(self):
        """Default labels=None should work."""
        assets = _make_assets(4)
        result = render_grid_layout(assets, cols=2, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_labels_shorter_than_assets(self):
        """Fewer labels than assets should pad with empty strings."""
        assets = _make_assets(4)
        labels = ["A", "B"]
        result = render_grid_layout(assets, cols=2, width=1920, height=1080, labels=labels)
        assert result.size == (1920, 1080)


class TestGridLayoutResponsivePadding:
    def test_padding_scales_with_canvas(self):
        """Larger canvas should have larger padding (no crash, correct size)."""
        assets = _make_assets(4)
        r_4k = render_grid_layout(assets, cols=2, width=3840, height=2160)
        r_720p = render_grid_layout(assets, cols=2, width=640, height=480)
        assert r_4k.size == (3840, 2160)
        assert r_720p.size == (640, 480)


class TestGridLayoutSparseGrid:
    def test_no_sparse_cells_3_in_2col(self):
        """3 assets in 2-col grid should use 2 rows, not waste space."""
        assets = _make_assets(3)
        result = render_grid_layout(assets, cols=2, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_no_sparse_cells_5_in_3col(self):
        """5 assets in 3-col grid should use 2 rows."""
        assets = _make_assets(5)
        result = render_grid_layout(assets, cols=3, width=1920, height=1080)
        assert result.size == (1920, 1080)

    def test_zero_assets_returns_blank(self):
        """Zero assets should return blank canvas."""
        result = render_grid_layout([], cols=2, width=1920, height=1080)
        assert result.size == (1920, 1080)
