"""Automatic camera positioning via PCA-based shape analysis and frustum fitting.

Analyzes the geometry of a VTK dataset to determine optimal camera placement:
1. PCA eigenvalue decomposition → shape classification (plate/tube/sphere/general)
2. Shape-aware azimuth/elevation selection
3. Frustum-aware distance calculation for target fill ratio (default 75%)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from viznoir.engine.camera import CameraConfig

if TYPE_CHECKING:
    import vtk


# ---------------------------------------------------------------------------
# Shape classification
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShapeAnalysis:
    """Result of PCA-based shape analysis."""

    eigvals: tuple[float, float, float]  # descending order
    eigvecs: np.ndarray  # (3, 3) columns = principal axes
    center: tuple[float, float, float]
    shape: str  # "plate", "tube", "sphere", "general"
    flat_ratio: float  # eigvals[0] / eigvals[2] — flatness measure
    elongation: float  # eigvals[0] / eigvals[1] — elongation measure


def _classify_shape(eigvals: np.ndarray) -> tuple[str, float, float]:
    """Classify shape from PCA eigenvalues (descending order).

    Returns (shape_name, flat_ratio, elongation).
    """
    e = np.maximum(eigvals, 1e-12)  # avoid division by zero
    flat_ratio = e[0] / e[2]
    elongation = e[0] / e[1]

    if flat_ratio > 10.0 and elongation < 2.0:
        return "plate", flat_ratio, elongation
    elif elongation > 5.0:
        return "tube", flat_ratio, elongation
    elif flat_ratio < 2.0:
        return "sphere", flat_ratio, elongation
    else:
        return "general", flat_ratio, elongation


def analyze_shape(
    points: np.ndarray,
) -> ShapeAnalysis:
    """Run PCA on point cloud to classify shape and find principal axes.

    Args:
        points: (N, 3) array of surface points.

    Returns:
        ShapeAnalysis with eigenvalues, eigenvectors, center, classification.
    """
    if points.shape[0] < 3:
        _m = points.mean(axis=0)
        center: tuple[float, float, float] = (float(_m[0]), float(_m[1]), float(_m[2]))
        return ShapeAnalysis(
            eigvals=(1.0, 1.0, 1.0),
            eigvecs=np.eye(3),
            center=center,
            shape="sphere",
            flat_ratio=1.0,
            elongation=1.0,
        )

    center_arr = points.mean(axis=0)
    centered = points - center_arr

    # Covariance matrix — eigh is faster than SVD for symmetric matrices
    cov = centered.T @ centered / (points.shape[0] - 1)
    eigvals_raw, eigvecs = np.linalg.eigh(cov)

    # eigh returns ascending order → reverse to descending
    idx = np.argsort(eigvals_raw)[::-1]
    eigvals_sorted = eigvals_raw[idx]
    eigvecs_sorted = eigvecs[:, idx]

    shape, flat_ratio, elongation = _classify_shape(eigvals_sorted)
    center = (float(center_arr[0]), float(center_arr[1]), float(center_arr[2]))
    ev: tuple[float, float, float] = (float(eigvals_sorted[0]), float(eigvals_sorted[1]), float(eigvals_sorted[2]))

    return ShapeAnalysis(
        eigvals=ev,
        eigvecs=eigvecs_sorted,
        center=center,
        shape=shape,
        flat_ratio=flat_ratio,
        elongation=elongation,
    )


# ---------------------------------------------------------------------------
# Optimal view direction
# ---------------------------------------------------------------------------

def _shape_to_angles(analysis: ShapeAnalysis) -> tuple[float, float]:
    """Select optimal (azimuth, elevation) in degrees based on shape.

    Azimuth: rotation in XY plane (0=+X, 90=+Y).
    Elevation: angle from XY plane (0=horizon, 90=top).
    """
    shape = analysis.shape

    if shape == "plate":
        # Look along the thinnest axis (normal to plate)
        # Slight tilt for depth perception
        return 35.0, 55.0

    elif shape == "tube":
        # 3/4 view perpendicular to longest axis
        return 40.0, 25.0

    elif shape == "sphere":
        # Classic isometric
        return 45.0, 35.264

    else:  # general
        # 3/4 view — balanced depth cues
        return 40.0, 30.0


def _angles_to_direction(
    azimuth_deg: float, elevation_deg: float
) -> tuple[float, float, float]:
    """Convert (azimuth, elevation) to unit direction vector.

    Uses mathematical convention:
    - azimuth: angle from +X toward +Y in XY plane
    - elevation: angle from XY plane toward +Z
    """
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    cos_el = math.cos(el)
    return (
        cos_el * math.cos(az),
        cos_el * math.sin(az),
        math.sin(el),
    )


# ---------------------------------------------------------------------------
# Frustum fitting
# ---------------------------------------------------------------------------

def _compute_frustum_distance(
    points: np.ndarray,
    center: np.ndarray,
    view_dir: np.ndarray,
    view_up: np.ndarray,
    fov_deg: float = 30.0,
    aspect_ratio: float = 16.0 / 9.0,
    fill_ratio: float = 0.75,
) -> float:
    """Compute camera distance so that the object fills `fill_ratio` of the frame.

    Projects all points onto the view plane and calculates the minimum distance
    where the bounding rectangle of projected points fits within the frustum.

    Args:
        points: (N, 3) point cloud.
        center: (3,) focal point.
        view_dir: (3,) unit vector from focal point to camera.
        view_up: (3,) camera up vector.
        fov_deg: Vertical field of view in degrees.
        aspect_ratio: Width / height of the viewport.
        fill_ratio: Target fraction of viewport to fill (0.0–1.0).

    Returns:
        Camera distance from focal point.
    """
    # Build orthonormal camera frame
    view_dir_n = view_dir / (np.linalg.norm(view_dir) + 1e-12)
    view_up_n = view_up / (np.linalg.norm(view_up) + 1e-12)

    # Right = view_dir × up (camera looks along -view_dir, but we place camera at center + view_dir * dist)
    right = np.cross(view_dir_n, view_up_n)
    right_norm = np.linalg.norm(right)
    if right_norm < 1e-6:
        # view_dir parallel to view_up — pick arbitrary perpendicular
        if abs(view_dir_n[2]) < 0.9:
            right = np.cross(view_dir_n, np.array([0.0, 0.0, 1.0]))
        else:
            right = np.cross(view_dir_n, np.array([1.0, 0.0, 0.0]))
        right_norm = np.linalg.norm(right)
    right /= right_norm

    # Recompute up to ensure orthogonality
    up = np.cross(right, view_dir_n)
    up /= np.linalg.norm(up) + 1e-12

    # Project points onto view plane (right, up axes)
    relative = points - center
    proj_right = relative @ right
    proj_up = relative @ up

    # Bounding box on the view plane
    half_w = max(abs(proj_right.max()), abs(proj_right.min()))
    half_h = max(abs(proj_up.max()), abs(proj_up.min()))

    if half_w < 1e-10 and half_h < 1e-10:
        # Degenerate — all points at center
        return 1.0

    # Adjust for fill ratio: we want the object to fill `fill_ratio` of the viewport
    half_w /= fill_ratio
    half_h /= fill_ratio

    # Distance from vertical FOV constraint
    half_fov_v = math.radians(fov_deg / 2.0)
    dist_from_height = half_h / math.tan(half_fov_v)

    # Distance from horizontal FOV constraint
    half_fov_h = math.atan(math.tan(half_fov_v) * aspect_ratio)
    dist_from_width = half_w / math.tan(half_fov_h)

    return float(max(dist_from_height, dist_from_width))


# ---------------------------------------------------------------------------
# View-up resolution
# ---------------------------------------------------------------------------

def _resolve_view_up(
    view_dir: np.ndarray, preferred_up: np.ndarray | None = None
) -> tuple[float, float, float]:
    """Determine a valid view-up vector that isn't parallel to view direction."""
    if preferred_up is None:
        preferred_up = np.array([0.0, 0.0, 1.0])

    cross = np.cross(view_dir, preferred_up)
    if np.linalg.norm(cross) < 1e-6:
        # View direction is nearly parallel to Z — fall back to Y-up
        preferred_up = np.array([0.0, 1.0, 0.0])

    return (float(preferred_up[0]), float(preferred_up[1]), float(preferred_up[2]))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_surface_points(dataset: vtk.vtkDataObject, max_points: int = 50000) -> np.ndarray:
    """Extract surface points from a VTK dataset for PCA analysis.

    Applies vtkGeometryFilter if needed, then subsamples if too many points.

    Args:
        dataset: Any VTK dataset (structured, unstructured, polydata, etc.).
        max_points: Maximum points to use for PCA (subsampled uniformly).

    Returns:
        (N, 3) numpy array of surface points.
    """
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    # Convert to polydata if needed
    if isinstance(dataset, vtk.vtkPolyData):
        poly = dataset
    else:
        geom = vtk.vtkGeometryFilter()
        geom.SetInputData(dataset)
        geom.Update()
        poly = geom.GetOutput()

    vtk_points = poly.GetPoints()
    if vtk_points is None or vtk_points.GetNumberOfPoints() == 0:
        return np.zeros((0, 3))

    points = vtk_to_numpy(vtk_points.GetData())

    # Subsample if too many points
    n = points.shape[0]
    if n > max_points:
        indices = np.linspace(0, n - 1, max_points, dtype=int)
        points = points[indices]

    return points.astype(np.float64)  # type: ignore[no-any-return]


def auto_camera(
    dataset: vtk.vtkDataObject,
    *,
    fill_ratio: float = 0.75,
    fov_deg: float = 30.0,
    aspect_ratio: float = 16.0 / 9.0,
    azimuth: float | None = None,
    elevation: float | None = None,
    zoom: float = 1.0,
    orthographic: bool = False,
) -> CameraConfig:
    """Compute optimal camera placement for a VTK dataset.

    Uses PCA-based shape analysis to determine the best viewing angle,
    then frustum fitting to ensure the object fills the target viewport fraction.

    Args:
        dataset: VTK dataset to frame.
        fill_ratio: Target fill (0.0–1.0). Default 0.75 = 75% of viewport.
        fov_deg: Vertical field of view. Default 30 (VTK default).
        aspect_ratio: Viewport width/height. Default 16:9.
        azimuth: Override azimuth in degrees (None = auto from shape).
        elevation: Override elevation in degrees (None = auto from shape).
        zoom: Additional zoom factor (>1 = closer).
        orthographic: Use parallel projection.

    Returns:
        CameraConfig positioned for optimal viewing.
    """
    points = extract_surface_points(dataset)

    if points.shape[0] == 0:
        # Fallback: use bounds
        bounds = dataset.GetBounds()
        from viznoir.engine.camera import preset_camera
        return preset_camera("isometric", bounds, zoom=zoom, orthographic=orthographic)

    analysis = analyze_shape(points)

    # Determine viewing angles
    auto_az, auto_el = _shape_to_angles(analysis)
    az = azimuth if azimuth is not None else auto_az
    el = elevation if elevation is not None else auto_el

    # View direction (from center toward camera position)
    view_dir = np.array(_angles_to_direction(az, el))

    # View up
    view_up_arr = np.array([0.0, 0.0, 1.0])
    view_up = _resolve_view_up(view_dir, view_up_arr)
    view_up_arr = np.array(view_up)

    # Frustum distance
    center = np.array(analysis.center)
    distance = _compute_frustum_distance(
        points, center, view_dir, view_up_arr,
        fov_deg=fov_deg,
        aspect_ratio=aspect_ratio,
        fill_ratio=fill_ratio,
    )
    distance /= zoom  # zoom > 1 means closer

    # Camera position
    position = center + view_dir * distance
    position_t: tuple[float, float, float] = (float(position[0]), float(position[1]), float(position[2]))

    # Parallel scale for orthographic
    parallel_scale = None
    if orthographic:
        half_fov = math.radians(fov_deg / 2.0)
        parallel_scale = distance * math.tan(half_fov) / zoom

    return CameraConfig(
        position=position_t,
        focal_point=analysis.center,
        view_up=view_up,
        parallel_projection=orthographic,
        parallel_scale=parallel_scale,
        zoom=zoom,
    )


def auto_camera_from_bounds(
    bounds: tuple[float, float, float, float, float, float],
    *,
    fill_ratio: float = 0.75,
    fov_deg: float = 30.0,
    aspect_ratio: float = 16.0 / 9.0,
    azimuth: float | None = None,
    elevation: float | None = None,
    zoom: float = 1.0,
    orthographic: bool = False,
) -> CameraConfig:
    """Simplified auto camera using only bounding box (no VTK dataset needed).

    Generates 8 corner points from bounds, runs PCA, then frustum fits.
    Less accurate than full surface analysis but works without VTK import.
    """
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    corners = np.array([
        [xmin, ymin, zmin], [xmax, ymin, zmin],
        [xmin, ymax, zmin], [xmax, ymax, zmin],
        [xmin, ymin, zmax], [xmax, ymin, zmax],
        [xmin, ymax, zmax], [xmax, ymax, zmax],
    ])

    analysis = analyze_shape(corners)

    auto_az, auto_el = _shape_to_angles(analysis)
    az = azimuth if azimuth is not None else auto_az
    el = elevation if elevation is not None else auto_el

    view_dir = np.array(_angles_to_direction(az, el))
    view_up = _resolve_view_up(view_dir)
    view_up_arr = np.array(view_up)

    center = np.array(analysis.center)
    distance = _compute_frustum_distance(
        corners, center, view_dir, view_up_arr,
        fov_deg=fov_deg,
        aspect_ratio=aspect_ratio,
        fill_ratio=fill_ratio,
    )
    distance /= zoom

    position = center + view_dir * distance
    position_t: tuple[float, float, float] = (float(position[0]), float(position[1]), float(position[2]))

    parallel_scale = None
    if orthographic:
        half_fov = math.radians(fov_deg / 2.0)
        parallel_scale = distance * math.tan(half_fov) / zoom

    return CameraConfig(
        position=position_t,
        focal_point=analysis.center,
        view_up=view_up,
        parallel_projection=orthographic,
        parallel_scale=parallel_scale,
        zoom=zoom,
    )
