"""Tests for anim/compositor.py — frame compositor with layout rendering + video export."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image


def _make_asset(w: int = 200, h: int = 150, color: tuple = (255, 0, 0, 255)) -> Image.Image:
    """Create a test RGBA asset image."""
    return Image.new("RGBA", (w, h), color)


# ---------------------------------------------------------------------------
# render_story_layout
# ---------------------------------------------------------------------------


class TestRenderStoryLayout:
    def test_returns_image(self):
        from viznoir.anim.compositor import render_story_layout

        assets = [_make_asset(), _make_asset(color=(0, 255, 0, 255))]
        labels = ["Panel A", "Panel B"]
        result = render_story_layout(
            assets, labels, title="Test Story", width=800, height=600,
        )
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)
        assert result.mode == "RGBA"

    def test_single_asset(self):
        from viznoir.anim.compositor import render_story_layout

        assets = [_make_asset()]
        labels = ["Only panel"]
        result = render_story_layout(
            assets, labels, title="Single", width=800, height=600,
        )
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)

    def test_no_title(self):
        from viznoir.anim.compositor import render_story_layout

        assets = [_make_asset(), _make_asset()]
        labels = ["A", "B"]
        result = render_story_layout(assets, labels, title=None, width=800, height=600)
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)

    def test_empty_labels_padded(self):
        """Labels shorter than assets should be padded with empty strings."""
        from viznoir.anim.compositor import render_story_layout

        assets = [_make_asset(), _make_asset(), _make_asset()]
        labels = ["Only first"]
        result = render_story_layout(
            assets, labels, title="Padded", width=800, height=600,
        )
        assert isinstance(result, Image.Image)

    def test_bg_color_applied(self):
        """Background color should be the dark theme BG_COLOR."""
        from viznoir.anim.compositor import BG_COLOR, render_story_layout

        assets = [_make_asset(50, 50)]
        result = render_story_layout(assets, [], title=None, width=200, height=200)
        # Corner pixel should be BG_COLOR
        px = result.getpixel((0, 0))
        assert px == BG_COLOR


# ---------------------------------------------------------------------------
# render_grid_layout
# ---------------------------------------------------------------------------


class TestRenderGridLayout:
    def test_returns_correct_size(self):
        from viznoir.anim.compositor import render_grid_layout

        assets = [_make_asset() for _ in range(4)]
        result = render_grid_layout(assets, cols=2, width=800, height=600)
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)

    def test_single_column(self):
        from viznoir.anim.compositor import render_grid_layout

        assets = [_make_asset(), _make_asset()]
        result = render_grid_layout(assets, cols=1, width=400, height=600)
        assert isinstance(result, Image.Image)
        assert result.size == (400, 600)

    def test_single_asset(self):
        from viznoir.anim.compositor import render_grid_layout

        assets = [_make_asset()]
        result = render_grid_layout(assets, cols=2, width=800, height=600)
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)

    def test_odd_number_of_assets(self):
        """3 assets in 2 cols should work (last cell empty)."""
        from viznoir.anim.compositor import render_grid_layout

        assets = [_make_asset() for _ in range(3)]
        result = render_grid_layout(assets, cols=2, width=800, height=600)
        assert isinstance(result, Image.Image)


# ---------------------------------------------------------------------------
# render_slides_layout
# ---------------------------------------------------------------------------


class TestRenderSlidesLayout:
    def test_returns_list_of_images(self):
        from viznoir.anim.compositor import render_slides_layout

        assets = [_make_asset(), _make_asset()]
        labels = ["Slide 1", "Slide 2"]
        result = render_slides_layout(
            assets, labels, width=800, height=600,
        )
        assert isinstance(result, list)
        assert len(result) == 2
        for slide in result:
            assert isinstance(slide, Image.Image)
            assert slide.size == (800, 600)

    def test_single_slide(self):
        from viznoir.anim.compositor import render_slides_layout

        assets = [_make_asset()]
        labels = ["Only"]
        result = render_slides_layout(assets, labels, width=800, height=600)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# export_video
# ---------------------------------------------------------------------------


class TestExportVideo:
    def test_export_creates_file(self, tmp_path):
        from viznoir.anim.compositor import export_video

        frames = [_make_asset(w=320, h=240) for _ in range(5)]
        output_path = str(tmp_path / "test_output.mp4")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = b""

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.__enter__ = MagicMock(return_value=mock_proc)
            mock_popen.return_value.__exit__ = MagicMock(return_value=False)
            mock_proc.stdin = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))

            export_video(frames, output_path, fps=30, preset="medium")

            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            # Should invoke ffmpeg
            assert cmd[0] == "ffmpeg"
            # Should include output path
            assert output_path in cmd

    def test_export_raises_on_ffmpeg_failure(self, tmp_path):
        from viznoir.anim.compositor import export_video

        frames = [_make_asset(w=320, h=240)]
        output_path = str(tmp_path / "fail.mp4")

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = b""
        mock_proc.stdin = MagicMock()
        mock_proc.communicate = MagicMock(return_value=(b"", b"ffmpeg error details"))

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.__enter__ = MagicMock(return_value=mock_proc)
            mock_popen.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(RuntimeError, match="ffmpeg"):
                export_video(frames, output_path, fps=30)

    def test_export_empty_frames_raises(self, tmp_path):
        from viznoir.anim.compositor import export_video

        output_path = str(tmp_path / "empty.mp4")
        with pytest.raises(ValueError, match="[Nn]o frames"):
            export_video([], output_path, fps=30)


# ---------------------------------------------------------------------------
# _get_font
# ---------------------------------------------------------------------------


class TestGetFont:
    def test_returns_truetype_or_default(self):
        from viznoir.anim.compositor import _get_font

        font = _get_font(24)
        # Should return some font object (ImageFont.FreeTypeFont or ImageFont.ImageFont)
        assert font is not None

    def test_different_sizes(self):
        from viznoir.anim.compositor import _get_font

        font_small = _get_font(12)
        font_large = _get_font(48)
        assert font_small is not None
        assert font_large is not None


# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------


class TestColorConstants:
    def test_bg_color(self):
        from viznoir.anim.compositor import BG_COLOR
        assert BG_COLOR == (0x1C, 0x1C, 0x2E, 255)

    def test_text_white(self):
        from viznoir.anim.compositor import TEXT_WHITE
        assert TEXT_WHITE == (255, 255, 255, 255)

    def test_text_dim(self):
        from viznoir.anim.compositor import TEXT_DIM
        assert TEXT_DIM == (0x88, 0x92, 0xB0, 255)

    def test_accent_teal(self):
        from viznoir.anim.compositor import ACCENT_TEAL
        assert ACCENT_TEAL == (0x00, 0xD4, 0xAA, 255)
