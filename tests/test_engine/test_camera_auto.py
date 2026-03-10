"""Tests for engine/camera_auto.py — PCA shape analysis + frustum fitting."""

from __future__ import annotations

import math

import numpy as np
import pytest

from viznoir.engine.camera import CameraConfig
from viznoir.engine.camera_auto import (
    ShapeAnalysis,
    _angles_to_direction,
    _classify_shape,
    _compute_frustum_distance,
    _resolve_view_up,
    _shape_to_angles,
    analyze_shape,
    auto_camera_from_bounds,
    extract_surface_points,
)

# ---------------------------------------------------------------------------
# Shape classification
# ---------------------------------------------------------------------------


class TestClassifyShape:
    def test_sphere(self):
        eigvals = np.array([1.0, 1.0, 1.0])
        shape, flat, elong = _classify_shape(eigvals)
        assert shape == "sphere"
        assert flat < 2.0

    def test_plate(self):
        eigvals = np.array([100.0, 80.0, 1.0])
        shape, flat, elong = _classify_shape(eigvals)
        assert shape == "plate"
        assert flat > 10.0

    def test_tube(self):
        eigvals = np.array([100.0, 1.0, 0.5])
        shape, flat, elong = _classify_shape(eigvals)
        assert shape == "tube"
        assert elong > 5.0

    def test_general(self):
        eigvals = np.array([5.0, 3.0, 1.0])
        shape, flat, elong = _classify_shape(eigvals)
        assert shape == "general"

    def test_near_zero_eigenvalues(self):
        eigvals = np.array([0.0, 0.0, 0.0])
        shape, _, _ = _classify_shape(eigvals)
        assert shape == "sphere"


# ---------------------------------------------------------------------------
# Analyze shape
# ---------------------------------------------------------------------------


class TestAnalyzeShape:
    def test_cube_points(self):
        rng = np.random.default_rng(42)
        points = rng.uniform(-1, 1, (1000, 3))
        result = analyze_shape(points)
        assert isinstance(result, ShapeAnalysis)
        assert result.shape == "sphere"  # uniform cube ≈ sphere
        assert len(result.eigvals) == 3
        assert result.eigvals[0] >= result.eigvals[1] >= result.eigvals[2]

    def test_flat_plate(self):
        rng = np.random.default_rng(42)
        points = rng.uniform(-10, 10, (1000, 3))
        points[:, 2] *= 0.01  # flatten Z
        result = analyze_shape(points)
        assert result.shape == "plate"

    def test_elongated_tube(self):
        rng = np.random.default_rng(42)
        points = rng.uniform(-1, 1, (1000, 3))
        points[:, 0] *= 50.0  # stretch X
        result = analyze_shape(points)
        assert result.shape == "tube"

    def test_few_points_fallback(self):
        points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        result = analyze_shape(points)
        assert result.shape == "sphere"  # fallback for < 3 points

    def test_center_is_mean(self):
        points = np.array(
            [
                [0.0, 0.0, 0.0],
                [2.0, 4.0, 6.0],
                [4.0, 8.0, 12.0],
            ]
        )
        result = analyze_shape(points)
        assert result.center == pytest.approx((2.0, 4.0, 6.0))


# ---------------------------------------------------------------------------
# Angles
# ---------------------------------------------------------------------------


class TestAnglesToDirection:
    def test_zero_angles(self):
        d = _angles_to_direction(0.0, 0.0)
        assert d == pytest.approx((1.0, 0.0, 0.0))

    def test_azimuth_90(self):
        d = _angles_to_direction(90.0, 0.0)
        assert d == pytest.approx((0.0, 1.0, 0.0), abs=1e-10)

    def test_elevation_90(self):
        d = _angles_to_direction(0.0, 90.0)
        assert d == pytest.approx((0.0, 0.0, 1.0), abs=1e-10)

    def test_isometric_angles(self):
        d = _angles_to_direction(45.0, 35.264)
        norm = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
        assert norm == pytest.approx(1.0)
        assert d[0] > 0 and d[1] > 0 and d[2] > 0


# ---------------------------------------------------------------------------
# Shape → angles
# ---------------------------------------------------------------------------


class TestShapeToAngles:
    def test_plate_high_elevation(self):
        analysis = ShapeAnalysis(
            eigvals=(100.0, 80.0, 1.0),
            eigvecs=np.eye(3),
            center=(0.0, 0.0, 0.0),
            shape="plate",
            flat_ratio=100.0,
            elongation=1.25,
        )
        az, el = _shape_to_angles(analysis)
        assert el > 45.0  # should look more from above

    def test_tube_low_elevation(self):
        analysis = ShapeAnalysis(
            eigvals=(100.0, 1.0, 0.5),
            eigvecs=np.eye(3),
            center=(0.0, 0.0, 0.0),
            shape="tube",
            flat_ratio=200.0,
            elongation=100.0,
        )
        az, el = _shape_to_angles(analysis)
        assert el < 35.0  # should look more from side

    def test_sphere_isometric(self):
        analysis = ShapeAnalysis(
            eigvals=(1.0, 1.0, 1.0),
            eigvecs=np.eye(3),
            center=(0.0, 0.0, 0.0),
            shape="sphere",
            flat_ratio=1.0,
            elongation=1.0,
        )
        az, el = _shape_to_angles(analysis)
        assert az == pytest.approx(45.0)
        assert el == pytest.approx(35.264)


# ---------------------------------------------------------------------------
# Frustum fitting
# ---------------------------------------------------------------------------


class TestFrustumDistance:
    def test_unit_sphere_distance(self):
        rng = np.random.default_rng(42)
        theta = rng.uniform(0, 2 * math.pi, 500)
        phi = rng.uniform(0, math.pi, 500)
        points = np.column_stack(
            [
                np.sin(phi) * np.cos(theta),
                np.sin(phi) * np.sin(theta),
                np.cos(phi),
            ]
        )
        center = np.array([0.0, 0.0, 0.0])
        view_dir = np.array([1.0, 0.0, 0.0])
        view_up = np.array([0.0, 0.0, 1.0])

        dist = _compute_frustum_distance(
            points,
            center,
            view_dir,
            view_up,
            fov_deg=30.0,
            fill_ratio=0.75,
        )
        assert dist > 0
        # For a unit sphere with 30deg FOV and 75% fill, distance ≈ 5.0
        assert 3.0 < dist < 10.0

    def test_higher_fill_ratio_means_closer(self):
        points = np.array([[-1, -1, 0], [1, -1, 0], [-1, 1, 0], [1, 1, 0.0]])
        center = np.zeros(3)
        view_dir = np.array([0.0, 0.0, 1.0])
        view_up = np.array([0.0, 1.0, 0.0])

        dist_75 = _compute_frustum_distance(points, center, view_dir, view_up, fill_ratio=0.75)
        dist_90 = _compute_frustum_distance(points, center, view_dir, view_up, fill_ratio=0.90)
        assert dist_90 < dist_75  # higher fill = closer camera

    def test_degenerate_points(self):
        points = np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]])
        center = np.array([1.0, 1.0, 1.0])
        view_dir = np.array([0.0, 0.0, 1.0])
        view_up = np.array([0.0, 1.0, 0.0])
        dist = _compute_frustum_distance(points, center, view_dir, view_up)
        assert dist == 1.0  # fallback


# ---------------------------------------------------------------------------
# View up resolution
# ---------------------------------------------------------------------------


class TestResolveViewUp:
    def test_normal_case(self):
        view_dir = np.array([1.0, 0.0, 0.0])
        up = _resolve_view_up(view_dir)
        assert up == (0.0, 0.0, 1.0)

    def test_top_down_falls_back(self):
        view_dir = np.array([0.0, 0.0, 1.0])
        up = _resolve_view_up(view_dir)
        assert up == (0.0, 1.0, 0.0)


# ---------------------------------------------------------------------------
# auto_camera_from_bounds (integration)
# ---------------------------------------------------------------------------


class TestAutoCameraFromBounds:
    def test_returns_camera_config(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam = auto_camera_from_bounds(bounds)
        assert isinstance(cam, CameraConfig)

    def test_focal_point_is_center(self):
        bounds = (0.0, 2.0, 0.0, 4.0, 0.0, 6.0)
        cam = auto_camera_from_bounds(bounds)
        assert cam.focal_point == pytest.approx((1.0, 2.0, 3.0))

    def test_camera_is_outside_bounds(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam = auto_camera_from_bounds(bounds)
        # Camera should be further away than the bounding box diagonal
        dist = math.sqrt(sum((p - f) ** 2 for p, f in zip(cam.position, cam.focal_point)))
        diag = math.sqrt(12)  # 2*sqrt(3)
        assert dist > diag

    def test_zoom_brings_closer(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam_1 = auto_camera_from_bounds(bounds, zoom=1.0)
        cam_2 = auto_camera_from_bounds(bounds, zoom=2.0)
        dist_1 = math.sqrt(sum((p - f) ** 2 for p, f in zip(cam_1.position, cam_1.focal_point)))
        dist_2 = math.sqrt(sum((p - f) ** 2 for p, f in zip(cam_2.position, cam_2.focal_point)))
        assert dist_2 < dist_1

    def test_orthographic_produces_parallel_scale(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam = auto_camera_from_bounds(bounds, orthographic=True)
        assert cam.parallel_projection is True
        assert cam.parallel_scale is not None
        assert cam.parallel_scale > 0

    def test_flat_bounds_plate_detection(self):
        bounds = (-10.0, 10.0, -10.0, 10.0, -0.1, 0.1)
        cam = auto_camera_from_bounds(bounds)
        # For a plate, camera should have higher elevation (looking more from above)
        # Verify camera Z is significantly above center Z
        assert cam.position[2] > cam.focal_point[2] + 1.0

    def test_override_azimuth_elevation(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam = auto_camera_from_bounds(bounds, azimuth=0.0, elevation=0.0)
        # With az=0, el=0, camera should be along +X axis
        dx = cam.position[0] - cam.focal_point[0]
        dy = cam.position[1] - cam.focal_point[1]
        dz = cam.position[2] - cam.focal_point[2]
        assert abs(dx) > abs(dy) and abs(dx) > abs(dz)

    def test_fill_ratio_affects_distance(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam_50 = auto_camera_from_bounds(bounds, fill_ratio=0.5)
        cam_90 = auto_camera_from_bounds(bounds, fill_ratio=0.9)
        dist_50 = math.sqrt(sum((p - f) ** 2 for p, f in zip(cam_50.position, cam_50.focal_point)))
        dist_90 = math.sqrt(sum((p - f) ** 2 for p, f in zip(cam_90.position, cam_90.focal_point)))
        assert dist_90 < dist_50

    def test_orthographic_projection(self):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        cam = auto_camera_from_bounds(bounds, orthographic=True)
        assert cam.parallel_projection is True
        assert cam.parallel_scale is not None
        assert cam.parallel_scale > 0


class TestComputeFrustumDistanceParallel:
    """Test _compute_frustum_distance when view_dir is parallel to view_up."""

    def test_view_dir_parallel_up_z_axis(self):
        """When view_dir and view_up are both Z, should not crash."""
        points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
        center = np.array([0.5, 0.5, 0.0])
        view_dir = np.array([0.0, 0.0, 1.0])
        view_up = np.array([0.0, 0.0, 1.0])
        dist = _compute_frustum_distance(points, center, view_dir, view_up)
        assert dist > 0

    def test_view_dir_parallel_up_x_axis(self):
        """When view_dir is [1,0,0] and up is [1,0,0], should use fallback."""
        points = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        center = np.array([0.0, 0.5, 0.5])
        view_dir = np.array([1.0, 0.0, 0.0])
        view_up = np.array([1.0, 0.0, 0.0])
        dist = _compute_frustum_distance(points, center, view_dir, view_up)
        assert dist > 0


class TestResolveViewUpEdgeCases:
    """Test _resolve_view_up with parallel view direction."""

    def test_view_dir_parallel_to_default_up_z(self):
        """When view_dir is along Z, should pick perpendicular up."""
        view_dir = np.array([0.0, 0.0, 1.0])
        view_up = np.array([0.0, 0.0, 1.0])
        result = _resolve_view_up(view_dir, view_up)
        # Result should be perpendicular to view_dir
        dot = abs(np.dot(result / np.linalg.norm(result), view_dir))
        assert dot < 0.1

    def test_view_dir_parallel_to_default_up_nonz(self):
        """When view_dir is along a non-Z axis and parallel to up."""
        view_dir = np.array([1.0, 0.0, 0.0])
        view_up = np.array([1.0, 0.0, 0.0])
        result = _resolve_view_up(view_dir, view_up)
        dot = abs(np.dot(result / np.linalg.norm(result), view_dir / np.linalg.norm(view_dir)))
        assert dot < 0.1


class TestAutoCameraWithVTK:
    """Tests requiring VTK for auto_camera with real datasets."""

    vtk = pytest.importorskip("vtk")

    def test_auto_camera_empty_polydata(self):
        """auto_camera with empty polydata falls back to bounds."""
        import vtk

        from viznoir.engine.camera_auto import auto_camera

        pd = vtk.vtkPolyData()
        # No points set → empty
        cam = auto_camera(pd)
        assert isinstance(cam, CameraConfig)

    def test_auto_camera_with_points(self):
        """auto_camera with real polydata produces valid camera."""
        import vtk

        from viznoir.engine.camera_auto import auto_camera

        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        for x in range(10):
            for y in range(10):
                pts.InsertNextPoint(float(x), float(y), 0.0)
        pd.SetPoints(pts)

        cam = auto_camera(pd)
        assert isinstance(cam, CameraConfig)
        # Camera should be above the XY plane for a flat plate
        assert cam.position[2] > 0.0

    def test_auto_camera_orthographic(self):
        """auto_camera with orthographic projection."""
        import vtk

        from viznoir.engine.camera_auto import auto_camera

        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(1, 0, 0)
        pts.InsertNextPoint(0, 1, 0)
        pd.SetPoints(pts)

        cam = auto_camera(pd, orthographic=True)
        assert cam.parallel_projection is True
        assert cam.parallel_scale is not None

    def test_extract_surface_points_subsampling(self):
        """extract_surface_points subsamples large point sets."""
        import vtk

        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        for i in range(20000):
            pts.InsertNextPoint(float(i), 0.0, 0.0)
        pd.SetPoints(pts)

        # max_points < num_points triggers subsampling
        result = extract_surface_points(pd, max_points=1000)
        assert result.shape[0] == 1000
