"""VTK offscreen rendering — headless rendering with EGL/OSMesa support."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk

__all__ = [
    "RenderConfig",
    "VTKRenderer",
    "render_to_png",
]


@dataclass
class RenderConfig:
    """Configuration for a single render pass."""

    width: int = 1920
    height: int = 1080
    background: tuple[float, float, float] = (0.2, 0.2, 0.2)
    colormap: str = "cool to warm"
    scalar_range: tuple[float, float] | None = None
    log_scale: bool = False
    array_name: str | None = None
    component: int = -1  # -1 = magnitude
    representation: str = "surface"  # surface, wireframe, points
    opacity: float = 1.0
    show_scalar_bar: bool = True
    scalar_bar_title: str | None = None
    edge_visibility: bool = False
    edge_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    point_size: float = 2.0
    line_width: float = 1.0


# ---------------------------------------------------------------------------
# Render window management
# ---------------------------------------------------------------------------

_RENDER_WINDOW: vtk.vtkRenderWindow | None = None


def _get_render_window(width: int, height: int) -> vtk.vtkRenderWindow:
    """Get or create a reusable offscreen render window.

    Auto-detects EGL (GPU) vs OSMesa (CPU) based on environment.
    """
    import vtk

    global _RENDER_WINDOW  # noqa: PLW0603

    if _RENDER_WINDOW is not None:
        _RENDER_WINDOW.SetSize(width, height)
        return _RENDER_WINDOW

    # Try EGL first (GPU accelerated), fallback to offscreen
    use_egl = os.environ.get("VTK_DEFAULT_OPENGL_WINDOW", "").lower() == "vtkeglrenderwindow"

    if use_egl:
        try:
            rw = vtk.vtkEGLRenderWindow()
            rw.SetOffScreenRendering(True)
            rw.SetSize(width, height)
            _RENDER_WINDOW = rw
            return rw
        except AttributeError:
            pass

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(True)
    rw.SetSize(width, height)
    _RENDER_WINDOW = rw
    return rw


# ---------------------------------------------------------------------------
# VTKRenderer
# ---------------------------------------------------------------------------


class VTKRenderer:
    """Offscreen VTK renderer with colormap, scalar bar, and PNG output."""

    __slots__ = ("_config", "_render_window", "_renderer")

    def __init__(self, config: RenderConfig | None = None) -> None:
        self._config = config or RenderConfig()
        self._render_window: vtk.vtkRenderWindow | None = None
        self._renderer: vtk.vtkRenderer | None = None

    @property
    def config(self) -> RenderConfig:
        return self._config

    def render(
        self,
        data: vtk.vtkDataObject,
        camera_config: object | None = None,
    ) -> bytes:
        """Render a dataset to PNG bytes.

        Args:
            data: VTK dataset to render.
            camera_config: Optional CameraConfig from engine.camera.

        Returns:
            PNG image as bytes.
        """
        import vtk

        from .camera import CameraConfig, apply_camera

        rw = _get_render_window(self._config.width, self._config.height)
        self._render_window = rw

        # Clear existing renderers
        rw.GetRenderers().RemoveAllItems()

        renderer = vtk.vtkRenderer()
        renderer.SetBackground(*self._config.background)
        rw.AddRenderer(renderer)
        self._renderer = renderer

        # Resolve data — handle multiblock by extracting first leaf
        render_data = _resolve_renderable(data)
        if render_data is None:
            # Empty dataset, return blank image
            rw.Render()
            return _capture_png(rw)

        # Find array and association
        array_name, association = _resolve_array(render_data, self._config.array_name)

        # Build mapper
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(render_data)

        if array_name is not None:
            scalar_range = self._config.scalar_range
            if scalar_range is None:
                scalar_range = _get_scalar_range(render_data, array_name, association, self._config.component)

            mapper.SetScalarVisibility(True)
            if association == "cell":
                mapper.SetScalarModeToUseCellFieldData()
            else:
                mapper.SetScalarModeToUsePointFieldData()
            mapper.SelectColorArray(array_name)

            if self._config.component >= 0:
                mapper.ColorByArrayComponent(array_name, self._config.component)
            else:
                mapper.GetLookupTable().SetVectorModeToMagnitude()

            # Build LUT from colormaps module
            from .colormaps import build_lut

            lut = build_lut(
                self._config.colormap,
                scalar_range=scalar_range,
                log_scale=self._config.log_scale,
            )
            mapper.SetLookupTable(lut)
            mapper.SetScalarRange(*scalar_range)
        else:
            mapper.SetScalarVisibility(False)

        # Build actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        prop = actor.GetProperty()
        _apply_representation(prop, self._config)

        renderer.AddActor(actor)

        # Scalar bar
        if self._config.show_scalar_bar and array_name is not None:
            bar = _build_scalar_bar(mapper, self._config, array_name)
            renderer.AddActor2D(bar)

        # Camera
        if camera_config is not None and isinstance(camera_config, CameraConfig):
            apply_camera(renderer, camera_config)
        else:
            renderer.ResetCamera()
            renderer.ResetCameraClippingRange()

        rw.Render()
        return _capture_png(rw)

    def render_multiple(
        self,
        datasets: list[tuple[vtk.vtkDataObject, RenderConfig | None]],
        camera_config: object | None = None,
    ) -> bytes:
        """Render multiple datasets overlaid in a single image.

        Args:
            datasets: List of (data, optional_config) tuples.
            camera_config: Optional CameraConfig for the combined scene.

        Returns:
            PNG image as bytes.
        """
        import vtk

        from .camera import CameraConfig, apply_camera

        rw = _get_render_window(self._config.width, self._config.height)
        self._render_window = rw
        rw.GetRenderers().RemoveAllItems()

        renderer = vtk.vtkRenderer()
        renderer.SetBackground(*self._config.background)
        rw.AddRenderer(renderer)
        self._renderer = renderer

        for data, cfg in datasets:
            cfg = cfg or self._config
            render_data = _resolve_renderable(data)
            if render_data is None:
                continue

            array_name, association = _resolve_array(render_data, cfg.array_name)

            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputData(render_data)

            if array_name is not None:
                scalar_range = cfg.scalar_range
                if scalar_range is None:
                    scalar_range = _get_scalar_range(render_data, array_name, association, cfg.component)

                mapper.SetScalarVisibility(True)
                if association == "cell":
                    mapper.SetScalarModeToUseCellFieldData()
                else:
                    mapper.SetScalarModeToUsePointFieldData()
                mapper.SelectColorArray(array_name)

                from .colormaps import build_lut

                lut = build_lut(cfg.colormap, scalar_range=scalar_range, log_scale=cfg.log_scale)
                mapper.SetLookupTable(lut)
                mapper.SetScalarRange(*scalar_range)
            else:
                mapper.SetScalarVisibility(False)

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            _apply_representation(actor.GetProperty(), cfg)
            renderer.AddActor(actor)

        if camera_config is not None and isinstance(camera_config, CameraConfig):
            apply_camera(renderer, camera_config)
        else:
            renderer.ResetCamera()
            renderer.ResetCameraClippingRange()

        rw.Render()
        return _capture_png(rw)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_renderable(data: vtk.vtkDataObject) -> vtk.vtkDataSet | None:
    """Extract a renderable vtkDataSet from any VTK data object."""
    import vtk

    if isinstance(data, vtk.vtkDataSet):
        return data

    if isinstance(data, vtk.vtkMultiBlockDataSet):
        # Flatten: use vtkCompositeDataGeometryFilter for multiblock
        geom = vtk.vtkCompositeDataGeometryFilter()
        geom.SetInputData(data)
        geom.Update()
        return geom.GetOutput()

    return None


def _resolve_array(
    data: vtk.vtkDataSet,
    requested_name: str | None,
) -> tuple[str | None, str]:
    """Find the array to color by, auto-detecting association.

    Returns:
        (array_name, association) where association is "point" or "cell".
        array_name may be None if no arrays are available.
    """
    if requested_name is not None:
        # Check point data first
        pd = data.GetPointData()
        if pd and pd.GetArray(requested_name) is not None:
            return requested_name, "point"
        # Check cell data
        cd = data.GetCellData()
        if cd and cd.GetArray(requested_name) is not None:
            return requested_name, "cell"
        # Not found, return None
        return None, "point"

    # Auto-detect: first point array, then first cell array
    pd = data.GetPointData()
    if pd and pd.GetNumberOfArrays() > 0:
        name = pd.GetArrayName(0)
        if name:
            return name, "point"

    cd = data.GetCellData()
    if cd and cd.GetNumberOfArrays() > 0:
        name = cd.GetArrayName(0)
        if name:
            return name, "cell"

    return None, "point"


def _get_scalar_range(
    data: vtk.vtkDataSet,
    array_name: str,
    association: str,
    component: int,
) -> tuple[float, float]:
    """Get the scalar range of an array."""
    attrs = data.GetPointData() if association == "point" else data.GetCellData()
    arr = attrs.GetArray(array_name) if attrs else None

    if arr is None:
        return (0.0, 1.0)

    if component >= 0 and component < arr.GetNumberOfComponents():
        lo, hi = arr.GetRange(component)
    elif arr.GetNumberOfComponents() > 1:
        # Magnitude range
        lo, hi = arr.GetRange(-1)
    else:
        lo, hi = arr.GetRange(0)

    # Avoid zero-range
    if abs(hi - lo) < 1e-30:
        hi = lo + 1.0

    return (lo, hi)


def _apply_representation(prop: vtk.vtkProperty, config: RenderConfig) -> None:
    """Apply representation settings to an actor property."""
    rep_map = {
        "surface": 2,  # VTK_SURFACE
        "wireframe": 1,  # VTK_WIREFRAME
        "points": 0,  # VTK_POINTS
    }
    prop.SetRepresentation(rep_map.get(config.representation, 2))
    prop.SetOpacity(config.opacity)
    prop.SetPointSize(config.point_size)
    prop.SetLineWidth(config.line_width)

    if config.edge_visibility:
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(*config.edge_color)
    else:
        prop.EdgeVisibilityOff()


def _build_scalar_bar(
    mapper: vtk.vtkMapper,
    config: RenderConfig,
    array_name: str,
) -> vtk.vtkScalarBarActor:
    """Build a scalar bar actor."""
    import vtk

    bar = vtk.vtkScalarBarActor()
    bar.SetLookupTable(mapper.GetLookupTable())
    bar.SetTitle(config.scalar_bar_title or array_name)
    bar.SetNumberOfLabels(5)
    bar.SetMaximumWidthInPixels(120)
    bar.SetMaximumHeightInPixels(config.height // 2)

    # Auto text color: white on dark backgrounds, black on light
    bg_lum = 0.299 * config.background[0] + 0.587 * config.background[1] + 0.114 * config.background[2]
    text_color = (1.0, 1.0, 1.0) if bg_lum < 0.5 else (0.0, 0.0, 0.0)

    title_prop = bar.GetTitleTextProperty()
    title_prop.SetColor(*text_color)
    title_prop.SetFontSize(14)
    title_prop.BoldOn()
    title_prop.ItalicOff()
    title_prop.SetShadow(False)

    label_prop = bar.GetLabelTextProperty()
    label_prop.SetColor(*text_color)
    label_prop.SetFontSize(12)
    label_prop.BoldOff()
    label_prop.ItalicOff()
    label_prop.SetShadow(False)

    return bar


def _capture_png(rw: vtk.vtkRenderWindow) -> bytes:
    """Capture render window to PNG bytes (no temp file)."""
    import vtk

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGBA()
    w2i.ReadFrontBufferOff()
    w2i.Update()

    writer = vtk.vtkPNGWriter()
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.WriteToMemoryOn()
    writer.Write()

    data = writer.GetResult()
    # vtkUnsignedCharArray → Python bytes
    n = data.GetNumberOfValues()
    return bytes(data.GetValue(i) for i in range(n))


# ---------------------------------------------------------------------------
# Public convenience function
# ---------------------------------------------------------------------------


def render_to_png(
    data: vtk.vtkDataObject,
    config: RenderConfig | None = None,
    camera_config: object | None = None,
) -> bytes:
    """Render a dataset to PNG bytes (convenience wrapper).

    Args:
        data: VTK dataset to render.
        config: Render configuration. Defaults to sensible values.
        camera_config: Optional CameraConfig from engine.camera.

    Returns:
        PNG image as bytes.
    """
    renderer = VTKRenderer(config)
    return renderer.render(data, camera_config)
