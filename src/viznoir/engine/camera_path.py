"""Camera path animation — Bezier spline with easing for cinematic camera moves."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CameraKeyframe:
    """A single keyframe in a camera path."""

    position: tuple[float, float, float]
    focal_point: tuple[float, float, float]
    view_up: tuple[float, float, float] = (0.0, 0.0, 1.0)
    t: float = 0.0  # normalized time [0, 1]


@dataclass(frozen=True)
class CameraPath:
    """A sequence of keyframes defining a camera trajectory."""

    keyframes: tuple[CameraKeyframe, ...]
    easing: str = "ease_in_out"  # linear, ease_in, ease_out, ease_in_out


# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------

def _ease_linear(t: float) -> float:
    return t


def _ease_in(t: float) -> float:
    """Quadratic ease-in: slow start."""
    return t * t


def _ease_out(t: float) -> float:
    """Quadratic ease-out: slow end."""
    return t * (2.0 - t)


def _ease_in_out(t: float) -> float:
    """Cubic ease-in-out: slow start and end."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


EASING_FUNCTIONS = {
    "linear": _ease_linear,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
}


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def _lerp_tuple(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    t: float,
) -> tuple[float, float, float]:
    """Linear interpolation between two 3-tuples."""
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _catmull_rom(
    p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray,
    t: float,
) -> np.ndarray:
    """Catmull-Rom spline interpolation between p1 and p2.

    p0, p3 are control points for tangent calculation.
    """
    t2 = t * t
    t3 = t2 * t
    result = 0.5 * (
        (2.0 * p1) +
        (-p0 + p2) * t +
        (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 +
        (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )
    return result  # type: ignore[no-any-return]


def interpolate_path(
    path: CameraPath,
    num_frames: int,
) -> list[CameraKeyframe]:
    """Generate interpolated keyframes along a camera path.

    Uses Catmull-Rom spline for smooth position interpolation
    and linear interpolation for focal point and view up.

    Args:
        path: Camera path with keyframes.
        num_frames: Number of output frames.

    Returns:
        List of interpolated CameraKeyframes, one per frame.
    """
    kfs = path.keyframes
    if len(kfs) < 2:
        return [kfs[0]] * num_frames if kfs else []

    ease_fn = EASING_FUNCTIONS.get(path.easing, _ease_in_out)

    # Extract arrays for Catmull-Rom
    positions = np.array([kf.position for kf in kfs])
    focals = np.array([kf.focal_point for kf in kfs])
    ups = np.array([kf.view_up for kf in kfs])

    # Extend endpoints for Catmull-Rom (mirror first/last)
    pos_ext = np.vstack([
        2 * positions[0] - positions[1],
        positions,
        2 * positions[-1] - positions[-2],
    ])
    foc_ext = np.vstack([
        2 * focals[0] - focals[1],
        focals,
        2 * focals[-1] - focals[-2],
    ])

    n_segments = len(kfs) - 1
    result: list[CameraKeyframe] = []

    for i in range(num_frames):
        # Global t ∈ [0, 1]
        global_t = i / max(num_frames - 1, 1)
        eased_t = ease_fn(global_t)

        # Map to segment
        seg_f = eased_t * n_segments
        seg_idx = min(int(seg_f), n_segments - 1)
        local_t = seg_f - seg_idx

        # Catmull-Rom for position (seg_idx maps to pos_ext[seg_idx+1])
        p0 = pos_ext[seg_idx]
        p1 = pos_ext[seg_idx + 1]
        p2 = pos_ext[seg_idx + 2]
        p3 = pos_ext[seg_idx + 3]
        pos = _catmull_rom(p0, p1, p2, p3, local_t)

        # Catmull-Rom for focal point
        f0 = foc_ext[seg_idx]
        f1 = foc_ext[seg_idx + 1]
        f2 = foc_ext[seg_idx + 2]
        f3 = foc_ext[seg_idx + 3]
        foc = _catmull_rom(f0, f1, f2, f3, local_t)

        # Linear interpolation for view up (slerp would be better but overkill here)
        up_a = ups[seg_idx]
        up_b = ups[min(seg_idx + 1, len(ups) - 1)]
        up = up_a + (up_b - up_a) * local_t
        up_norm = np.linalg.norm(up)
        if up_norm > 1e-8:
            up = up / up_norm

        pos_t: tuple[float, float, float] = (float(pos[0]), float(pos[1]), float(pos[2]))
        foc_t: tuple[float, float, float] = (float(foc[0]), float(foc[1]), float(foc[2]))
        up_t: tuple[float, float, float] = (float(up[0]), float(up[1]), float(up[2]))
        result.append(CameraKeyframe(
            position=pos_t,
            focal_point=foc_t,
            view_up=up_t,
            t=global_t,
        ))

    return result


# ---------------------------------------------------------------------------
# Preset paths
# ---------------------------------------------------------------------------

def orbit_path(
    center: tuple[float, float, float],
    radius: float,
    elevation_deg: float = 30.0,
    start_azimuth_deg: float = 0.0,
    end_azimuth_deg: float = 360.0,
    num_keyframes: int = 8,
    easing: str = "ease_in_out",
) -> CameraPath:
    """Create a circular orbit camera path around a center point.

    Args:
        center: Point to orbit around.
        radius: Distance from center.
        elevation_deg: Camera elevation above the XY plane.
        start_azimuth_deg: Starting azimuth angle.
        end_azimuth_deg: Ending azimuth angle.
        num_keyframes: Number of keyframes in the path.
        easing: Easing function name.

    Returns:
        CameraPath with keyframes distributed along the orbit.
    """
    el = math.radians(elevation_deg)
    cos_el = math.cos(el)
    sin_el = math.sin(el)

    keyframes = []
    for i in range(num_keyframes):
        t = i / max(num_keyframes - 1, 1)
        az = math.radians(start_azimuth_deg + (end_azimuth_deg - start_azimuth_deg) * t)

        pos = (
            center[0] + radius * cos_el * math.cos(az),
            center[1] + radius * cos_el * math.sin(az),
            center[2] + radius * sin_el,
        )

        keyframes.append(CameraKeyframe(
            position=pos,
            focal_point=center,
            view_up=(0.0, 0.0, 1.0),
            t=t,
        ))

    return CameraPath(keyframes=tuple(keyframes), easing=easing)


def flythrough_path(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    focal_point: tuple[float, float, float],
    num_keyframes: int = 4,
    easing: str = "ease_in_out",
) -> CameraPath:
    """Create a straight flythrough camera path.

    Args:
        start: Starting camera position.
        end: Ending camera position.
        focal_point: Point to look at throughout the path.
        num_keyframes: Number of intermediate keyframes.
        easing: Easing function name.

    Returns:
        CameraPath from start to end.
    """
    keyframes = []
    for i in range(num_keyframes):
        t = i / max(num_keyframes - 1, 1)
        pos = _lerp_tuple(start, end, t)
        keyframes.append(CameraKeyframe(
            position=pos,
            focal_point=focal_point,
            view_up=(0.0, 0.0, 1.0),
            t=t,
        ))

    return CameraPath(keyframes=tuple(keyframes), easing=easing)
