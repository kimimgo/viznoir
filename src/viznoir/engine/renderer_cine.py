"""Cinematic VTK renderer — combines lighting, SSAO, FXAA, scene, auto-camera.

Extends the base VTKRenderer with cinematic rendering features:
- 3-point lighting presets (cinematic, dramatic, studio, publication, outdoor)
- SSAO (contact shadows) + FXAA (anti-aliasing)
- Gradient backgrounds with ground plane
- PCA-based auto-camera framing
- PBR material support (metallic/roughness)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import TYPE_CHECKING, Any

from viznoir.engine.renderer import (
    RenderConfig,
    VTKRenderer,
    _apply_representation,
    _build_scalar_bar,
    _capture_png,
    _get_render_window,
    _get_scalar_range,
    _resolve_array,
    _resolve_renderable,
)
from viznoir.logging import get_logger

if TYPE_CHECKING:
    import vtk

logger = get_logger("renderer_cine")


@dataclass
class CinematicConfig:
    """Extended render configuration for cinematic output."""

    # Base render settings
    render: RenderConfig = field(default_factory=lambda: RenderConfig(
        background=(0.1, 0.1, 0.12),
    ))

    # Lighting
    lighting_preset: str | None = "cinematic"

    # Post-processing
    ssao: bool = True
    fxaa: bool = True

    # Background
    background_preset: str | None = "dark_gradient"
    ground_plane: bool = False
    ground_color: tuple[float, float, float] = (0.3, 0.3, 0.3)
    ground_opacity: float = 0.5

    # Camera
    auto_camera: bool = True
    fill_ratio: float = 0.75
    azimuth: float | None = None
    elevation: float | None = None

    # PBR material
    metallic: float = 0.0
    roughness: float = 0.5

    # Quality preset name (for convenience)
    quality: str = "standard"  # draft, standard, cinematic, ultra, publication


# Quality presets
QUALITY_PRESETS: dict[str, dict[str, Any]] = {
    "draft": {
        "width": 960, "height": 540,
        "ssao": False, "fxaa": False,
    },
    "standard": {
        "width": 1920, "height": 1080,
        "ssao": True, "fxaa": True,
    },
    "cinematic": {
        "width": 1920, "height": 1080,
        "ssao": True, "fxaa": True,
        "lighting_preset": "cinematic",
        "background_preset": "dark_gradient",
        "ground_plane": True,
    },
    "ultra": {
        "width": 3840, "height": 2160,
        "ssao": True, "fxaa": True,
        "lighting_preset": "cinematic",
        "background_preset": "dark_gradient",
        "ground_plane": True,
    },
    "publication": {
        "width": 2400, "height": 1800,
        "ssao": False, "fxaa": True,
        "lighting_preset": "publication",
        "background_preset": "publication",
        "ground_plane": False,
    },
}


def cinematic_render(
    data: vtk.vtkDataObject,
    config: CinematicConfig | None = None,
) -> bytes:
    """Render a dataset with cinematic quality settings.

    This is the main entry point for cinematic rendering. Combines:
    - Auto-camera positioning (PCA shape analysis + frustum fitting)
    - 3-point lighting
    - SSAO + FXAA post-processing
    - Gradient background + optional ground plane
    - PBR material properties

    Args:
        data: VTK dataset to render.
        config: Cinematic configuration. Uses "standard" quality if None.

    Returns:
        PNG image as bytes.
    """
    import vtk

    from .camera import apply_camera
    from .camera_auto import auto_camera
    from .lighting import apply_lighting
    from .postfx import apply_fxaa, apply_ssao
    from .scene import add_ground_plane, apply_background

    if config is None:
        config = CinematicConfig()

    # Apply quality preset overrides
    _apply_quality_preset(config)

    rc = config.render
    rw = _get_render_window(rc.width, rc.height)
    rw.GetRenderers().RemoveAllItems()

    renderer = vtk.vtkRenderer()
    rw.AddRenderer(renderer)

    # 1. Background
    if config.background_preset:
        apply_background(renderer, config.background_preset)
    else:
        renderer.SetBackground(*rc.background)

    # 2. Resolve data
    render_data = _resolve_renderable(data)
    if render_data is None:
        rw.Render()
        return _capture_png(rw)

    # 3. Mapper + Actor
    array_name, association = _resolve_array(render_data, rc.array_name)

    if rc.representation == "volume":
        base = VTKRenderer(rc)
        base._renderer = renderer
        base._render_volume(renderer, render_data, array_name, association)
    else:
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(render_data)

        if array_name is not None:
            scalar_range = rc.scalar_range
            if scalar_range is None:
                scalar_range = _get_scalar_range(render_data, array_name, association, rc.component)

            mapper.SetScalarVisibility(True)
            if association == "cell":
                mapper.SetScalarModeToUseCellFieldData()
            else:
                mapper.SetScalarModeToUsePointFieldData()
            mapper.SelectColorArray(array_name)

            if rc.component >= 0:
                mapper.ColorByArrayComponent(array_name, rc.component)
            else:
                mapper.GetLookupTable().SetVectorModeToMagnitude()

            from .colormaps import build_lut
            lut = build_lut(rc.colormap, scalar_range=scalar_range, log_scale=rc.log_scale)
            mapper.SetLookupTable(lut)
            mapper.SetScalarRange(*scalar_range)
        else:
            mapper.SetScalarVisibility(False)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        _apply_representation(actor.GetProperty(), rc)

        # PBR material
        if config.metallic > 0 or config.roughness != 0.5:
            prop = actor.GetProperty()
            prop.SetInterpolationToPBR()
            prop.SetMetallic(config.metallic)
            prop.SetRoughness(config.roughness)

        renderer.AddActor(actor)

        # Scalar bar
        if rc.show_scalar_bar and array_name is not None:
            bar = _build_scalar_bar(mapper, rc, array_name)
            renderer.AddViewProp(bar)

    # 4. Ground plane
    if config.ground_plane:
        bounds = render_data.GetBounds()
        add_ground_plane(
            renderer, bounds,
            color=config.ground_color,
            opacity=config.ground_opacity,
        )

    # 5. Lighting
    if config.lighting_preset:
        apply_lighting(renderer, config.lighting_preset)

    # 6. Camera (auto or default)
    if config.auto_camera:
        cam_config = auto_camera(
            render_data,
            fill_ratio=config.fill_ratio,
            aspect_ratio=rc.width / rc.height,
            azimuth=config.azimuth,
            elevation=config.elevation,
        )
        apply_camera(renderer, cam_config)
    else:
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()

    # 7. Post-processing (must be after scene setup)
    scene_size = _scene_diagonal(render_data)
    if config.ssao:
        apply_ssao(renderer, scene_size)
    if config.fxaa:
        apply_fxaa(renderer)

    rw.Render()
    logger.info(
        "cinematic render: %dx%d, lighting=%s, ssao=%s, fxaa=%s",
        rc.width, rc.height, config.lighting_preset, config.ssao, config.fxaa,
    )
    return _capture_png(rw)


def _scene_diagonal(data: vtk.vtkDataSet) -> float:
    """Calculate scene bounding box diagonal."""
    bounds = data.GetBounds()
    dx = bounds[1] - bounds[0]
    dy = bounds[3] - bounds[2]
    dz = bounds[5] - bounds[4]
    return sqrt(dx * dx + dy * dy + dz * dz) or 1.0


def _apply_quality_preset(config: CinematicConfig) -> None:
    """Apply quality preset values to config (only overrides defaults)."""
    preset = QUALITY_PRESETS.get(config.quality)
    if preset is None:
        return

    if "width" in preset:
        config.render.width = preset["width"]
        config.render.height = preset["height"]
    if "ssao" in preset:
        config.ssao = preset["ssao"]
    if "fxaa" in preset:
        config.fxaa = preset["fxaa"]
    if "lighting_preset" in preset:
        config.lighting_preset = preset["lighting_preset"]
    if "background_preset" in preset:
        config.background_preset = preset["background_preset"]
    if "ground_plane" in preset:
        config.ground_plane = preset["ground_plane"]
