"""Tests for anim/transitions.py — scene transitions."""

from __future__ import annotations

from PIL import Image


def _red_image(w=100, h=100):
    return Image.new("RGBA", (w, h), (255, 0, 0, 255))


def _blue_image(w=100, h=100):
    return Image.new("RGBA", (w, h), (0, 0, 255, 255))


class TestFadeIn:
    def test_t0_is_transparent(self):
        from viznoir.anim.transitions import fade_in

        img = _red_image()
        result = fade_in(img, 0.0)
        assert result.getpixel((50, 50))[3] == 0

    def test_t1_is_opaque(self):
        from viznoir.anim.transitions import fade_in

        img = _red_image()
        result = fade_in(img, 1.0)
        assert result.getpixel((50, 50))[3] == 255


class TestFadeOut:
    def test_t0_is_opaque(self):
        from viznoir.anim.transitions import fade_out

        img = _red_image()
        result = fade_out(img, 0.0)
        assert result.getpixel((50, 50))[3] == 255

    def test_t1_is_transparent(self):
        from viznoir.anim.transitions import fade_out

        img = _red_image()
        result = fade_out(img, 1.0)
        assert result.getpixel((50, 50))[3] == 0


class TestDissolve:
    def test_t0_is_source(self):
        from viznoir.anim.transitions import dissolve

        result = dissolve(_red_image(), _blue_image(), 0.0)
        r, g, b, a = result.getpixel((50, 50))
        assert r == 255 and b == 0

    def test_t1_is_target(self):
        from viznoir.anim.transitions import dissolve

        result = dissolve(_red_image(), _blue_image(), 1.0)
        r, g, b, a = result.getpixel((50, 50))
        assert r == 0 and b == 255

    def test_t05_is_blend(self):
        from viznoir.anim.transitions import dissolve

        result = dissolve(_red_image(), _blue_image(), 0.5)
        r, g, b, a = result.getpixel((50, 50))
        assert 100 < r < 200


class TestWipe:
    def test_wipe_left_t0(self):
        from viznoir.anim.transitions import wipe

        result = wipe(_red_image(), _blue_image(), 0.0, direction="left")
        r, g, b, a = result.getpixel((50, 50))
        assert r == 255

    def test_wipe_left_t1(self):
        from viznoir.anim.transitions import wipe

        result = wipe(_red_image(), _blue_image(), 1.0, direction="left")
        r, g, b, a = result.getpixel((50, 50))
        assert b == 255


class TestGetTransition:
    def test_known_transitions(self):
        from viznoir.anim.transitions import get_transition

        for name in ["fade_in", "fade_out", "dissolve", "wipe_left", "wipe_right"]:
            fn = get_transition(name)
            assert callable(fn)

    def test_unknown_raises(self):
        import pytest

        from viznoir.anim.transitions import get_transition

        with pytest.raises(KeyError):
            get_transition("nonexistent")
