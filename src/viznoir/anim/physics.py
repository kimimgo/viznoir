"""Physics-driven animation presets — every effect has a physical reason.

Design principle: **"Why this animation?"** must have a physics answer.

- Orbit alone is NOT informative — it shows surface from different angles
  but reveals no internal structure or causal mechanism.
- Each preset encodes a specific physical analysis technique:
  - ``layer_reveal``: Transfer function sweep separates density layers (CT, MRI)
  - ``streamline_growth``: Lagrangian advection IS the physics of flow
  - ``clip_sweep``: Cross-section reveals internal gradient along a direction
  - ``iso_sweep``: Isosurface threshold maps 3D scalar field structure
  - ``threshold_reveal``: Progressive opacity reveals feature hierarchy
  - ``warp_oscillation``: Deformation exaggeration shows structural response
  - ``light_orbit``: Oblique illumination is a standard geomorphology technique

Usage::

    from viznoir.anim.physics import clip_sweep, FrameConfig
    from viznoir.engine.renderer import _get_render_window, _capture_png

    config = FrameConfig(width=1280, height=720, fps=24, duration=8.0)
    frames = clip_sweep(
        dataset=ds,
        renderer_setup=my_setup_fn,
        axis="x",
        config=config,
        output_dir="/tmp/frames",
    )
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from viznoir.anim.easing import smooth

if TYPE_CHECKING:
    import vtk


__all__ = [
    "FrameConfig",
    "layer_reveal",
    "streamline_growth",
    "clip_sweep",
    "iso_sweep",
    "threshold_reveal",
    "warp_oscillation",
    "light_orbit",
]


@dataclass
class FrameConfig:
    """Configuration for animation frame rendering."""

    width: int = 1280
    height: int = 720
    fps: int = 24
    duration: float = 8.0
    background: tuple[float, float, float] = (0.02, 0.02, 0.04)

    @property
    def n_frames(self) -> int:
        return int(self.fps * self.duration)


# ---------------------------------------------------------------------------
# Core render loop (shared by all presets)
# ---------------------------------------------------------------------------


def _render_loop(
    config: FrameConfig,
    setup_fn: Callable[..., tuple[vtk.vtkRenderWindow, vtk.vtkRenderer]],
    frame_fn: Callable[[vtk.vtkRenderer, vtk.vtkRenderWindow, float, int], None],
    output_dir: str,
) -> list[str]:
    """Internal: run the frame-by-frame render loop.

    Args:
        config: Frame configuration.
        setup_fn: Creates render window + renderer. Returns (rw, ren).
        frame_fn: Called per frame with (renderer, render_window, t, frame_idx).
            ``t`` is normalized time [0, 1].
        output_dir: Directory to write frame PNGs.

    Returns:
        List of frame file paths.
    """
    from viznoir.engine.renderer import _capture_png, _get_render_window

    rw = _get_render_window(config.width, config.height)
    rw.GetRenderers().RemoveAllItems()
    ren_result = setup_fn(rw)

    # setup_fn can return (rw, ren) or just ren
    if isinstance(ren_result, tuple):
        _, ren = ren_result
    else:
        ren = ren_result

    os.makedirs(output_dir, exist_ok=True)
    paths: list[str] = []
    n = config.n_frames

    for i in range(n):
        t = i / max(n - 1, 1)
        frame_fn(ren, rw, t, i)
        ren.ResetCameraClippingRange()
        rw.Render()
        png = _capture_png(rw)
        path = os.path.join(output_dir, f"frame_{i:04d}.png")
        with open(path, "wb") as f:
            f.write(png)
        paths.append(path)

    return paths


# ---------------------------------------------------------------------------
# Preset: Layer Reveal (TF opacity sweep)
# ---------------------------------------------------------------------------


def layer_reveal(
    dataset: vtk.vtkImageData,
    layers: list[tuple[float, float, str]],
    colormap: str = "bone",
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/layer_reveal",
) -> list[str]:
    """Reveal density layers by sweeping transfer function opacity.

    **Physics**: In volumetric imaging (CT, MRI), distinct tissue types
    occupy different intensity ranges. Sweeping the opacity threshold
    from high to low progressively reveals deeper structures — this is
    the standard radiological reading workflow.

    Args:
        dataset: VTK ImageData with scalar field.
        layers: List of (threshold_low, threshold_high, label) tuples,
            ordered from outermost (shown last) to innermost (shown first).
        colormap: Colormap name for color transfer function.
        config: Frame config (default 1280x720, 8s, 24fps).
        output_dir: Output directory for frame PNGs.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk

    from viznoir.engine.colormaps import build_lut

    cfg = config or FrameConfig()

    scalar_range = dataset.GetScalarRange()
    n_layers = len(layers)

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        rw.AddRenderer(ren)

        lut = build_lut(colormap, scalar_range=scalar_range)
        ctf = _vtk.vtkColorTransferFunction()
        for i in range(256):
            v = scalar_range[0] + (scalar_range[1] - scalar_range[0]) * i / 255
            c = [0.0, 0.0, 0.0]
            lut.GetColor(v, c)
            ctf.AddRGBPoint(v, c[0], c[1], c[2])

        vol_mapper = _vtk.vtkSmartVolumeMapper()
        vol_mapper.SetInputData(dataset)

        vol_prop = _vtk.vtkVolumeProperty()
        vol_prop.ShadeOn()
        vol_prop.SetAmbient(0.2)
        vol_prop.SetDiffuse(0.8)
        vol_prop.SetColor(ctf)

        volume = _vtk.vtkVolume()
        volume.SetMapper(vol_mapper)
        volume.SetProperty(vol_prop)
        ren.AddVolume(volume)

        ren.ResetCamera()

        # Store mutable state on renderer for frame_fn access
        ren._viznoir_vol_prop = vol_prop  # type: ignore[attr-defined]
        ren._viznoir_layers = layers  # type: ignore[attr-defined]

        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        vol_prop = ren._viznoir_vol_prop  # type: ignore[attr-defined]
        lyrs = ren._viznoir_layers  # type: ignore[attr-defined]

        # Determine which layers are visible at time t
        # Layer i appears at t = i / n_layers
        otf = _vtk.vtkPiecewiseFunction()
        otf.AddPoint(scalar_range[0], 0.0)

        for i, (lo, hi, _label) in enumerate(lyrs):
            appear_t = (n_layers - 1 - i) / max(n_layers, 1)
            if t >= appear_t:
                alpha = min(1.0, (t - appear_t) / 0.15)
                opacity = smooth(alpha) * 0.5
                otf.AddPoint(lo, 0.0)
                otf.AddPoint(lo + (hi - lo) * 0.1, opacity * 0.3)
                otf.AddPoint(hi, opacity)

        vol_prop.SetScalarOpacity(otf)

    return _render_loop(cfg, setup, frame, output_dir)


# ---------------------------------------------------------------------------
# Preset: Clip Sweep
# ---------------------------------------------------------------------------


def clip_sweep(
    dataset: vtk.vtkDataSet,
    axis: str = "x",
    colormap: str = "inferno",
    array_name: str | None = None,
    scalar_range: tuple[float, float] | None = None,
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/clip_sweep",
    bounce: bool = True,
) -> list[str]:
    """Sweep a clip plane along an axis, revealing internal structure.

    **Physics**: Cross-sectioning along a physical gradient direction
    (e.g., streamwise for pressure, depth for seismic) reveals how
    quantities change spatially. The clip direction should follow the
    dominant physical transport direction.

    Args:
        dataset: Any VTK dataset.
        axis: Sweep axis — "x", "y", or "z".
        colormap: Colormap name.
        array_name: Scalar array to color by (None = active scalars).
        scalar_range: Color map range (None = auto from data).
        config: Frame config.
        output_dir: Output directory.
        bounce: If True, sweep forward then back. If False, one-way.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk

    from viznoir.engine.colormaps import build_lut

    cfg = config or FrameConfig()
    bounds = dataset.GetBounds()
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]
    normal = [0.0, 0.0, 0.0]
    normal[axis_idx] = -1.0

    bmin = bounds[axis_idx * 2]
    bmax = bounds[axis_idx * 2 + 1]

    if scalar_range is None:
        if array_name:
            arr = dataset.GetPointData().GetArray(array_name) or dataset.GetCellData().GetArray(array_name)
            if arr:
                scalar_range = arr.GetRange()
            else:
                scalar_range = dataset.GetScalarRange()
        else:
            scalar_range = dataset.GetScalarRange()

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        rw.AddRenderer(ren)

        lut = build_lut(colormap, scalar_range=scalar_range)

        # Ghost shell
        surface = _vtk.vtkDataSetSurfaceFilter()
        surface.SetInputData(dataset)
        surface.Update()
        ghost_m = _vtk.vtkPolyDataMapper()
        ghost_m.SetInputData(surface.GetOutput())
        if array_name:
            ghost_m.SetScalarModeToUsePointFieldData()
            ghost_m.SelectColorArray(array_name)
        ghost_m.SetScalarRange(*scalar_range)
        ghost_m.SetLookupTable(lut)
        ghost_a = _vtk.vtkActor()
        ghost_a.SetMapper(ghost_m)
        ghost_a.GetProperty().SetOpacity(0.12)
        ren.AddActor(ghost_a)

        # Clip plane
        clip_plane = _vtk.vtkPlane()
        clip_plane.SetNormal(*normal)

        clipper = _vtk.vtkTableBasedClipDataSet()
        clipper.SetInputData(dataset)
        clipper.SetClipFunction(clip_plane)
        clipper.SetInsideOut(True)

        clip_surface = _vtk.vtkDataSetSurfaceFilter()
        clip_surface.SetInputConnection(clipper.GetOutputPort())

        clip_m = _vtk.vtkPolyDataMapper()
        clip_m.SetInputConnection(clip_surface.GetOutputPort())
        if array_name:
            clip_m.SetScalarModeToUsePointFieldData()
            clip_m.SelectColorArray(array_name)
        clip_m.SetScalarRange(*scalar_range)
        clip_m.SetLookupTable(lut)

        clip_a = _vtk.vtkActor()
        clip_a.SetMapper(clip_m)
        ren.AddActor(clip_a)

        ren.ResetCamera()
        cam = ren.GetActiveCamera()
        cam.Azimuth(30)
        cam.Elevation(25)

        ren._viznoir_clip_plane = clip_plane  # type: ignore[attr-defined]
        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        clip_plane = ren._viznoir_clip_plane  # type: ignore[attr-defined]

        if bounce:
            sweep_t = smooth(t * 2) if t < 0.5 else smooth((1.0 - t) * 2)
        else:
            sweep_t = smooth(t)

        origin = [0.0, 0.0, 0.0]
        origin[axis_idx] = bmin + sweep_t * (bmax - bmin)
        clip_plane.SetOrigin(*origin)

        ren.GetActiveCamera().Azimuth(0.15)

    return _render_loop(cfg, setup, frame, output_dir)


# ---------------------------------------------------------------------------
# Preset: Iso Sweep
# ---------------------------------------------------------------------------


def iso_sweep(
    dataset: vtk.vtkImageData,
    iso_range: tuple[float, float] | None = None,
    colormap: str | None = None,
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/iso_sweep",
) -> list[str]:
    """Sweep isovalue from high to low, revealing nested scalar structures.

    **Physics**: Isosurfaces are level sets of a scalar field. Sweeping
    from high to low reveals the field's topological structure layer by
    layer — e.g., electron density orbitals or temperature contours.
    The color transition (red→blue) encodes the scalar magnitude.

    Args:
        dataset: VTK ImageData with scalar field.
        iso_range: (high, low) isovalue range. Default: (90%, 5%) of max.
        colormap: Optional colormap name.
        config: Frame config.
        output_dir: Output directory.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk
    from vtk.util.numpy_support import vtk_to_numpy

    cfg = config or FrameConfig()
    arr = vtk_to_numpy(dataset.GetPointData().GetScalars())
    vmax = float(arr.max())

    if iso_range is None:
        iso_range = (vmax * 0.7, vmax * 0.05)

    iso_high, iso_low = iso_range

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        rw.AddRenderer(ren)

        contour = _vtk.vtkContourFilter()
        contour.SetInputData(dataset)
        contour.SetValue(0, iso_high)

        mapper = _vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(contour.GetOutputPort())
        mapper.ScalarVisibilityOff()

        actor = _vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetOpacity(0.7)
        actor.GetProperty().SetSpecular(0.4)
        actor.GetProperty().SetDiffuse(0.7)
        ren.AddActor(actor)

        ren.ResetCamera()
        ren.GetActiveCamera().Zoom(0.9)

        ren._viznoir_contour = contour  # type: ignore[attr-defined]
        ren._viznoir_actor = actor  # type: ignore[attr-defined]
        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        contour = ren._viznoir_contour  # type: ignore[attr-defined]
        actor = ren._viznoir_actor  # type: ignore[attr-defined]

        # Bounce: high → low → high
        sweep_t = smooth(t * 2) if t < 0.5 else smooth((1.0 - t) * 2)
        iso_val = iso_high - sweep_t * (iso_high - iso_low)
        iso_val = max(iso_val, iso_low)
        contour.SetValue(0, iso_val)

        # Color encodes scalar magnitude
        r = 0.9 - sweep_t * 0.6
        g = 0.2 + sweep_t * 0.4
        b = 0.1 + sweep_t * 0.9
        actor.GetProperty().SetColor(r, g, b)
        actor.GetProperty().SetOpacity(0.8 - sweep_t * 0.3)

        ren.GetActiveCamera().Azimuth(0.3)

    return _render_loop(cfg, setup, frame, output_dir)


# ---------------------------------------------------------------------------
# Preset: Threshold Reveal (volume opacity ramp)
# ---------------------------------------------------------------------------


def threshold_reveal(
    dataset: vtk.vtkImageData,
    scalar_range: tuple[float, float] | None = None,
    threshold_range: tuple[float, float] | None = None,
    colormap: str = "inferno",
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/threshold_reveal",
) -> list[str]:
    """Progressively reveal volume features by lowering opacity threshold.

    **Physics**: In volume rendering, the opacity transfer function defines
    which scalar values are visible. Starting with only the highest values
    (e.g., hottest temperature, brightest vessels) and progressively
    lowering the threshold reveals the feature hierarchy — from extreme
    events to the full field structure.

    Args:
        dataset: VTK ImageData.
        scalar_range: Data range for colormap.
        threshold_range: (start_high, end_low) opacity threshold sweep range.
        colormap: Colormap name.
        config: Frame config.
        output_dir: Output directory.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk

    from viznoir.engine.colormaps import build_lut

    cfg = config or FrameConfig()

    if scalar_range is None:
        scalar_range = dataset.GetScalarRange()

    smin, smax = scalar_range
    if threshold_range is None:
        threshold_range = (smax * 0.85, smin + (smax - smin) * 0.15)

    thresh_high, thresh_low = threshold_range

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        rw.AddRenderer(ren)

        lut = build_lut(colormap, scalar_range=scalar_range)
        ctf = _vtk.vtkColorTransferFunction()
        for i in range(256):
            v = smin + (smax - smin) * i / 255
            c = [0.0, 0.0, 0.0]
            lut.GetColor(v, c)
            ctf.AddRGBPoint(v, c[0], c[1], c[2])

        vol_prop = _vtk.vtkVolumeProperty()
        vol_prop.ShadeOn()
        vol_prop.SetAmbient(0.3)
        vol_prop.SetDiffuse(0.7)
        vol_prop.SetColor(ctf)

        vol_mapper = _vtk.vtkSmartVolumeMapper()
        vol_mapper.SetInputData(dataset)

        volume = _vtk.vtkVolume()
        volume.SetMapper(vol_mapper)
        volume.SetProperty(vol_prop)
        ren.AddVolume(volume)

        ren.ResetCamera()
        ren.GetActiveCamera().Elevation(15)
        ren.GetActiveCamera().Zoom(2.0)

        ren._viznoir_vol_prop = vol_prop  # type: ignore[attr-defined]
        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        vol_prop = ren._viznoir_vol_prop  # type: ignore[attr-defined]

        # First half: reveal, second half: orbit at full
        if t < 0.5:
            sweep_t = smooth(t * 2)
            threshold = thresh_high - sweep_t * (thresh_high - thresh_low)
        else:
            threshold = thresh_low

        otf = _vtk.vtkPiecewiseFunction()
        otf.AddPoint(smin, 0.0)
        otf.AddPoint(threshold * 0.85, 0.0)
        otf.AddPoint(threshold, 0.08)
        mid = smin + (smax - smin) * 0.5
        otf.AddPoint(mid, 0.2)
        otf.AddPoint(smax * 0.8, 0.5)
        otf.AddPoint(smax, 0.85)
        vol_prop.SetScalarOpacity(otf)

        if t > 0.3:
            ren.GetActiveCamera().Azimuth(360.0 / cfg.n_frames * 1.3)

    return _render_loop(cfg, setup, frame, output_dir)


# ---------------------------------------------------------------------------
# Preset: Warp Oscillation
# ---------------------------------------------------------------------------


def warp_oscillation(
    dataset: vtk.vtkDataSet,
    displacement_field: str = "Displacement",
    stress_field: str | None = "VonMises",
    max_scale: float = 25.0,
    n_cycles: int = 2,
    colormap: str = "jet",
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/warp_oscillation",
) -> list[str]:
    """Oscillate deformation scale to visualize structural response.

    **Physics**: Structural FEA results have small real displacements.
    Exaggerating the warp factor reveals the deformation mode shape.
    Oscillation shows the dynamic response pattern. The undeformed
    wireframe ghost provides reference for measuring deflection.

    Args:
        dataset: VTK dataset with displacement vector field.
        displacement_field: Name of displacement vector array.
        stress_field: Scalar array for coloring (e.g., VonMises). None = no coloring.
        max_scale: Maximum warp scale factor.
        n_cycles: Number of oscillation cycles.
        colormap: Colormap for stress coloring.
        config: Frame config.
        output_dir: Output directory.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk

    from viznoir.engine.colormaps import build_lut

    cfg = config or FrameConfig()

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        rw.AddRenderer(ren)

        # Warped surface
        warp = _vtk.vtkWarpVector()
        warp.SetInputData(dataset)
        warp.SetInputArrayToProcess(
            0,
            0,
            0,
            _vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS,
            displacement_field,
        )
        warp.SetScaleFactor(0)

        surface = _vtk.vtkDataSetSurfaceFilter()
        surface.SetInputConnection(warp.GetOutputPort())

        mapper = _vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(surface.GetOutputPort())

        if stress_field:
            arr = dataset.GetPointData().GetArray(stress_field)
            if arr:
                mapper.SetScalarModeToUsePointFieldData()
                mapper.SelectColorArray(stress_field)
                sr = arr.GetRange()
                mapper.SetScalarRange(*sr)
                lut = build_lut(colormap, scalar_range=sr)
                mapper.SetLookupTable(lut)

        actor = _vtk.vtkActor()
        actor.SetMapper(mapper)
        ren.AddActor(actor)

        # Ghost wireframe
        ghost_s = _vtk.vtkDataSetSurfaceFilter()
        ghost_s.SetInputData(dataset)
        ghost_s.Update()
        ghost_m = _vtk.vtkPolyDataMapper()
        ghost_m.SetInputData(ghost_s.GetOutput())
        ghost_m.ScalarVisibilityOff()
        ghost_a = _vtk.vtkActor()
        ghost_a.SetMapper(ghost_m)
        ghost_a.GetProperty().SetRepresentationToWireframe()
        ghost_a.GetProperty().SetColor(0.3, 0.35, 0.4)
        ghost_a.GetProperty().SetOpacity(0.25)
        ren.AddActor(ghost_a)

        ren.ResetCamera()
        cam = ren.GetActiveCamera()
        cam.Azimuth(30)
        cam.Elevation(20)
        cam.Zoom(0.8)

        ren._viznoir_warp = warp  # type: ignore[attr-defined]
        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        warp = ren._viznoir_warp  # type: ignore[attr-defined]
        osc = math.sin(t * 2 * math.pi * n_cycles) * 0.5 + 0.5
        warp.SetScaleFactor(osc * max_scale)
        warp.Update()
        ren.GetActiveCamera().Azimuth(0.1)

    return _render_loop(cfg, setup, frame, output_dir)


# ---------------------------------------------------------------------------
# Preset: Light Orbit (geomorphology oblique illumination)
# ---------------------------------------------------------------------------


def light_orbit(
    dataset: vtk.vtkPolyData,
    color: tuple[float, float, float] = (0.5, 0.47, 0.42),
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/light_orbit",
) -> list[str]:
    """Orbit a key light around a surface to reveal topology via shadows.

    **Physics**: In geomorphology and planetary science, oblique illumination
    at varying azimuths is a standard technique for revealing surface
    roughness, ridges, and craters. The changing shadow pattern encodes
    height information that a single viewpoint cannot capture.

    Args:
        dataset: VTK PolyData (mesh surface).
        color: Surface base color.
        config: Frame config.
        output_dir: Output directory.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk

    cfg = config or FrameConfig()

    bounds = dataset.GetBounds()
    cx = (bounds[0] + bounds[1]) / 2
    cy = (bounds[2] + bounds[3]) / 2
    cz = (bounds[4] + bounds[5]) / 2
    radius = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]) / 2

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        ren.AutomaticLightCreationOff()
        rw.AddRenderer(ren)

        mapper = _vtk.vtkPolyDataMapper()
        mapper.SetInputData(dataset)
        actor = _vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetSpecular(0.12)
        actor.GetProperty().SetDiffuse(0.8)
        actor.GetProperty().SetAmbient(0.15)
        ren.AddActor(actor)

        # Key light (will orbit)
        key = _vtk.vtkLight()
        key.SetFocalPoint(cx, cy, cz)
        key.SetIntensity(1.3)
        key.SetColor(1.0, 0.95, 0.87)
        ren.AddLight(key)

        # Constant fill
        fill = _vtk.vtkLight()
        fill.SetPosition(cx, cy, cz - radius * 4)
        fill.SetFocalPoint(cx, cy, cz)
        fill.SetIntensity(0.25)
        fill.SetColor(0.5, 0.55, 0.7)
        ren.AddLight(fill)

        ren.ResetCamera()
        ren.GetActiveCamera().Elevation(20)
        ren.GetActiveCamera().Zoom(1.3)

        ren._viznoir_key_light = key  # type: ignore[attr-defined]
        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        key = ren._viznoir_key_light  # type: ignore[attr-defined]
        angle = t * 360
        lx = cx + radius * 4 * math.cos(math.radians(angle + 45))
        ly = cy + radius * 4 * math.sin(math.radians(angle + 45))
        lz = cz + radius * 2.5
        key.SetPosition(lx, ly, lz)

        # Camera orbits slower than light
        ren.GetActiveCamera().Azimuth(360.0 / cfg.n_frames * 0.7)

    return _render_loop(cfg, setup, frame, output_dir)


# ---------------------------------------------------------------------------
# Preset: Streamline Growth
# ---------------------------------------------------------------------------


def streamline_growth(
    dataset: vtk.vtkDataSet,
    vector_field: str = "Velocity",
    color_field: str | None = None,
    seed_center: tuple[float, float, float] | None = None,
    seed_radius: float | None = None,
    n_seeds: int = 30,
    colormap: str = "inferno",
    config: FrameConfig | None = None,
    output_dir: str = "/tmp/viznoir-anim/streamline_growth",
) -> list[str]:
    """Grow streamlines from seeds, showing Lagrangian advection over time.

    **Physics**: Streamline integration is Lagrangian particle tracing —
    each line follows the velocity field from its seed point. Growing the
    maximum propagation length over time shows how the flow field develops
    spatially: entrainment, acceleration, mixing, and decay become visible
    as the lines extend further from their source.

    Args:
        dataset: VTK dataset with vector field.
        vector_field: Name of velocity vector array.
        color_field: Scalar array for line coloring (None = use vector_field magnitude).
        seed_center: Center of seed point distribution (None = auto from bounds).
        seed_radius: Radius of seed distribution (None = auto).
        n_seeds: Number of seed points.
        colormap: Colormap for line coloring.
        config: Frame config.
        output_dir: Output directory.

    Returns:
        List of frame file paths.
    """
    import vtk as _vtk

    from viznoir.engine.colormaps import build_lut

    cfg = config or FrameConfig()
    bounds = dataset.GetBounds()
    domain_len = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])

    if seed_center is None:
        seed_center = (bounds[0], (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2)
    if seed_radius is None:
        seed_radius = min(bounds[3] - bounds[2], bounds[5] - bounds[4]) * 0.3

    dataset.GetPointData().SetActiveVectors(vector_field)

    def setup(rw: _vtk.vtkRenderWindow) -> _vtk.vtkRenderer:
        ren = _vtk.vtkRenderer()
        ren.SetBackground(*cfg.background)
        rw.AddRenderer(ren)

        seeds = _vtk.vtkLineSource()
        seeds.SetPoint1(seed_center[0], seed_center[1] - seed_radius, seed_center[2])
        seeds.SetPoint2(seed_center[0], seed_center[1] + seed_radius, seed_center[2])
        seeds.SetResolution(n_seeds)
        seeds.Update()

        streamer = _vtk.vtkStreamTracer()
        streamer.SetInputData(dataset)
        streamer.SetSourceConnection(seeds.GetOutputPort())
        streamer.SetIntegrationDirectionToForward()
        streamer.SetIntegratorTypeToRungeKutta45()
        streamer.SetMaximumPropagation(domain_len * 0.05)

        tube = _vtk.vtkTubeFilter()
        tube.SetInputConnection(streamer.GetOutputPort())
        tube.SetRadius(domain_len * 0.003)
        tube.SetNumberOfSides(8)

        mapper = _vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tube.GetOutputPort())

        c_field = color_field or vector_field
        arr = dataset.GetPointData().GetArray(c_field)
        if arr:
            mapper.SetScalarModeToUsePointFieldData()
            mapper.SelectColorArray(c_field)
            sr = arr.GetRange()
            mapper.SetScalarRange(*sr)
            lut = build_lut(colormap, scalar_range=sr)
            mapper.SetLookupTable(lut)

        actor = _vtk.vtkActor()
        actor.SetMapper(mapper)
        ren.AddActor(actor)

        # Domain outline
        outline = _vtk.vtkOutlineFilter()
        outline.SetInputData(dataset)
        outline.Update()
        om = _vtk.vtkPolyDataMapper()
        om.SetInputData(outline.GetOutput())
        oa = _vtk.vtkActor()
        oa.SetMapper(om)
        oa.GetProperty().SetColor(0.2, 0.2, 0.25)
        ren.AddActor(oa)

        ren.ResetCamera()
        ren.GetActiveCamera().Elevation(20)
        ren.GetActiveCamera().Zoom(1.4)

        ren._viznoir_streamer = streamer  # type: ignore[attr-defined]
        ren._viznoir_max_prop = domain_len * 3  # type: ignore[attr-defined]
        return ren

    def frame(ren: _vtk.vtkRenderer, rw: _vtk.vtkRenderWindow, t: float, idx: int) -> None:
        streamer = ren._viznoir_streamer  # type: ignore[attr-defined]
        max_prop = ren._viznoir_max_prop  # type: ignore[attr-defined]

        # Growth: 5% → 100%
        prop = max_prop * (0.05 + 0.95 * smooth(min(t * 1.5, 1.0)))
        streamer.SetMaximumPropagation(prop)
        streamer.Update()

        if t > 0.3:
            ren.GetActiveCamera().Azimuth(0.08)

    return _render_loop(cfg, setup, frame, output_dir)
