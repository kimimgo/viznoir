"""Scene environment — background gradients, ground plane for VTK renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk


@dataclass(frozen=True)
class BackgroundPreset:
    """Background configuration."""

    name: str
    top_color: tuple[float, float, float]
    bottom_color: tuple[float, float, float]
    gradient: bool = True


BACKGROUND_PRESETS: dict[str, BackgroundPreset] = {
    "dark_gradient": BackgroundPreset("dark_gradient", (0.15, 0.15, 0.2), (0.05, 0.05, 0.08)),
    "light_gradient": BackgroundPreset("light_gradient", (1.0, 1.0, 1.0), (0.85, 0.87, 0.92)),
    "blue_gradient": BackgroundPreset("blue_gradient", (0.1, 0.15, 0.3), (0.02, 0.03, 0.08)),
    "warm_gradient": BackgroundPreset("warm_gradient", (0.2, 0.15, 0.12), (0.08, 0.05, 0.03)),
    "solid_white": BackgroundPreset("solid_white", (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), gradient=False),
    "solid_black": BackgroundPreset("solid_black", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), gradient=False),
    "publication": BackgroundPreset("publication", (1.0, 1.0, 1.0), (0.95, 0.95, 0.95)),
}


def apply_background(renderer: vtk.vtkRenderer, preset_name: str) -> None:
    """Apply a background preset to a VTK renderer.

    Args:
        renderer: VTK renderer.
        preset_name: One of the preset names.

    Raises:
        KeyError: If preset_name is not found.
    """
    preset = BACKGROUND_PRESETS[preset_name]

    if preset.gradient:
        renderer.GradientBackgroundOn()
        renderer.SetBackground(*preset.bottom_color)
        renderer.SetBackground2(*preset.top_color)
    else:
        renderer.GradientBackgroundOff()
        renderer.SetBackground(*preset.top_color)


def apply_gradient_background(
    renderer: vtk.vtkRenderer,
    top: tuple[float, float, float],
    bottom: tuple[float, float, float],
) -> None:
    """Apply a custom gradient background."""
    renderer.GradientBackgroundOn()
    renderer.SetBackground(*bottom)
    renderer.SetBackground2(*top)


def add_ground_plane(
    renderer: vtk.vtkRenderer,
    bounds: tuple[float, float, float, float, float, float],
    *,
    color: tuple[float, float, float] = (0.3, 0.3, 0.3),
    opacity: float = 0.5,
    offset_ratio: float = 0.01,
) -> None:
    """Add a ground plane below the dataset for shadow catching.

    Places a semi-transparent plane at the bottom of the bounding box.

    Args:
        renderer: VTK renderer.
        bounds: (xmin, xmax, ymin, ymax, zmin, zmax) dataset bounds.
        color: Ground plane color.
        opacity: Ground plane opacity.
        offset_ratio: How far below zmin to place the plane (as fraction of z-range).
    """
    import vtk

    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    dz = zmax - zmin
    ground_z = zmin - max(dz * offset_ratio, 0.001)

    # Extend plane beyond data bounds
    pad_x = (xmax - xmin) * 0.5
    pad_y = (ymax - ymin) * 0.5

    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(xmin - pad_x, ymin - pad_y, ground_z)
    plane.SetPoint1(xmax + pad_x, ymin - pad_y, ground_z)
    plane.SetPoint2(xmin - pad_x, ymax + pad_y, ground_z)
    plane.SetResolution(1, 1)
    plane.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(plane.GetOutput())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(opacity)
    actor.GetProperty().LightingOff()

    renderer.AddActor(actor)


def get_preset_names() -> list[str]:
    """Return list of available background preset names."""
    return list(BACKGROUND_PRESETS.keys())
