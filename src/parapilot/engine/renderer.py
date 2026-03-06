"""VTK offscreen rendering — headless rendering with EGL/OSMesa support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from parapilot.logging import get_logger

if TYPE_CHECKING:
    import vtk

__all__ = [
    "RenderConfig",
    "VTKRenderer",
    "render_to_png",
    "cleanup",
]

logger = get_logger("renderer")


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
    representation: str = "surface"  # surface, wireframe, points, volume
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
_RENDER_COUNT: int = 0


def _get_render_window(width: int, height: int) -> vtk.vtkRenderWindow:
    """Get or create a reusable offscreen render window.

    Uses vtkRenderWindow() which respects VTK_DEFAULT_OPENGL_WINDOW env var
    to select EGL (GPU) or OSMesa (CPU) backend via VTK's factory mechanism.
    Direct vtkEGLRenderWindow() construction causes SIGSEGV in pip-installed VTK.

    Regenerates the window every 100 renders to prevent GPU memory leaks.
    """
    import vtk

    global _RENDER_WINDOW, _RENDER_COUNT  # noqa: PLW0603

    _RENDER_COUNT += 1
    if _RENDER_COUNT % 100 == 0:
        logger.info("render window: regenerating after %d renders", _RENDER_COUNT)
        _RENDER_WINDOW = None

    if _RENDER_WINDOW is not None:
        _RENDER_WINDOW.SetSize(width, height)
        return _RENDER_WINDOW

    logger.debug("render window: creating new %dx%d", width, height)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(True)
    rw.SetSize(width, height)
    _RENDER_WINDOW = rw
    return rw


def cleanup() -> None:
    """Explicitly release the render window and GPU memory."""
    global _RENDER_WINDOW, _RENDER_COUNT  # noqa: PLW0603

    if _RENDER_WINDOW is not None:
        _RENDER_WINDOW.Finalize()
        logger.info("render window: released after %d renders", _RENDER_COUNT)
    _RENDER_WINDOW = None
    _RENDER_COUNT = 0


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

        if self._config.representation == "volume":
            # Volume rendering path
            self._render_volume(renderer, render_data, array_name, association)
        else:
            # Surface/wireframe/points rendering path
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
                renderer.AddViewProp(bar)

        # Camera
        if camera_config is not None and isinstance(camera_config, CameraConfig):
            apply_camera(renderer, camera_config)
        else:
            renderer.ResetCamera()
            renderer.ResetCameraClippingRange()

        rw.Render()
        return _capture_png(rw)

    def _render_volume(
        self,
        renderer: vtk.vtkRenderer,
        data: vtk.vtkDataSet,
        array_name: str | None,
        association: str,
    ) -> None:
        """Add a volume actor to the renderer using vtkSmartVolumeMapper."""
        import vtk

        from .colormaps import build_lut

        # Volume rendering requires vtkImageData; convert if needed
        image_data = data
        if not isinstance(data, vtk.vtkImageData):
            # Try resampling to regular grid
            resample = vtk.vtkResampleToImage()
            resample.SetInputDataObject(data)
            resample.SetSamplingDimensions(128, 128, 128)
            resample.Update()
            image_data = resample.GetOutput()

        # Set active scalars
        if array_name is not None:
            pd = image_data.GetPointData()
            if pd.GetArray(array_name) is not None:
                pd.SetActiveScalars(array_name)

        # Scalar range
        scalar_range = self._config.scalar_range
        if scalar_range is None and array_name is not None:
            scalar_range = _get_scalar_range(image_data, array_name, "point", self._config.component)
        if scalar_range is None:
            scalar_range = (0.0, 1.0)

        lo, hi = scalar_range

        # Build color transfer function from colormap
        ctf = build_lut(
            self._config.colormap,
            scalar_range=scalar_range,
            log_scale=self._config.log_scale,
        )
        # build_lut returns vtkColorTransferFunction — use directly

        # Opacity transfer function — ramp from transparent to opaque
        otf = vtk.vtkPiecewiseFunction()
        otf.AddPoint(lo, 0.0)
        otf.AddPoint(lo + (hi - lo) * 0.2, 0.0)
        otf.AddPoint(lo + (hi - lo) * 0.4, 0.05)
        otf.AddPoint(hi, self._config.opacity * 0.5)

        # Volume property
        vol_prop = vtk.vtkVolumeProperty()
        vol_prop.SetColor(ctf)
        vol_prop.SetScalarOpacity(otf)
        vol_prop.ShadeOn()
        vol_prop.SetInterpolationTypeToLinear()
        vol_prop.SetAmbient(0.2)
        vol_prop.SetDiffuse(0.7)
        vol_prop.SetSpecular(0.3)

        # Volume mapper
        mapper = vtk.vtkSmartVolumeMapper()
        mapper.SetInputData(image_data)

        # Volume actor
        volume = vtk.vtkVolume()
        volume.SetMapper(mapper)
        volume.SetProperty(vol_prop)

        renderer.AddVolume(volume)

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
        if data.GetNumberOfPoints() == 0:
            return None
        return data

    if isinstance(data, vtk.vtkMultiBlockDataSet):
        # Flatten: use vtkCompositeDataGeometryFilter for multiblock
        geom = vtk.vtkCompositeDataGeometryFilter()
        geom.SetInputData(data)
        geom.Update()
        result = geom.GetOutput()
        if result.GetNumberOfPoints() == 0:
            return None
        return result

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
        # Not found — log available fields with "did you mean?" suggestion
        import difflib

        available: list[str] = []
        if pd:
            for i in range(pd.GetNumberOfArrays()):
                name = pd.GetArrayName(i)
                if name:
                    available.append(name)
        if cd:
            for i in range(cd.GetNumberOfArrays()):
                name = cd.GetArrayName(i)
                if name:
                    available.append(name)
        if available:
            close = difflib.get_close_matches(requested_name, available, n=3)
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            logger.warning("Field '%s' not found. Available: %s.%s", requested_name, available, hint)
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
    from vtkmodules.util.numpy_support import vtk_to_numpy

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()

    writer = vtk.vtkPNGWriter()
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.WriteToMemoryOn()
    writer.Write()

    data = writer.GetResult()
    return vtk_to_numpy(data).tobytes()  # type: ignore[no-untyped-call,no-any-return]


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
