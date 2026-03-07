"""Tests for engine/camera_path.py — Bezier/Catmull-Rom camera animation paths."""

from __future__ import annotations

import math

import numpy as np
import pytest

from viznoir.engine.camera_path import (
    CameraKeyframe,
    CameraPath,
    _catmull_rom,
    _ease_in,
    _ease_in_out,
    _ease_linear,
    _ease_out,
    _lerp_tuple,
    flythrough_path,
    interpolate_path,
    orbit_path,
)


class TestEasing:
    def test_linear_endpoints(self):
        assert _ease_linear(0.0) == 0.0
        assert _ease_linear(1.0) == 1.0

    def test_ease_in_endpoints(self):
        assert _ease_in(0.0) == 0.0
        assert _ease_in(1.0) == 1.0

    def test_ease_out_endpoints(self):
        assert _ease_out(0.0) == 0.0
        assert _ease_out(1.0) == 1.0

    def test_ease_in_out_endpoints(self):
        assert _ease_in_out(0.0) == 0.0
        assert _ease_in_out(1.0) == pytest.approx(1.0)

    def test_ease_in_slow_start(self):
        assert _ease_in(0.1) < 0.1

    def test_ease_out_slow_end(self):
        assert _ease_out(0.9) > 0.9


class TestLerp:
    def test_endpoints(self):
        a = (1.0, 2.0, 3.0)
        b = (4.0, 5.0, 6.0)
        assert _lerp_tuple(a, b, 0.0) == a
        assert _lerp_tuple(a, b, 1.0) == b

    def test_midpoint(self):
        a = (0.0, 0.0, 0.0)
        b = (2.0, 4.0, 6.0)
        result = _lerp_tuple(a, b, 0.5)
        assert result == pytest.approx((1.0, 2.0, 3.0))


class TestCatmullRom:
    def test_t0_returns_p1(self):
        p0 = np.array([0.0, 0.0, 0.0])
        p1 = np.array([1.0, 0.0, 0.0])
        p2 = np.array([2.0, 0.0, 0.0])
        p3 = np.array([3.0, 0.0, 0.0])
        result = _catmull_rom(p0, p1, p2, p3, 0.0)
        np.testing.assert_allclose(result, p1)

    def test_t1_returns_p2(self):
        p0 = np.array([0.0, 0.0, 0.0])
        p1 = np.array([1.0, 0.0, 0.0])
        p2 = np.array([2.0, 0.0, 0.0])
        p3 = np.array([3.0, 0.0, 0.0])
        result = _catmull_rom(p0, p1, p2, p3, 1.0)
        np.testing.assert_allclose(result, p2)


class TestCameraKeyframe:
    def test_creation(self):
        kf = CameraKeyframe(
            position=(1.0, 2.0, 3.0),
            focal_point=(0.0, 0.0, 0.0),
        )
        assert kf.position == (1.0, 2.0, 3.0)
        assert kf.view_up == (0.0, 0.0, 1.0)
        assert kf.t == 0.0

    def test_frozen(self):
        kf = CameraKeyframe(position=(0, 0, 0), focal_point=(0, 0, 0))
        with pytest.raises(AttributeError):
            kf.t = 0.5  # type: ignore[misc]


class TestInterpolatePath:
    def test_single_keyframe(self):
        kf = CameraKeyframe(position=(1, 2, 3), focal_point=(0, 0, 0))
        path = CameraPath(keyframes=(kf,))
        result = interpolate_path(path, 5)
        assert len(result) == 5
        for r in result:
            assert r.position == (1, 2, 3)

    def test_two_keyframes(self):
        kf1 = CameraKeyframe(position=(0, 0, 0), focal_point=(0, 0, 0), t=0.0)
        kf2 = CameraKeyframe(position=(10, 0, 0), focal_point=(0, 0, 0), t=1.0)
        path = CameraPath(keyframes=(kf1, kf2), easing="linear")
        result = interpolate_path(path, 11)
        assert len(result) == 11
        # First frame at start
        assert result[0].position[0] == pytest.approx(0.0, abs=0.1)
        # Last frame at end
        assert result[-1].position[0] == pytest.approx(10.0, abs=0.1)
        # Midpoint roughly in the middle
        assert result[5].position[0] == pytest.approx(5.0, abs=1.0)

    def test_easing_affects_timing(self):
        kf1 = CameraKeyframe(position=(0, 0, 0), focal_point=(0, 0, 0), t=0.0)
        kf2 = CameraKeyframe(position=(10, 0, 0), focal_point=(0, 0, 0), t=1.0)

        linear = CameraPath(keyframes=(kf1, kf2), easing="linear")
        eased = CameraPath(keyframes=(kf1, kf2), easing="ease_in_out")

        r_lin = interpolate_path(linear, 21)
        r_ease = interpolate_path(eased, 21)

        # At t=0.25, ease_in_out should be slower than linear
        assert r_ease[5].position[0] < r_lin[5].position[0]

    def test_output_count_matches(self):
        kf1 = CameraKeyframe(position=(0, 0, 0), focal_point=(0, 0, 0))
        kf2 = CameraKeyframe(position=(5, 5, 5), focal_point=(0, 0, 0))
        kf3 = CameraKeyframe(position=(10, 0, 0), focal_point=(0, 0, 0))
        path = CameraPath(keyframes=(kf1, kf2, kf3))
        result = interpolate_path(path, 30)
        assert len(result) == 30


class TestOrbitPath:
    def test_default_orbit(self):
        path = orbit_path(
            center=(0, 0, 0),
            radius=10.0,
        )
        assert len(path.keyframes) == 8
        for kf in path.keyframes:
            assert kf.focal_point == (0, 0, 0)
            dist = math.sqrt(sum(x**2 for x in kf.position))
            assert dist == pytest.approx(10.0, rel=0.01)

    def test_full_orbit_closes(self):
        path = orbit_path(center=(0, 0, 0), radius=5.0, num_keyframes=9)
        # Last keyframe should be close to first (360 degree orbit)
        first = path.keyframes[0].position
        last = path.keyframes[-1].position
        assert first[0] == pytest.approx(last[0], abs=0.01)
        assert first[1] == pytest.approx(last[1], abs=0.01)

    def test_custom_elevation(self):
        path = orbit_path(center=(0, 0, 0), radius=10.0, elevation_deg=60.0)
        for kf in path.keyframes:
            assert kf.position[2] > 5.0  # high elevation = high Z


class TestFlythroughPath:
    def test_start_end(self):
        path = flythrough_path(
            start=(0, 0, 10),
            end=(10, 0, 10),
            focal_point=(5, 0, 0),
        )
        assert path.keyframes[0].position == (0, 0, 10)
        assert path.keyframes[-1].position == (10, 0, 10)

    def test_all_look_at_focal(self):
        path = flythrough_path(
            start=(0, 0, 10),
            end=(10, 0, 10),
            focal_point=(5, 0, 0),
        )
        for kf in path.keyframes:
            assert kf.focal_point == (5, 0, 0)
