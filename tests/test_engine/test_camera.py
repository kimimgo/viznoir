"""Tests for engine/camera.py — preset and custom camera positioning."""

from __future__ import annotations

from math import sqrt

import pytest

from parapilot.engine.camera import (
    CameraConfig,
    custom_camera,
    preset_camera,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unit_bounds() -> tuple[float, float, float, float, float, float]:
    """Unit cube centered at origin: (-0.5..0.5) in each axis."""
    return (-0.5, 0.5, -0.5, 0.5, -0.5, 0.5)


@pytest.fixture
def asym_bounds() -> tuple[float, float, float, float, float, float]:
    """Asymmetric bounds for testing center calculation."""
    return (0.0, 2.0, 0.0, 4.0, 0.0, 6.0)


# ---------------------------------------------------------------------------
# preset_camera
# ---------------------------------------------------------------------------

class TestPresetCamera:
    def test_returns_camera_config(self, unit_bounds):
        result = preset_camera("top", unit_bounds)
        assert isinstance(result, CameraConfig)

    def test_top_preset_looks_down_z(self, unit_bounds):
        cam = preset_camera("top", unit_bounds)
        # Camera should be above center, looking down
        assert cam.position[2] > 0
        assert cam.focal_point == (0.0, 0.0, 0.0)
        assert cam.view_up == (0.0, 1.0, 0.0)

    def test_front_preset_looks_along_y(self, unit_bounds):
        cam = preset_camera("front", unit_bounds)
        # Camera should be in -Y direction from center
        assert cam.position[1] < 0
        assert cam.focal_point == (0.0, 0.0, 0.0)

    def test_right_preset_looks_along_x(self, unit_bounds):
        cam = preset_camera("right", unit_bounds)
        assert cam.position[0] > 0
        assert cam.focal_point == (0.0, 0.0, 0.0)

    def test_isometric_all_positive(self, unit_bounds):
        cam = preset_camera("isometric", unit_bounds)
        assert cam.position[0] > 0
        assert cam.position[1] > 0
        assert cam.position[2] > 0

    def test_focal_point_is_center(self, asym_bounds):
        cam = preset_camera("top", asym_bounds)
        assert cam.focal_point == pytest.approx((1.0, 2.0, 3.0))

    def test_zoom_closer(self, unit_bounds):
        cam_normal = preset_camera("top", unit_bounds, zoom=1.0)
        cam_zoomed = preset_camera("top", unit_bounds, zoom=2.0)
        # Zoomed camera should be closer to center
        dist_normal = abs(cam_normal.position[2] - cam_normal.focal_point[2])
        dist_zoomed = abs(cam_zoomed.position[2] - cam_zoomed.focal_point[2])
        assert dist_zoomed < dist_normal

    def test_orthographic_flag(self, unit_bounds):
        cam = preset_camera("top", unit_bounds, orthographic=True)
        assert cam.parallel_projection is True
        assert cam.parallel_scale is not None
        assert cam.parallel_scale > 0

    def test_perspective_default(self, unit_bounds):
        cam = preset_camera("top", unit_bounds)
        assert cam.parallel_projection is False
        assert cam.parallel_scale is None

    def test_unknown_preset_falls_back_to_isometric(self, unit_bounds):
        cam_unknown = preset_camera("nonexistent", unit_bounds)
        cam_iso = preset_camera("isometric", unit_bounds)
        assert cam_unknown.position == cam_iso.position
        assert cam_unknown.view_up == cam_iso.view_up

    def test_degenerate_bounds_no_crash(self):
        """Zero-size bounds should not cause division by zero."""
        degenerate = (1.0, 1.0, 2.0, 2.0, 3.0, 3.0)
        cam = preset_camera("top", degenerate)
        assert cam.focal_point == pytest.approx((1.0, 2.0, 3.0))

    @pytest.mark.parametrize("preset", [
        "isometric", "top", "bottom", "front", "back", "right", "left",
    ])
    def test_all_presets_produce_valid_config(self, unit_bounds, preset):
        cam = preset_camera(preset, unit_bounds)
        assert isinstance(cam, CameraConfig)
        assert len(cam.position) == 3
        assert len(cam.focal_point) == 3
        assert len(cam.view_up) == 3


# ---------------------------------------------------------------------------
# custom_camera
# ---------------------------------------------------------------------------

class TestCustomCamera:
    def test_explicit_position(self):
        cam = custom_camera(position=(10.0, 20.0, 30.0))
        assert cam.position == (10.0, 20.0, 30.0)

    def test_default_focal_point_origin(self):
        cam = custom_camera(position=(1.0, 0.0, 0.0))
        assert cam.focal_point == (0.0, 0.0, 0.0)

    def test_focal_point_from_bounds(self):
        cam = custom_camera(
            position=(10.0, 0.0, 0.0),
            bounds=(0.0, 2.0, 0.0, 4.0, 0.0, 6.0),
        )
        assert cam.focal_point == pytest.approx((1.0, 2.0, 3.0))

    def test_explicit_focal_point_overrides_bounds(self):
        cam = custom_camera(
            position=(10.0, 0.0, 0.0),
            focal_point=(5.0, 5.0, 5.0),
            bounds=(0.0, 2.0, 0.0, 4.0, 0.0, 6.0),
        )
        assert cam.focal_point == (5.0, 5.0, 5.0)

    def test_default_view_up(self):
        cam = custom_camera(position=(1.0, 0.0, 0.0))
        assert cam.view_up == (0.0, 0.0, 1.0)

    def test_explicit_view_up(self):
        cam = custom_camera(position=(1.0, 0.0, 0.0), view_up=(0.0, 1.0, 0.0))
        assert cam.view_up == (0.0, 1.0, 0.0)

    def test_orthographic_with_bounds(self):
        cam = custom_camera(
            position=(10.0, 0.0, 0.0),
            bounds=(0.0, 2.0, 0.0, 4.0, 0.0, 6.0),
            orthographic=True,
        )
        assert cam.parallel_projection is True
        assert cam.parallel_scale is not None

    def test_orthographic_without_bounds(self):
        cam = custom_camera(
            position=(10.0, 0.0, 0.0),
            orthographic=True,
        )
        assert cam.parallel_projection is True
        assert cam.parallel_scale is None
