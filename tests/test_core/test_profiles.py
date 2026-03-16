# tests/test_core/test_profiles.py
"""Tests for render profile resolution."""

import pytest

from viznoir.core.profiles import PROFILES, RenderProfile, resolve_profile


class TestRenderProfile:
    def test_profile_is_frozen(self):
        p = RenderProfile(800, 600, 6, "test")
        with pytest.raises(AttributeError):
            p.width = 1024


class TestResolveProfile:
    def test_analyze_default(self):
        p = resolve_profile()
        assert p.width == 854
        assert p.height == 480
        assert p.label == "analyze"

    def test_preview(self):
        p = resolve_profile("preview")
        assert p.width == 1280
        assert p.height == 720

    def test_publish(self):
        p = resolve_profile("publish")
        assert p.width == 1920
        assert p.height == 1080
        assert p.png_compress_level == 9

    def test_custom_override_both(self):
        p = resolve_profile("analyze", width=3840, height=2160)
        assert p.width == 3840
        assert p.height == 2160
        assert p.label == "custom"

    def test_one_sided_width_raises(self):
        with pytest.raises(ValueError, match="both width and height"):
            resolve_profile("analyze", width=1920)

    def test_one_sided_height_raises(self):
        with pytest.raises(ValueError, match="both width and height"):
            resolve_profile("analyze", height=1080)

    def test_unknown_purpose_raises(self):
        with pytest.raises(ValueError, match="Unknown purpose"):
            resolve_profile("cinematic")

    def test_bounds_zero_raises(self):
        with pytest.raises(ValueError, match="1-8192"):
            resolve_profile("analyze", width=0, height=480)

    def test_bounds_too_large_raises(self):
        with pytest.raises(ValueError, match="1-8192"):
            resolve_profile("analyze", width=10000, height=480)

    def test_all_profiles_have_valid_dimensions(self):
        for name, p in PROFILES.items():
            assert 1 <= p.width <= 8192, f"{name} width"
            assert 1 <= p.height <= 8192, f"{name} height"
            assert 0 <= p.png_compress_level <= 9, f"{name} compress"
