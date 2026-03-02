"""VTK filter chain — apply slice, clip, contour, streamlines, and more."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import vtk

__all__ = [
    "FilterSpec",
    "apply_filter",
    "apply_filters",
    "slice_plane",
    "clip_plane",
    "contour",
    "threshold",
    "streamlines",
    "calculator",
    "gradient",
    "integrate_variables",
    "extract_block",
    "extract_surface",
    "warp_by_vector",
    "warp_by_scalar",
    "cell_to_point",
    "point_to_cell",
    "plot_over_line",
    "glyph",
    "decimate",
    "triangulate",
    "isosurface",
]


# ---------------------------------------------------------------------------
# Filter spec — declarative filter description for pipeline composition
# ---------------------------------------------------------------------------


class FilterSpec(Protocol):
    """Protocol for filter specifications."""

    def apply(self, input_data: vtk.vtkDataObject) -> vtk.vtkDataObject: ...


# ---------------------------------------------------------------------------
# Individual filter functions
# ---------------------------------------------------------------------------


def slice_plane(
    data: vtk.vtkDataObject,
    origin: tuple[float, float, float],
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> vtk.vtkDataObject:
    """Slice dataset with a plane.

    Args:
        data: Input VTK dataset.
        origin: Point on the plane (x, y, z).
        normal: Plane normal direction (nx, ny, nz).

    Returns:
        Sliced polydata.
    """
    import vtk

    plane = vtk.vtkPlane()
    plane.SetOrigin(*origin)
    plane.SetNormal(*normal)

    cutter = vtk.vtkCutter()
    cutter.SetInputData(data)
    cutter.SetCutFunction(plane)
    cutter.Update()
    return cutter.GetOutput()


def clip_plane(
    data: vtk.vtkDataObject,
    origin: tuple[float, float, float],
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
    inside_out: bool = False,
) -> vtk.vtkDataObject:
    """Clip dataset with a plane.

    Args:
        data: Input VTK dataset.
        origin: Point on the plane (x, y, z).
        normal: Plane normal direction (nx, ny, nz).
        inside_out: If True, keep the half-space behind the plane.

    Returns:
        Clipped unstructured grid.
    """
    import vtk

    plane = vtk.vtkPlane()
    plane.SetOrigin(*origin)
    plane.SetNormal(*normal)

    clipper = vtk.vtkClipDataSet()
    clipper.SetInputData(data)
    clipper.SetClipFunction(plane)
    clipper.SetInsideOut(inside_out)
    clipper.Update()
    return clipper.GetOutput()


def contour(
    data: vtk.vtkDataObject,
    array_name: str,
    values: list[float],
) -> vtk.vtkDataObject:
    """Generate contour surfaces at specified values.

    Args:
        data: Input VTK dataset.
        array_name: Name of the scalar array to contour.
        values: List of contour values.

    Returns:
        Contour polydata.
    """
    import vtk

    filt = vtk.vtkContourFilter()
    filt.SetInputData(data)
    filt.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)

    for i, val in enumerate(values):
        filt.SetValue(i, val)

    filt.Update()
    return filt.GetOutput()


def isosurface(
    data: vtk.vtkDataObject,
    array_name: str,
    value: float,
) -> vtk.vtkDataObject:
    """Generate a single isosurface. Convenience wrapper around contour().

    Args:
        data: Input VTK dataset.
        array_name: Name of the scalar array.
        value: Isosurface value.

    Returns:
        Isosurface polydata.
    """
    return contour(data, array_name, [value])


def threshold(
    data: vtk.vtkDataObject,
    array_name: str,
    lower: float | None = None,
    upper: float | None = None,
    component: int = 0,
) -> vtk.vtkDataObject:
    """Threshold dataset by scalar range.

    Args:
        data: Input VTK dataset.
        array_name: Name of the scalar array.
        lower: Lower bound (None = no lower bound).
        upper: Upper bound (None = no upper bound).
        component: Array component index for multi-component arrays.

    Returns:
        Thresholded unstructured grid.
    """
    import vtk

    filt = vtk.vtkThreshold()
    filt.SetInputData(data)
    filt.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)
    filt.SetComponentModeToUseSelected()
    filt.SetSelectedComponent(component)

    if lower is not None and upper is not None:
        filt.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_BETWEEN)
        filt.SetLowerThreshold(lower)
        filt.SetUpperThreshold(upper)
    elif lower is not None:
        filt.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_UPPER)
        filt.SetLowerThreshold(lower)
    elif upper is not None:
        filt.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_LOWER)
        filt.SetUpperThreshold(upper)

    filt.Update()
    return filt.GetOutput()


def streamlines(
    data: vtk.vtkDataObject,
    array_name: str,
    seed_point1: tuple[float, float, float],
    seed_point2: tuple[float, float, float],
    num_seeds: int = 25,
    max_length: float = 0.0,
    integration_direction: str = "both",
) -> vtk.vtkDataObject:
    """Generate streamlines from a line source seed.

    Args:
        data: Input VTK dataset with vector data.
        array_name: Name of the vector array for integration.
        seed_point1: First endpoint of the seed line.
        seed_point2: Second endpoint of the seed line.
        num_seeds: Number of seed points along the line.
        max_length: Maximum streamline length. 0 = auto (10x dataset diagonal).
        integration_direction: "forward", "backward", or "both".

    Returns:
        Streamline polydata.
    """
    import vtk

    line = vtk.vtkLineSource()
    line.SetPoint1(*seed_point1)
    line.SetPoint2(*seed_point2)
    line.SetResolution(num_seeds)
    line.Update()

    tracer = vtk.vtkStreamTracer()
    tracer.SetInputData(data)
    tracer.SetSourceConnection(line.GetOutputPort())
    tracer.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)

    direction_map = {
        "forward": vtk.vtkStreamTracer.FORWARD,
        "backward": vtk.vtkStreamTracer.BACKWARD,
        "both": vtk.vtkStreamTracer.BOTH,
    }
    tracer.SetIntegrationDirection(direction_map.get(integration_direction, vtk.vtkStreamTracer.BOTH))
    tracer.SetIntegratorTypeToRungeKutta45()

    if max_length > 0:
        tracer.SetMaximumPropagation(max_length)
    else:
        # Auto: 10x dataset diagonal
        if hasattr(data, "GetBounds"):
            b = data.GetBounds()
            dx = b[1] - b[0]
            dy = b[3] - b[2]
            dz = b[5] - b[4]
            diag = (dx * dx + dy * dy + dz * dz) ** 0.5
            tracer.SetMaximumPropagation(diag * 10.0)
        else:
            tracer.SetMaximumPropagation(100.0)

    tracer.Update()
    return tracer.GetOutput()


def calculator(
    data: vtk.vtkDataObject,
    expression: str,
    result_name: str = "Result",
    attribute_type: str = "point",
) -> vtk.vtkDataObject:
    """Apply a calculator expression to create a new array.

    Args:
        data: Input VTK dataset.
        expression: VTK calculator expression (e.g., "mag(U)", "p/1000").
        result_name: Name for the output array.
        attribute_type: "point" or "cell".

    Returns:
        Dataset with new calculated array.
    """
    import vtk

    calc = vtk.vtkArrayCalculator()
    calc.SetInputData(data)
    calc.SetFunction(expression)
    calc.SetResultArrayName(result_name)

    if attribute_type == "cell":
        calc.SetAttributeTypeToCellData()
    else:
        calc.SetAttributeTypeToPointData()

    # Register all existing arrays as variables
    pd = data.GetPointData() if attribute_type == "point" else data.GetCellData()
    if pd is not None:
        for i in range(pd.GetNumberOfArrays()):
            name = pd.GetArrayName(i)
            if name:
                arr = pd.GetArray(i)
                if arr and arr.GetNumberOfComponents() == 1:
                    calc.AddScalarVariable(name, name, 0)
                elif arr and arr.GetNumberOfComponents() == 3:
                    calc.AddVectorVariable(name, name)

    calc.Update()
    return calc.GetOutput()


def gradient(
    data: vtk.vtkDataObject,
    array_name: str,
    result_name: str = "Gradient",
    compute_vorticity: bool = False,
    compute_qcriterion: bool = False,
) -> vtk.vtkDataObject:
    """Compute gradient (and optionally vorticity/Q-criterion) of a scalar/vector field.

    Args:
        data: Input VTK dataset.
        array_name: Name of the input array.
        result_name: Name for the gradient output array.
        compute_vorticity: Also compute vorticity (for vector inputs).
        compute_qcriterion: Also compute Q-criterion (for vector inputs).

    Returns:
        Dataset with gradient array added.
    """
    import vtk

    filt = vtk.vtkGradientFilter()
    filt.SetInputData(data)
    filt.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)
    filt.SetResultArrayName(result_name)
    filt.SetComputeVorticity(compute_vorticity)
    filt.SetComputeQCriterion(compute_qcriterion)

    if compute_vorticity:
        filt.SetVorticityArrayName("Vorticity")
    if compute_qcriterion:
        filt.SetQCriterionArrayName("QCriterion")

    filt.Update()
    return filt.GetOutput()


def integrate_variables(data: vtk.vtkDataObject) -> vtk.vtkDataObject:
    """Integrate variables over the dataset (area/volume averages).

    Args:
        data: Input VTK dataset.

    Returns:
        Single-cell dataset with integrated values.
    """
    import vtk

    filt = vtk.vtkIntegrateAttributes()
    filt.SetInputData(data)
    filt.Update()
    return filt.GetOutput()


def extract_block(
    data: vtk.vtkDataObject,
    block_index: int,
) -> vtk.vtkDataObject:
    """Extract a single block from a multiblock dataset.

    Args:
        data: Input multiblock dataset.
        block_index: Zero-based block index.

    Returns:
        The extracted block as a dataset.
    """
    import vtk

    if not isinstance(data, vtk.vtkMultiBlockDataSet):
        msg = f"Expected vtkMultiBlockDataSet, got {type(data).__name__}"
        raise TypeError(msg)

    filt = vtk.vtkExtractBlock()
    filt.SetInputData(data)
    filt.AddIndex(block_index + 1)  # vtkExtractBlock uses 1-based flat index
    filt.Update()
    return filt.GetOutput()


def extract_surface(data: vtk.vtkDataObject) -> vtk.vtkDataObject:
    """Extract the outer surface of a volumetric dataset.

    Args:
        data: Input VTK dataset (typically unstructured grid).

    Returns:
        Surface polydata.
    """
    import vtk

    filt = vtk.vtkDataSetSurfaceFilter()
    filt.SetInputData(data)
    filt.Update()
    return filt.GetOutput()


def warp_by_vector(
    data: vtk.vtkDataObject,
    array_name: str,
    scale_factor: float = 1.0,
) -> vtk.vtkDataObject:
    """Warp geometry by a vector field.

    Args:
        data: Input VTK dataset.
        array_name: Name of the vector array for displacement.
        scale_factor: Scaling factor for displacement magnitude.

    Returns:
        Warped dataset.
    """
    import vtk

    filt = vtk.vtkWarpVector()
    filt.SetInputData(data)
    filt.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)
    filt.SetScaleFactor(scale_factor)
    filt.Update()
    return filt.GetOutput()


def warp_by_scalar(
    data: vtk.vtkDataObject,
    array_name: str,
    scale_factor: float = 1.0,
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> vtk.vtkDataObject:
    """Warp geometry by a scalar field along a normal direction.

    Args:
        data: Input VTK dataset.
        array_name: Name of the scalar array.
        scale_factor: Scaling factor.
        normal: Direction of warp displacement.

    Returns:
        Warped dataset.
    """
    import vtk

    filt = vtk.vtkWarpScalar()
    filt.SetInputData(data)
    filt.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)
    filt.SetScaleFactor(scale_factor)
    filt.SetNormal(*normal)
    filt.SetUseNormal(True)
    filt.Update()
    return filt.GetOutput()


def cell_to_point(data: vtk.vtkDataObject) -> vtk.vtkDataObject:
    """Convert cell data to point data via averaging.

    Args:
        data: Input VTK dataset with cell arrays.

    Returns:
        Dataset with point arrays interpolated from cell data.
    """
    import vtk

    filt = vtk.vtkCellDataToPointData()
    filt.SetInputData(data)
    filt.Update()
    return filt.GetOutput()


def point_to_cell(data: vtk.vtkDataObject) -> vtk.vtkDataObject:
    """Convert point data to cell data via averaging.

    Args:
        data: Input VTK dataset with point arrays.

    Returns:
        Dataset with cell arrays interpolated from point data.
    """
    import vtk

    filt = vtk.vtkPointDataToCellData()
    filt.SetInputData(data)
    filt.Update()
    return filt.GetOutput()


def plot_over_line(
    data: vtk.vtkDataObject,
    point1: tuple[float, float, float],
    point2: tuple[float, float, float],
    resolution: int = 200,
) -> vtk.vtkDataObject:
    """Probe dataset along a line (for 1D plot extraction).

    Args:
        data: Input VTK dataset.
        point1: Start point of the line.
        point2: End point of the line.
        resolution: Number of sample points along the line.

    Returns:
        Polydata with probed values along the line.
    """
    import vtk

    line = vtk.vtkLineSource()
    line.SetPoint1(*point1)
    line.SetPoint2(*point2)
    line.SetResolution(resolution)
    line.Update()

    probe = vtk.vtkProbeFilter()
    probe.SetInputConnection(line.GetOutputPort())
    probe.SetSourceData(data)
    probe.Update()
    return probe.GetOutput()


def glyph(
    data: vtk.vtkDataObject,
    array_name: str,
    scale_factor: float = 1.0,
    glyph_type: str = "arrow",
    max_points: int = 5000,
) -> vtk.vtkDataObject:
    """Place glyphs (arrows, cones) oriented by a vector field.

    Args:
        data: Input VTK dataset.
        array_name: Name of the vector array for orientation.
        scale_factor: Glyph size scaling.
        glyph_type: "arrow" or "cone".
        max_points: Maximum number of glyphs (random mask if exceeded).

    Returns:
        Polydata with glyphs.
    """
    import vtk

    # Mask to limit glyph count
    num_points = data.GetNumberOfPoints() if hasattr(data, "GetNumberOfPoints") else 0
    source_data = data

    if num_points > max_points and num_points > 0:
        mask = vtk.vtkMaskPoints()
        mask.SetInputData(data)
        mask.SetMaximumNumberOfPoints(max_points)
        mask.SetRandomModeType(2)
        mask.Update()
        source_data = mask.GetOutput()

    if glyph_type == "cone":
        shape = vtk.vtkConeSource()
        shape.SetResolution(8)
    else:
        shape = vtk.vtkArrowSource()

    shape.Update()

    glyph_filter = vtk.vtkGlyph3D()
    glyph_filter.SetInputData(source_data)
    glyph_filter.SetSourceConnection(shape.GetOutputPort())
    glyph_filter.SetInputArrayToProcess(1, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, array_name)
    glyph_filter.SetVectorModeToUseVector()
    glyph_filter.SetScaleModeToScaleByVector()
    glyph_filter.SetScaleFactor(scale_factor)
    glyph_filter.OrientOn()
    glyph_filter.Update()
    return glyph_filter.GetOutput()


def decimate(
    data: vtk.vtkDataObject,
    reduction: float = 0.5,
    preserve_topology: bool = True,
) -> vtk.vtkDataObject:
    """Reduce polygon count of a polydata mesh.

    Args:
        data: Input polydata.
        reduction: Target reduction ratio (0.5 = reduce by 50%).
        preserve_topology: Prevent holes and non-manifold edges.

    Returns:
        Decimated polydata.
    """
    import vtk

    # Ensure input is polydata
    if not isinstance(data, vtk.vtkPolyData):
        surf = vtk.vtkDataSetSurfaceFilter()
        surf.SetInputData(data)
        surf.Update()
        data = surf.GetOutput()

    filt = vtk.vtkDecimatePro()
    filt.SetInputData(data)
    filt.SetTargetReduction(reduction)
    filt.SetPreserveTopology(preserve_topology)
    filt.Update()
    return filt.GetOutput()


def triangulate(data: vtk.vtkDataObject) -> vtk.vtkDataObject:
    """Convert all polygons to triangles.

    Args:
        data: Input polydata or dataset.

    Returns:
        Triangulated polydata.
    """
    import vtk

    filt = vtk.vtkTriangleFilter()
    filt.SetInputData(data)
    filt.Update()
    return filt.GetOutput()


# ---------------------------------------------------------------------------
# Pipeline composition
# ---------------------------------------------------------------------------

# Map of filter name → function (for declarative pipeline specs)
_FILTER_REGISTRY: dict[str, object] = {
    "slice": slice_plane,
    "clip": clip_plane,
    "contour": contour,
    "isosurface": isosurface,
    "threshold": threshold,
    "streamlines": streamlines,
    "calculator": calculator,
    "gradient": gradient,
    "integrate": integrate_variables,
    "extract_block": extract_block,
    "extract_surface": extract_surface,
    "warp_by_vector": warp_by_vector,
    "warp_by_scalar": warp_by_scalar,
    "cell_to_point": cell_to_point,
    "point_to_cell": point_to_cell,
    "plot_over_line": plot_over_line,
    "glyph": glyph,
    "decimate": decimate,
    "triangulate": triangulate,
}


def apply_filter(
    data: vtk.vtkDataObject,
    filter_name: str,
    **kwargs: object,
) -> vtk.vtkDataObject:
    """Apply a named filter with keyword arguments.

    Args:
        data: Input VTK dataset.
        filter_name: Filter name from registry.
        **kwargs: Arguments passed to the filter function.

    Returns:
        Filtered dataset.

    Raises:
        ValueError: If filter_name is not recognized.
    """
    func = _FILTER_REGISTRY.get(filter_name)
    if func is None:
        available = ", ".join(sorted(_FILTER_REGISTRY.keys()))
        msg = f"Unknown filter '{filter_name}'. Available: {available}"
        raise ValueError(msg)

    return func(data, **kwargs)  # type: ignore[operator]


def apply_filters(
    data: vtk.vtkDataObject,
    filters: list[tuple[str, dict[str, object]]],
) -> vtk.vtkDataObject:
    """Apply a chain of filters sequentially.

    Args:
        data: Input VTK dataset.
        filters: List of (filter_name, kwargs) tuples.

    Returns:
        Result after all filters applied.
    """
    result = data
    for filter_name, kwargs in filters:
        result = apply_filter(result, filter_name, **kwargs)
    return result


def list_filters() -> list[str]:
    """Return sorted list of available filter names."""
    return sorted(_FILTER_REGISTRY.keys())
