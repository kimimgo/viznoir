"""Field topology extraction — vortex detection, critical points, centerline profiles.

Pure VTK + numpy analysis of field topology features. Works with any VTK dataset
that has velocity (vector) or scalar fields attached as point data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Vortex:
    """A detected vortex region."""

    center: list[float]
    strength: float
    rotation: str  # "clockwise" / "counter-clockwise"
    radius: float | None = None


@dataclass
class CriticalPoint:
    """A point where velocity magnitude is near zero."""

    position: list[float]
    type: str  # "stagnation" / "separation" / "reattachment"
    velocity_magnitude: float


@dataclass
class LineProfile:
    """Sampled field values along a probe line through the domain."""

    start: list[float]
    end: list[float]
    num_points: int
    fields: dict[str, list[float]]  # field_name → sampled values


@dataclass
class FieldTopology:
    """Complete topology analysis result for a single field."""

    field_name: str
    field_range: dict[str, float]  # min, max, mean, std
    vortices: list[Vortex] = field(default_factory=list)
    critical_points: list[CriticalPoint] = field(default_factory=list)
    centerline_profiles: list[LineProfile] = field(default_factory=list)
    gradient_stats: dict[str, Any] = field(default_factory=dict)
    spatial_distribution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""

        def _convert(obj: Any) -> Any:
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(v) for v in obj]
            return obj

        return _convert({
            "field_name": self.field_name,
            "field_range": self.field_range,
            "vortices": [
                {"center": v.center, "strength": v.strength, "rotation": v.rotation, "radius": v.radius}
                for v in self.vortices
            ],
            "critical_points": [
                {"position": cp.position, "type": cp.type, "velocity_magnitude": cp.velocity_magnitude}
                for cp in self.critical_points
            ],
            "centerline_profiles": [
                {"start": lp.start, "end": lp.end, "num_points": lp.num_points, "fields": lp.fields}
                for lp in self.centerline_profiles
            ],
            "gradient_stats": self.gradient_stats,
            "spatial_distribution": self.spatial_distribution,
        })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_field_array(dataset: Any, field_name: str) -> Any:
    """Get a VTK array from point data (preferred) or cell data."""
    arr = dataset.GetPointData().GetArray(field_name)
    if arr is not None:
        return arr
    arr = dataset.GetCellData().GetArray(field_name)
    if arr is not None:
        return arr
    msg = f"Field '{field_name}' not found in dataset"
    raise KeyError(msg)


def _is_vector_field(dataset: Any, field_name: str) -> bool:
    """Check if a field has 3 components (vector)."""
    arr = _get_field_array(dataset, field_name)
    result: bool = arr.GetNumberOfComponents() == 3
    return result


def _get_bounds(dataset: Any) -> tuple[float, float, float, float, float, float]:
    """Get dataset bounding box as (xmin, xmax, ymin, ymax, zmin, zmax)."""
    b = dataset.GetBounds()
    return b[0], b[1], b[2], b[3], b[4], b[5]


def _is_2d(dataset: Any) -> bool:
    """Check if dataset is essentially 2D (thin extent in z)."""
    b = _get_bounds(dataset)
    z_extent = b[5] - b[4]
    max_extent = max(b[1] - b[0], b[3] - b[2], z_extent)
    if max_extent == 0:
        return True
    return z_extent / max_extent < 0.01


# ---------------------------------------------------------------------------
# 1. Vortex Detection (Q-criterion based)
# ---------------------------------------------------------------------------


def detect_vortices(
    dataset: Any,
    field_name: str,
    threshold: float = 0.01,
) -> list[Vortex]:
    """Detect vortex regions using Q-criterion and vorticity.

    For scalar fields or zero-velocity fields, returns empty list.
    """
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    arr = _get_field_array(dataset, field_name)
    if arr.GetNumberOfComponents() != 3:
        return []

    vel_np = vtk_to_numpy(arr)
    if np.allclose(vel_np, 0.0):
        return []

    # Compute Q-criterion and vorticity via vtkGradientFilter
    grad_filter = vtk.vtkGradientFilter()
    grad_filter.SetInputData(dataset)
    grad_filter.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, field_name)
    grad_filter.SetResultArrayName("Gradients")
    grad_filter.SetComputeQCriterion(True)
    grad_filter.SetQCriterionArrayName("QCriterion")
    grad_filter.SetComputeVorticity(True)
    grad_filter.SetVorticityArrayName("Vorticity")
    grad_filter.Update()
    output = grad_filter.GetOutput()

    q_arr = output.GetPointData().GetArray("QCriterion")
    vort_arr = output.GetPointData().GetArray("Vorticity")
    if q_arr is None or vort_arr is None:
        return []

    q_values = vtk_to_numpy(q_arr)
    vorticity = vtk_to_numpy(vort_arr)

    q_max = float(np.max(q_values))
    if q_max <= 0:
        return []

    # Adaptive threshold: fraction of max Q
    effective_threshold = min(threshold, q_max * 0.1)

    vortex_mask = q_values > effective_threshold
    vortex_indices = np.where(vortex_mask)[0]
    if len(vortex_indices) == 0:
        return []

    # Get all point coordinates
    n_pts = output.GetNumberOfPoints()
    coords = np.zeros((n_pts, 3), dtype=np.float64)
    for i in range(n_pts):
        coords[i] = output.GetPoint(i)

    vortex_coords = coords[vortex_indices]
    vortex_q = q_values[vortex_indices]
    vortex_vort = vorticity[vortex_indices]

    # Clustering radius: ~15% of domain max extent
    bounds = _get_bounds(output)
    extents = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
    cluster_radius = max(extents) * 0.15

    clusters = _cluster_points(vortex_coords, vortex_q, vortex_vort, cluster_radius)

    vortices = []
    for cluster in clusters:
        center = cluster["center"].tolist()
        strength = float(cluster["strength"])
        omega_z = float(cluster["mean_vorticity"][2])
        rotation = "clockwise" if omega_z < 0 else "counter-clockwise"
        vortices.append(Vortex(
            center=center,
            strength=strength,
            rotation=rotation,
            radius=cluster.get("radius"),
        ))

    vortices.sort(key=lambda v: v.strength, reverse=True)
    return vortices


def _cluster_points(
    coords: np.ndarray,
    q_values: np.ndarray,
    vorticity: np.ndarray,
    radius: float,
) -> list[dict[str, Any]]:
    """Greedy clustering: pick highest-Q seed, gather neighbors, repeat."""
    remaining = np.ones(len(coords), dtype=bool)
    clusters: list[dict[str, Any]] = []

    max_clusters = 20
    while np.any(remaining) and len(clusters) < max_clusters:
        remaining_idx = np.where(remaining)[0]
        best_local = np.argmax(q_values[remaining_idx])
        seed_idx = remaining_idx[best_local]
        seed_pos = coords[seed_idx]

        dists = np.linalg.norm(coords[remaining_idx] - seed_pos, axis=1)
        in_cluster = dists < radius
        cluster_indices = remaining_idx[in_cluster]

        if len(cluster_indices) == 0:
            break

        cluster_q = q_values[cluster_indices]
        cluster_coords = coords[cluster_indices]
        cluster_vort = vorticity[cluster_indices]

        weights = cluster_q / cluster_q.sum()
        weighted_center: np.ndarray = np.average(cluster_coords, axis=0, weights=weights)
        mean_vort: np.ndarray = np.average(cluster_vort, axis=0, weights=weights)
        strength = float(np.max(cluster_q))

        cluster_dists: np.ndarray = np.linalg.norm(cluster_coords - weighted_center, axis=1)
        cluster_radius = float(np.max(cluster_dists)) if len(cluster_dists) > 1 else radius * 0.5

        clusters.append({
            "center": weighted_center,
            "strength": strength,
            "mean_vorticity": mean_vort,
            "radius": cluster_radius,
        })
        remaining[cluster_indices] = False

    return clusters


# ---------------------------------------------------------------------------
# 2. Critical Points (near-zero velocity)
# ---------------------------------------------------------------------------


def detect_critical_points(
    dataset: Any,
    field_name: str,
    epsilon: float = 0.05,
) -> list[CriticalPoint]:
    """Detect critical points where velocity magnitude is near zero.

    For scalar fields: finds points where gradient magnitude is near zero.
    """
    arr = _get_field_array(dataset, field_name)
    is_vector = arr.GetNumberOfComponents() == 3

    if is_vector:
        return _detect_vector_critical_points(dataset, field_name, arr, epsilon)
    return _detect_scalar_critical_points(dataset, field_name, epsilon)


def _detect_vector_critical_points(
    dataset: Any,
    field_name: str,
    arr: Any,
    epsilon: float,
) -> list[CriticalPoint]:
    """Find points where velocity magnitude < epsilon * max_magnitude."""
    from vtk.util.numpy_support import vtk_to_numpy

    vel = vtk_to_numpy(arr)
    mag: np.ndarray = np.linalg.norm(vel, axis=1)
    max_mag = float(np.max(mag))
    if max_mag == 0:
        return []

    threshold_val = epsilon * max_mag
    critical_indices = np.where(mag < threshold_val)[0]
    if len(critical_indices) == 0:
        return []

    n_pts = dataset.GetNumberOfPoints()
    coords = np.zeros((n_pts, 3), dtype=np.float64)
    for i in range(n_pts):
        coords[i] = dataset.GetPoint(i)

    sorted_indices = critical_indices[np.argsort(mag[critical_indices])]

    # Filter neighbors: min separation
    bounds = _get_bounds(dataset)
    max_extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
    min_separation = max_extent * 0.05

    selected: list[CriticalPoint] = []
    used_positions: list[np.ndarray] = []

    for idx in sorted_indices:
        pos = coords[idx]
        too_close = any(float(np.linalg.norm(pos - used)) < min_separation for used in used_positions)
        if too_close:
            continue

        selected.append(CriticalPoint(
            position=pos.tolist(),
            type="stagnation",
            velocity_magnitude=float(mag[idx]),
        ))
        used_positions.append(pos)
        if len(selected) >= 20:
            break

    return selected


def _detect_scalar_critical_points(
    dataset: Any,
    field_name: str,
    epsilon: float,
) -> list[CriticalPoint]:
    """Find points where scalar gradient magnitude is near zero."""
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    grad_filter = vtk.vtkGradientFilter()
    grad_filter.SetInputData(dataset)
    grad_filter.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, field_name)
    grad_filter.SetResultArrayName("ScalarGradient")
    grad_filter.Update()
    output = grad_filter.GetOutput()

    grad_arr = output.GetPointData().GetArray("ScalarGradient")
    if grad_arr is None:
        return []

    grad_data = vtk_to_numpy(grad_arr)
    if grad_data.ndim == 1:
        grad_mag = np.abs(grad_data)
    else:
        grad_mag: np.ndarray = np.linalg.norm(grad_data, axis=1)

    max_grad = float(np.max(grad_mag))
    if max_grad == 0:
        return []

    threshold_val = epsilon * max_grad
    critical_indices = np.where(grad_mag < threshold_val)[0]
    if len(critical_indices) == 0:
        return []

    n_pts = output.GetNumberOfPoints()
    coords = np.zeros((n_pts, 3), dtype=np.float64)
    for i in range(n_pts):
        coords[i] = output.GetPoint(i)

    sorted_indices = critical_indices[np.argsort(grad_mag[critical_indices])]

    bounds = _get_bounds(dataset)
    max_extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
    min_separation = max_extent * 0.05

    selected: list[CriticalPoint] = []
    used_positions: list[np.ndarray] = []

    for idx in sorted_indices:
        pos = coords[idx]
        too_close = any(float(np.linalg.norm(pos - used)) < min_separation for used in used_positions)
        if too_close:
            continue

        selected.append(CriticalPoint(
            position=pos.tolist(),
            type="stagnation",
            velocity_magnitude=float(grad_mag[idx]),
        ))
        used_positions.append(pos)
        if len(selected) >= 20:
            break

    return selected


# ---------------------------------------------------------------------------
# 3. Centerline Profiles (probe lines through domain)
# ---------------------------------------------------------------------------


def extract_centerline_profiles(
    dataset: Any,
    field_names: list[str],
    num_lines: int = 3,
    num_points: int = 100,
) -> list[LineProfile]:
    """Extract field values along centerline probe lines through the domain.

    Auto-detects centerlines from bounding box (x, y, z axis midlines).
    Uses vtkLineSource + vtkProbeFilter.
    """
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    bounds = _get_bounds(dataset)
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    cz = (zmin + zmax) / 2

    is_2d_ds = _is_2d(dataset)

    # Define candidate probe lines through center
    candidates: list[tuple[list[float], list[float]]] = []
    if ymax > ymin:
        candidates.append(([cx, ymin, cz], [cx, ymax, cz]))
    if xmax > xmin:
        candidates.append(([xmin, cy, cz], [xmax, cy, cz]))
    if not is_2d_ds and zmax > zmin:
        candidates.append(([cx, cy, zmin], [cx, cy, zmax]))

    lines_to_probe = candidates[:num_lines]
    profiles: list[LineProfile] = []

    for start, end in lines_to_probe:
        line_source = vtk.vtkLineSource()
        line_source.SetPoint1(*start)
        line_source.SetPoint2(*end)
        line_source.SetResolution(num_points - 1)
        line_source.Update()

        probe = vtk.vtkProbeFilter()
        probe.SetInputConnection(line_source.GetOutputPort())
        probe.SetSourceData(dataset)
        probe.Update()
        probed = probe.GetOutput()

        n_probed = probed.GetNumberOfPoints()
        if n_probed == 0:
            continue

        # Extract field values
        fields: dict[str, list[float]] = {}
        for fname in field_names:
            arr = probed.GetPointData().GetArray(fname)
            if arr is None:
                continue
            data = vtk_to_numpy(arr)
            if arr.GetNumberOfComponents() == 3:
                fields[f"{fname}x"] = data[:, 0].tolist()
                fields[f"{fname}y"] = data[:, 1].tolist()
                fields[f"{fname}z"] = data[:, 2].tolist()
            elif arr.GetNumberOfComponents() == 1:
                fields[fname] = data.tolist()
            else:
                for c in range(arr.GetNumberOfComponents()):
                    fields[f"{fname}_{c}"] = data[:, c].tolist()

        if not fields:
            continue

        profiles.append(LineProfile(
            start=start,
            end=end,
            num_points=n_probed,
            fields=fields,
        ))

    return profiles


# ---------------------------------------------------------------------------
# 4. Gradient Statistics
# ---------------------------------------------------------------------------


def compute_gradient_stats(
    dataset: Any,
    field_name: str,
) -> dict[str, Any]:
    """Compute gradient magnitude statistics for a field.

    Returns dict with mean_magnitude, max_magnitude, dominant_direction.
    """
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    grad_filter = vtk.vtkGradientFilter()
    grad_filter.SetInputData(dataset)
    grad_filter.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, field_name)
    grad_filter.SetResultArrayName("Gradient")
    grad_filter.Update()
    output = grad_filter.GetOutput()

    grad_arr = output.GetPointData().GetArray("Gradient")
    if grad_arr is None:
        return {"mean_magnitude": 0.0, "max_magnitude": 0.0, "dominant_direction": [0, 0, 0]}

    grad_data = vtk_to_numpy(grad_arr)
    n_comp = grad_arr.GetNumberOfComponents()

    if n_comp == 3:
        grad_mag: np.ndarray = np.linalg.norm(grad_data, axis=1)
        mean_grad = grad_data.mean(axis=0)
        mean_norm = float(np.linalg.norm(mean_grad))
        dominant = (mean_grad / mean_norm).tolist() if mean_norm > 0 else [0.0, 0.0, 0.0]
    elif n_comp == 9:
        grad_reshaped = grad_data.reshape(-1, 3, 3)
        grad_mag = np.linalg.norm(grad_reshaped, axis=(1, 2))
        dominant = [0.0, 0.0, 0.0]
    else:
        grad_mag = np.abs(grad_data).flatten() if grad_data.ndim == 1 else np.linalg.norm(grad_data, axis=1)
        dominant = [0.0, 0.0, 0.0]

    return {
        "mean_magnitude": float(np.mean(grad_mag)),
        "max_magnitude": float(np.max(grad_mag)),
        "dominant_direction": dominant,
    }


# ---------------------------------------------------------------------------
# 5. Full Topology Analysis (orchestrator)
# ---------------------------------------------------------------------------


def analyze_field_topology(
    dataset: Any,
    field_name: str,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> FieldTopology:
    """Run complete topology analysis on a field.

    Vector fields: vortex detection + critical points + profiles + gradients.
    Scalar fields: profiles + gradients + field range.
    """
    from vtk.util.numpy_support import vtk_to_numpy

    is_vector = _is_vector_field(dataset, field_name)

    vortices: list[Vortex] = []
    critical_points: list[CriticalPoint] = []
    if is_vector:
        vortices = detect_vortices(dataset, field_name, threshold=vortex_threshold)
        critical_points = detect_critical_points(dataset, field_name)

    profiles = extract_centerline_profiles(dataset, [field_name], num_lines=probe_lines)
    grad_stats = compute_gradient_stats(dataset, field_name)

    # Compute field range
    arr = _get_field_array(dataset, field_name)
    data = vtk_to_numpy(arr)
    if arr.GetNumberOfComponents() == 3:
        mag: np.ndarray = np.linalg.norm(data, axis=1)
    else:
        mag = data.flatten() if data.ndim > 1 else data

    field_range: dict[str, float] = {
        "min": float(np.min(mag)),
        "max": float(np.max(mag)),
        "mean": float(np.mean(mag)),
        "std": float(np.std(mag)),
    }

    return FieldTopology(
        field_name=field_name,
        field_range=field_range,
        vortices=vortices,
        critical_points=critical_points,
        centerline_profiles=profiles,
        gradient_stats=grad_stats,
    )
