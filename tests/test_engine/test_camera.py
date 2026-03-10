"""Tests for engine/camera.py — preset and custom camera positioning."""

from __future__ import annotations

import pytest

from viznoir.engine.camera import (
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

    @pytest.mark.parametrize(
        "preset",
        [
            "isometric",
            "top",
            "bottom",
            "front",
            "back",
            "right",
            "left",
        ],
    )
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


# ---------------------------------------------------------------------------
# preset_camera edge cases (coverage: line 74)
# ---------------------------------------------------------------------------


class TestPresetCameraZeroDirection:
    """Test that a zero-magnitude direction vector is handled safely."""

    def test_zero_direction_no_crash(self, monkeypatch):
        """If _PRESETS returned (0,0,0) direction, mag fallback to 1.0."""
        from viznoir.engine import camera as cam_mod

        original = cam_mod._PRESETS.copy()
        cam_mod._PRESETS["zero"] = ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        try:
            result = preset_camera("zero", (-1, 1, -1, 1, -1, 1))
            # With zero direction, position == center (offset is 0)
            assert result.focal_point == pytest.approx((0.0, 0.0, 0.0))
            assert isinstance(result.position, tuple)
        finally:
            cam_mod._PRESETS.clear()
            cam_mod._PRESETS.update(original)


# ---------------------------------------------------------------------------
# apply_camera (coverage: lines 135-149)
# ---------------------------------------------------------------------------


class TestApplyCamera:
    def test_apply_perspective(self):
        """apply_camera sets perspective mode correctly."""
        from unittest.mock import MagicMock

        from viznoir.engine.camera import apply_camera

        renderer = MagicMock()
        camera = MagicMock()
        renderer.GetActiveCamera.return_value = camera

        config = CameraConfig(
            position=(10.0, 0.0, 0.0),
            focal_point=(0.0, 0.0, 0.0),
            view_up=(0.0, 0.0, 1.0),
        )
        apply_camera(renderer, config)

        camera.SetPosition.assert_called_once_with(10.0, 0.0, 0.0)
        camera.SetFocalPoint.assert_called_once_with(0.0, 0.0, 0.0)
        camera.SetViewUp.assert_called_once_with(0.0, 0.0, 1.0)
        camera.SetParallelProjection.assert_called_once_with(False)
        camera.SetParallelScale.assert_not_called()
        renderer.ResetCameraClippingRange.assert_called_once()

    def test_apply_parallel_with_scale(self):
        """apply_camera sets parallel projection and scale."""
        from unittest.mock import MagicMock

        from viznoir.engine.camera import apply_camera

        renderer = MagicMock()
        camera = MagicMock()
        renderer.GetActiveCamera.return_value = camera

        config = CameraConfig(
            position=(0.0, 0.0, 10.0),
            focal_point=(0.0, 0.0, 0.0),
            view_up=(0.0, 1.0, 0.0),
            parallel_projection=True,
            parallel_scale=5.0,
        )
        apply_camera(renderer, config)

        camera.SetParallelProjection.assert_called_once_with(True)
        camera.SetParallelScale.assert_called_once_with(5.0)

    def test_apply_parallel_without_scale(self):
        """apply_camera with parallel projection but no scale."""
        from unittest.mock import MagicMock

        from viznoir.engine.camera import apply_camera

        renderer = MagicMock()
        camera = MagicMock()
        renderer.GetActiveCamera.return_value = camera

        config = CameraConfig(
            position=(0.0, 0.0, 10.0),
            focal_point=(0.0, 0.0, 0.0),
            view_up=(0.0, 1.0, 0.0),
            parallel_projection=True,
            parallel_scale=None,
        )
        apply_camera(renderer, config)

        camera.SetParallelProjection.assert_called_once_with(True)
        camera.SetParallelScale.assert_not_called()
