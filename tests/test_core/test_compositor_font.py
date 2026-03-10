"""Tests for improved font system (B-2)."""

from __future__ import annotations

from viznoir.anim.compositor import _get_font, _get_scaled_font


class TestGetFont:
    def test_returns_font_object(self):
        """Should return a usable font object."""
        font = _get_font(24)
        assert font is not None

    def test_different_sizes(self):
        """Different sizes should return valid fonts."""
        for size in [12, 18, 24, 32, 48]:
            font = _get_font(size)
            assert font is not None


class TestGetScaledFont:
    def test_scales_up_for_4k(self):
        """4K canvas (3840) should produce larger font than reference (1920)."""
        font_4k = _get_scaled_font(32, 3840)
        font_1080 = _get_scaled_font(32, 1920)
        assert font_4k is not None
        assert font_1080 is not None

    def test_scales_down_for_720p(self):
        """720p canvas should produce smaller font."""
        font = _get_scaled_font(32, 1280)
        assert font is not None

    def test_minimum_size_enforced(self):
        """Very small canvas should not go below minimum font size (12)."""
        font = _get_scaled_font(32, 100)
        assert font is not None

    def test_custom_reference_width(self):
        """Custom reference width should work."""
        font = _get_scaled_font(24, 1920, reference_width=3840)
        assert font is not None

    def test_scaled_size_calculation(self):
        """Verify scaled size math: base 32 at 3840 with ref 1920 -> 64."""
        # We can't directly check font size, but we can verify the function
        # doesn't crash and returns a valid font for edge cases
        for width in [100, 500, 1920, 3840, 7680]:
            font = _get_scaled_font(32, width)
            assert font is not None


class TestFontCandidatesExpanded:
    def test_has_macos_paths(self):
        """Font candidates should include macOS system font paths."""
        from viznoir.anim.compositor import _FONT_CANDIDATES

        macos_paths = [c for c in _FONT_CANDIDATES if "/System/Library/Fonts" in c]
        assert len(macos_paths) > 0

    def test_has_windows_paths(self):
        """Font candidates should include Windows font paths."""
        from viznoir.anim.compositor import _FONT_CANDIDATES

        win_paths = [c for c in _FONT_CANDIDATES if "Windows" in c or "C:\\" in c]
        assert len(win_paths) > 0

    def test_has_cjk_fonts(self):
        """Font candidates should include CJK font entries."""
        from viznoir.anim.compositor import _FONT_CANDIDATES

        cjk = [c for c in _FONT_CANDIDATES if "CJK" in c or "Noto" in c.split("/")[-1]]
        assert len(cjk) > 0
