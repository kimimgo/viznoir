"""PBR material presets for cinematic scientific visualization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk


@dataclass(frozen=True)
class MaterialPreset:
    """PBR material definition."""

    name: str
    metallic: float = 0.0
    roughness: float = 0.5
    color: tuple[float, float, float] | None = None  # None = use colormap
    opacity: float = 1.0


MATERIAL_PRESETS: dict[str, MaterialPreset] = {
    # Metals
    "brushed_metal": MaterialPreset("brushed_metal", 0.9, 0.4, (0.8, 0.8, 0.85)),
    "polished_steel": MaterialPreset("polished_steel", 1.0, 0.1, (0.9, 0.9, 0.92)),
    "aluminum": MaterialPreset("aluminum", 0.9, 0.3, (0.91, 0.92, 0.92)),
    "copper": MaterialPreset("copper", 0.9, 0.35, (0.95, 0.64, 0.54)),
    # Non-metals
    "glass": MaterialPreset("glass", 0.0, 0.0, (0.9, 0.95, 1.0), 0.3),
    "ceramic": MaterialPreset("ceramic", 0.0, 0.3, (0.95, 0.95, 0.9)),
    "skin": MaterialPreset("skin", 0.0, 0.6, (0.9, 0.7, 0.6)),
    "plastic": MaterialPreset("plastic", 0.0, 0.4, (0.8, 0.8, 0.85)),
    # Scientific visualization
    "fluid_surface": MaterialPreset("fluid_surface", 0.1, 0.2, (0.3, 0.6, 0.9)),
    "matte_vis": MaterialPreset("matte_vis", 0.0, 0.8),  # colormap-driven
    "glossy_vis": MaterialPreset("glossy_vis", 0.1, 0.3),  # colormap-driven
    "transparent_vis": MaterialPreset("transparent_vis", 0.0, 0.2, None, 0.5),
}


def apply_material(actor: vtk.vtkActor, preset_name: str) -> None:
    """Apply a PBR material preset to a VTK actor.

    Args:
        actor: VTK actor to configure.
        preset_name: Name of the material preset.

    Raises:
        KeyError: If preset_name is not found.
    """
    preset = MATERIAL_PRESETS[preset_name]
    prop = actor.GetProperty()

    prop.SetInterpolationToPBR()
    prop.SetMetallic(preset.metallic)
    prop.SetRoughness(preset.roughness)

    if preset.color is not None:
        prop.SetColor(*preset.color)

    if preset.opacity < 1.0:
        prop.SetOpacity(preset.opacity)


def get_preset_names() -> list[str]:
    """Return list of available material preset names."""
    return list(MATERIAL_PRESETS.keys())
