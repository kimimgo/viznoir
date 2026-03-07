"""Cinematic lighting system — 3-point lighting and presets for VTK renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk


@dataclass(frozen=True)
class LightDef:
    """Definition of a single light source."""

    type: str  # "directional", "positional", "ambient"
    position: tuple[float, float, float] = (0.0, 0.0, 1.0)
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    cone_angle: float = 0.0  # for spot lights
    shadow: bool = False


@dataclass(frozen=True)
class LightingPreset:
    """A named lighting configuration with multiple lights."""

    name: str
    lights: tuple[LightDef, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Built-in presets
# ---------------------------------------------------------------------------

LIGHTING_PRESETS: dict[str, LightingPreset] = {
    # 3-point cinematic (warm key, cool fill, neutral rim)
    "cinematic": LightingPreset(
        "cinematic",
        (
            LightDef("directional", (1.0, 1.0, 2.0), (1.0, 0.98, 0.95), 1.0, 0, True),
            LightDef("directional", (-1.0, 0.0, 1.0), (0.7, 0.8, 1.0), 0.4, 0, False),
            LightDef("directional", (0.0, -1.0, 0.5), (1.0, 1.0, 1.0), 0.3, 0, False),
        ),
    ),
    # High contrast single key
    "dramatic": LightingPreset(
        "dramatic",
        (
            LightDef("directional", (1.0, 0.5, 2.0), (1.0, 0.95, 0.9), 1.2, 0, True),
            LightDef("ambient", (0.0, 0.0, 0.0), (0.15, 0.15, 0.2), 0.1, 0, False),
        ),
    ),
    # Even, soft illumination
    "studio": LightingPreset(
        "studio",
        (
            LightDef("directional", (0.0, 0.0, 1.0), (1.0, 1.0, 1.0), 0.8, 0, False),
            LightDef("directional", (1.0, 1.0, 0.5), (1.0, 1.0, 1.0), 0.5, 0, False),
            LightDef("directional", (-1.0, -1.0, 0.5), (1.0, 1.0, 1.0), 0.3, 0, False),
            LightDef("ambient", (0.0, 0.0, 0.0), (0.3, 0.3, 0.3), 0.2, 0, False),
        ),
    ),
    # Clean and bright for papers
    "publication": LightingPreset(
        "publication",
        (
            LightDef("directional", (0.0, 0.0, 1.0), (1.0, 1.0, 1.0), 0.7, 0, False),
            LightDef("ambient", (0.0, 0.0, 0.0), (0.5, 0.5, 0.5), 0.3, 0, False),
        ),
    ),
    # Outdoor-like: strong directional + ambient sky
    "outdoor": LightingPreset(
        "outdoor",
        (
            LightDef("directional", (1.0, 0.5, 3.0), (1.0, 0.97, 0.92), 1.0, 0, True),
            LightDef("ambient", (0.0, 0.0, 0.0), (0.6, 0.7, 0.9), 0.25, 0, False),
        ),
    ),
}


def apply_lighting(renderer: vtk.vtkRenderer, preset_name: str) -> None:
    """Apply a lighting preset to a VTK renderer.

    Removes all existing lights and disables VTK's automatic light creation.

    Args:
        renderer: VTK renderer to configure.
        preset_name: One of the preset names (cinematic, dramatic, studio, publication, outdoor).

    Raises:
        KeyError: If preset_name is not found.
    """
    import vtk

    preset = LIGHTING_PRESETS[preset_name]

    renderer.RemoveAllLights()
    renderer.AutomaticLightCreationOff()

    for ldef in preset.lights:
        light = vtk.vtkLight()

        if ldef.type == "ambient":
            light.SetLightTypeToHeadlight()
            light.SetAmbientColor(*ldef.color)
        elif ldef.type == "positional":
            light.SetLightTypeToSceneLight()
            light.SetPositional(True)
            light.SetPosition(*ldef.position)
            if ldef.cone_angle > 0:
                light.SetConeAngle(ldef.cone_angle)
        else:  # directional
            light.SetLightTypeToSceneLight()
            light.SetPosition(*ldef.position)
            light.SetFocalPoint(0.0, 0.0, 0.0)

        light.SetColor(*ldef.color)
        light.SetIntensity(ldef.intensity)

        if ldef.shadow:
            light.SwitchOn()

        renderer.AddLight(light)


def get_preset_names() -> list[str]:
    """Return list of available lighting preset names."""
    return list(LIGHTING_PRESETS.keys())
