"""Tests for anim/easing.py — Manim-inspired easing functions."""

from __future__ import annotations

import pytest

from viznoir.anim.easing import EASING_FUNCTIONS, smooth  # noqa: N811


class TestEasingEndpoints:
    @pytest.mark.parametrize("name", list(EASING_FUNCTIONS.keys()))
    def test_f0_equals_0(self, name):
        func = EASING_FUNCTIONS[name]
        assert func(0.0) == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.parametrize(
        "name",
        [n for n in EASING_FUNCTIONS if n != "there_and_back"],
    )
    def test_f1_equals_1(self, name):
        func = EASING_FUNCTIONS[name]
        assert func(1.0) == pytest.approx(1.0, abs=1e-10)


class TestEasingCount:
    def test_at_least_17_functions(self):
        assert len(EASING_FUNCTIONS) >= 17

    def test_all_callable(self):
        for name, func in EASING_FUNCTIONS.items():
            assert callable(func), f"{name} is not callable"


class TestEasingBehavior:
    def test_smooth_is_slow_at_endpoints(self):
        assert smooth(0.01) < 0.01
        assert smooth(0.99) > 0.99

    def test_ease_in_sine_slow_start(self):
        from viznoir.anim.easing import ease_in_sine
        assert ease_in_sine(0.1) < 0.1

    def test_ease_out_sine_slow_end(self):
        from viznoir.anim.easing import ease_out_sine
        assert ease_out_sine(0.9) > 0.9

    def test_there_and_back_returns_to_zero(self):
        from viznoir.anim.easing import there_and_back
        assert there_and_back(0.0) == pytest.approx(0.0)
        assert there_and_back(0.5) == pytest.approx(1.0, abs=0.05)
        assert there_and_back(1.0) == pytest.approx(0.0, abs=1e-10)

    def test_rush_into_accelerating(self):
        from viznoir.anim.easing import rush_into
        assert rush_into(0.5) < 0.5

    def test_rush_from_decelerating(self):
        from viznoir.anim.easing import rush_from
        assert rush_from(0.5) > 0.5

    def test_linear_identity(self):
        from viznoir.anim.easing import linear
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert linear(t) == pytest.approx(t)

    def test_double_smooth_stronger(self):
        from viznoir.anim.easing import double_smooth
        assert double_smooth(0.01) < smooth(0.01)


class TestBackwardsCompatibility:
    def test_camera_path_easing_still_works(self):
        from viznoir.engine.camera_path import EASING_FUNCTIONS as cam_easings  # noqa: N811
        assert "linear" in cam_easings
        assert "ease_in" in cam_easings
        assert "ease_out" in cam_easings
        assert "ease_in_out" in cam_easings
        assert "smooth" in cam_easings
