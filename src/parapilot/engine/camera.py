"""Camera presets and smart camera positioning for VTK renderer."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk


@dataclass
class CameraConfig:
    """Camera configuration for VTK renderer."""

    position: tuple[float, float, float]
    focal_point: tuple[float, float, float]
    view_up: tuple[float, float, float]
    parallel_projection: bool = False
    parallel_scale: float | None = None
    zoom: float = 1.0


# ---------------------------------------------------------------------------
# Preset definitions
# Each preset returns (direction, view_up) relative to center.
# direction is where the camera looks FROM (normalized offset from center).
# ---------------------------------------------------------------------------

_PRESETS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "isometric": ((1.0, 1.0, 1.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "back": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
}


def preset_camera(
    preset: str,
    bounds: tuple[float, float, float, float, float, float],
    zoom: float = 1.0,
    orthographic: bool = False,
) -> CameraConfig:
    """Build a CameraConfig from a named preset and dataset bounds.

    Args:
        preset: One of 'isometric', 'top', 'front', 'right', 'left', 'back', 'bottom'.
        bounds: (xmin, xmax, ymin, ymax, zmin, zmax) from dataset.
        zoom: Zoom factor (>1 = closer).
        orthographic: Use parallel projection.
    """
    direction, view_up = _PRESETS.get(preset, _PRESETS["isometric"])

    cx = (bounds[0] + bounds[1]) / 2.0
    cy = (bounds[2] + bounds[3]) / 2.0
    cz = (bounds[4] + bounds[5]) / 2.0
    center = (cx, cy, cz)

    dx = bounds[1] - bounds[0]
    dy = bounds[3] - bounds[2]
    dz = bounds[5] - bounds[4]
    diag = sqrt(dx * dx + dy * dy + dz * dz)
    if diag < 1e-10:
        diag = 1.0

    # Place camera at 2x diagonal distance along direction
    distance = diag * 2.0 / zoom
    mag = sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2)
    if mag < 1e-10:
        mag = 1.0
    nd = (direction[0] / mag, direction[1] / mag, direction[2] / mag)

    position = (
        cx + nd[0] * distance,
        cy + nd[1] * distance,
        cz + nd[2] * distance,
    )

    parallel_scale = diag / 2.0 / zoom if orthographic else None

    return CameraConfig(
        position=position,
        focal_point=center,
        view_up=view_up,
        parallel_projection=orthographic,
        parallel_scale=parallel_scale,
        zoom=zoom,
    )


def custom_camera(
    position: tuple[float, float, float],
    focal_point: tuple[float, float, float] | None = None,
    view_up: tuple[float, float, float] | None = None,
    bounds: tuple[float, float, float, float, float, float] | None = None,
    zoom: float = 1.0,
    orthographic: bool = False,
) -> CameraConfig:
    """Build a CameraConfig from explicit camera parameters."""
    if focal_point is None:
        if bounds is not None:
            focal_point = (
                (bounds[0] + bounds[1]) / 2.0,
                (bounds[2] + bounds[3]) / 2.0,
                (bounds[4] + bounds[5]) / 2.0,
            )
        else:
            focal_point = (0.0, 0.0, 0.0)

    if view_up is None:
        view_up = (0.0, 0.0, 1.0)

    parallel_scale = None
    if orthographic and bounds is not None:
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        diag = sqrt(dx * dx + dy * dy + dz * dz)
        parallel_scale = diag / 2.0 / zoom

    return CameraConfig(
        position=position,
        focal_point=focal_point,
        view_up=view_up,
        parallel_projection=orthographic,
        parallel_scale=parallel_scale,
        zoom=zoom,
    )


def apply_camera(renderer: "vtk.vtkRenderer", config: CameraConfig) -> None:
    """Apply a CameraConfig to a VTK renderer."""
    camera = renderer.GetActiveCamera()
    camera.SetPosition(*config.position)
    camera.SetFocalPoint(*config.focal_point)
    camera.SetViewUp(*config.view_up)

    if config.parallel_projection:
        camera.SetParallelProjection(True)
        if config.parallel_scale is not None:
            camera.SetParallelScale(config.parallel_scale)
    else:
        camera.SetParallelProjection(False)

    renderer.ResetCameraClippingRange()
