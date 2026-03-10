"""VTK filter chain — apply slice, clip, contour, streamlines, and more."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from viznoir.errors import EmptyOutputError

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
    "smooth_mesh",
    "probe_point",
    "clean_polydata",
    "shrink",
    "tube",
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
    origin: tuple[float, float, float] | None = None,
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> vtk.vtkDataObject:
    """Slice dataset with a plane.

    Args:
        data: Input VTK dataset.
        origin: Point on the plane (x, y, z). None = dataset center.
        normal: Plane normal direction (nx, ny, nz).

    Returns:
        Sliced polydata.
    """
    import vtk

    # Auto-compute origin from dataset center if not specified
    if origin is None and hasattr(data, "GetBounds"):
        b = data.GetBounds()
        origin = ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2)
    elif origin is None:
        origin = (0.0, 0.0, 0.0)

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
    origin: tuple[float, float, float] | None = None,
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
    inside_out: bool = False,
    invert: bool | None = None,
) -> vtk.vtkDataObject:
    """Clip dataset with a plane.

    Args:
        data: Input VTK dataset.
        origin: Point on the plane (x, y, z). None = dataset center.
        normal: Plane normal direction (nx, ny, nz).
        inside_out: If True, keep the half-space behind the plane.
        invert: Alias for inside_out (registry compatibility).

    Returns:
        Clipped unstructured grid.
    """
    import vtk

    if invert is not None:
        inside_out = invert

    # Auto-compute origin from dataset center if not specified
    if origin is None and hasattr(data, "GetBounds"):
        b = data.GetBounds()
        origin = ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2)
    elif origin is None:
        origin = (0.0, 0.0, 0.0)

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
    array_name: str | None = None,
    values: list[float] | None = None,
    field: str | None = None,
    association: str = "POINTS",
    isovalues: list[float] | None = None,
) -> vtk.vtkDataObject:
    """Generate contour surfaces at specified values.

    Args:
        data: Input VTK dataset.
        array_name: Name of the scalar array to contour.
        values: List of contour values.
        field: Alias for array_name (registry compatibility).
        association: Array association (POINTS or CELLS).
        isovalues: Alias for values (registry compatibility).

    Returns:
        Contour polydata.
    """
    import vtk

    name = field or array_name
    if name is None:
        raise ValueError("contour requires 'field' or 'array_name'")
    vals = isovalues or values
    if not vals:
        raise ValueError("contour requires 'isovalues' or 'values'")

    assoc = (
        vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS
        if association.upper() == "CELLS"
        else vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS
    )

    # Get data range for diagnostics
    pd = data.GetPointData() if association.upper() == "POINTS" else data.GetCellData()
    arr = pd.GetArray(name) if pd else None
    if arr is None:
        msg = f"Array '{name}' not found in {association} data"
        raise ValueError(msg)

    data_range = arr.GetRange(0)

    filt = vtk.vtkContourFilter()
    filt.SetInputData(data)
    filt.SetInputArrayToProcess(0, 0, 0, assoc, name)

    for i, val in enumerate(vals):
        filt.SetValue(i, val)

    filt.Update()
    output = filt.GetOutput()

    if output.GetNumberOfCells() == 0:
        msg = (
            f"Contour produced empty output: no cells at isovalues {vals}. "
            f"Array '{name}' range is [{data_range[0]:.6g}, {data_range[1]:.6g}]. "
            f"Choose isovalues within this range."
        )
        raise EmptyOutputError(msg)

    return output


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
    array_name: str | None = None,
    lower: float | None = None,
    upper: float | None = None,
    component: int = 0,
    field: str | None = None,
    method: str | None = None,
) -> vtk.vtkDataObject:
    """Threshold dataset by scalar range.

    Args:
        data: Input VTK dataset.
        array_name: Name of the scalar array.
        lower: Lower bound (None = no lower bound).
        upper: Upper bound (None = no upper bound).
        component: Array component index for multi-component arrays.
        field: Alias for array_name (registry compatibility).
        method: Ignored (kept for registry compatibility).

    Returns:
        Thresholded unstructured grid.
    """
    _ = method
    array_name = field or array_name
    if array_name is None:
        raise ValueError("threshold requires 'field' or 'array_name'")
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
    array_name: str | None = None,
    seed_point1: tuple[float, float, float] | None = None,
    seed_point2: tuple[float, float, float] | None = None,
    num_seeds: int = 25,
    max_length: float = 0.0,
    integration_direction: str = "both",
    # Registry aliases (from ScriptCompiler)
    vectors: list[str] | None = None,
    seed_type: str | None = None,
    seed_resolution: int | None = None,
    direction: str | None = None,
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
        vectors: Registry alias — ['POINTS', 'field_name'], extracts array_name.
        seed_type: Registry alias — ignored (always 'Line').
        seed_resolution: Registry alias for num_seeds.
        direction: Registry alias for integration_direction.

    Returns:
        Streamline polydata.
    """
    import vtk

    # Resolve registry aliases
    if vectors is not None and array_name is None:
        array_name = vectors[-1] if isinstance(vectors, list) else vectors
    if array_name is None:
        raise ValueError("streamlines requires array_name or vectors parameter")
    if seed_resolution is not None and num_seeds == 25:
        num_seeds = seed_resolution
    if direction is not None and integration_direction == "both":
        integration_direction = direction.lower()

    # Auto-compute seed points from data bounds if not specified
    if seed_point1 is None or seed_point2 is None:
        if hasattr(data, "GetBounds"):
            b = data.GetBounds()
            cx = (b[0] + b[1]) / 2
            cy = (b[2] + b[3]) / 2
            cz = (b[4] + b[5]) / 2
            dx = b[1] - b[0]
            dy = b[3] - b[2]
            dz = b[5] - b[4]
            # Place seed line along longest axis, centered
            if dx >= dy and dx >= dz:
                seed_point1 = seed_point1 or (b[0] + dx * 0.2, cy, cz)
                seed_point2 = seed_point2 or (b[1] - dx * 0.2, cy, cz)
            elif dy >= dz:
                seed_point1 = seed_point1 or (cx, b[2] + dy * 0.2, cz)
                seed_point2 = seed_point2 or (cx, b[3] - dy * 0.2, cz)
            else:
                seed_point1 = seed_point1 or (cx, cy, b[4] + dz * 0.2)
                seed_point2 = seed_point2 or (cx, cy, b[5] - dz * 0.2)
        else:
            seed_point1 = seed_point1 or (0, 0, 0)
            seed_point2 = seed_point2 or (1, 0, 0)

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
    array_name: str | None = None,
    result_name: str = "Gradient",
    compute_vorticity: bool = False,
    compute_qcriterion: bool = False,
    field: str | None = None,
) -> vtk.vtkDataObject:
    """Compute gradient (and optionally vorticity/Q-criterion) of a scalar/vector field.

    Args:
        data: Input VTK dataset.
        array_name: Name of the input array.
        result_name: Name for the gradient output array.
        compute_vorticity: Also compute vorticity (for vector inputs).
        compute_qcriterion: Also compute Q-criterion (for vector inputs).
        field: Alias for array_name (registry compatibility).

    Returns:
        Dataset with gradient array added.
    """
    import vtk

    array_name = field or array_name
    if array_name is None:
        raise ValueError("gradient requires 'field' or 'array_name'")

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


def smooth_mesh(
    data: vtk.vtkDataObject,
    iterations: int = 20,
    relaxation_factor: float = 0.1,
) -> vtk.vtkDataObject:
    """Smooth mesh using Laplacian smoothing.

    Args:
        data: Input VTK dataset.
        iterations: Number of smoothing iterations.
        relaxation_factor: Relaxation factor per iteration.

    Returns:
        Smoothed polydata.
    """
    import vtk

    # Convert to polydata if needed
    if not isinstance(data, vtk.vtkPolyData):
        surf = vtk.vtkDataSetSurfaceFilter()
        surf.SetInputData(data)
        surf.Update()
        data = surf.GetOutput()

    filt = vtk.vtkSmoothPolyDataFilter()
    filt.SetInputData(data)
    filt.SetNumberOfIterations(iterations)
    filt.SetRelaxationFactor(relaxation_factor)
    filt.Update()
    return filt.GetOutput()


def probe_point(
    data: vtk.vtkDataObject,
    point: tuple[float, float, float],
) -> vtk.vtkDataObject:
    """Probe dataset at a single point.

    Args:
        data: Input VTK dataset.
        point: Sample location (x, y, z).

    Returns:
        Single-point polydata with interpolated field values.
    """
    import vtk

    pts = vtk.vtkPoints()
    pts.InsertNextPoint(*point)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)

    probe = vtk.vtkProbeFilter()
    probe.SetInputData(pd)
    probe.SetSourceData(data)
    probe.Update()
    return probe.GetOutput()


def clean_polydata(
    data: vtk.vtkDataObject,
    tolerance: float = 0.0,
) -> vtk.vtkDataObject:
    """Remove duplicate points and degenerate cells.

    Args:
        data: Input VTK dataset.
        tolerance: Merge tolerance. 0 = exact duplicates only.

    Returns:
        Cleaned polydata.
    """
    import vtk

    # Convert to polydata if needed
    if not isinstance(data, vtk.vtkPolyData):
        surf = vtk.vtkDataSetSurfaceFilter()
        surf.SetInputData(data)
        surf.Update()
        data = surf.GetOutput()

    filt = vtk.vtkCleanPolyData()
    filt.SetInputData(data)
    if tolerance > 0:
        filt.SetTolerance(tolerance)
    filt.Update()
    return filt.GetOutput()


def shrink(
    data: vtk.vtkDataObject,
    shrink_factor: float = 0.5,
) -> vtk.vtkDataObject:
    """Shrink cells for exploded view visualization.

    Args:
        data: Input VTK dataset.
        shrink_factor: Factor between 0 (full shrink) and 1 (no shrink).

    Returns:
        Dataset with shrunk cells.
    """
    import vtk

    filt = vtk.vtkShrinkFilter()
    filt.SetInputData(data)
    filt.SetShrinkFactor(shrink_factor)
    filt.Update()
    return filt.GetOutput()


def tube(
    data: vtk.vtkDataObject,
    radius: float = 0.01,
    sides: int = 6,
) -> vtk.vtkDataObject:
    """Add tube thickness to polylines (e.g., streamlines).

    Args:
        data: Input polydata with lines.
        radius: Tube radius.
        sides: Number of sides for tube cross-section.

    Returns:
        Polydata with tube geometry.
    """
    import vtk

    filt = vtk.vtkTubeFilter()
    filt.SetInputData(data)
    filt.SetRadius(radius)
    filt.SetNumberOfSides(sides)
    filt.Update()
    return filt.GetOutput()


# ---------------------------------------------------------------------------
# Pipeline composition
# ---------------------------------------------------------------------------


# Map of filter name → function (for declarative pipeline specs)
def _normalize_filter_name(name: str) -> str:
    """Normalize filter name: CamelCase → snake_case, then lowercase."""
    import re

    # CamelCase → snake_case: insert _ before uppercase letters
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    return s.lower()


_FILTER_REGISTRY: dict[str, object] = {
    "slice": slice_plane,
    "clip": clip_plane,
    "contour": contour,
    "isosurface": isosurface,
    "threshold": threshold,
    "streamlines": streamlines,
    "stream_tracer": streamlines,
    "calculator": calculator,
    "gradient": gradient,
    "integrate": integrate_variables,
    "integrate_variables": integrate_variables,
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
    "smooth_mesh": smooth_mesh,
    "smooth": smooth_mesh,
    "probe_point": probe_point,
    "probe": probe_point,
    "clean_polydata": clean_polydata,
    "clean_poly_data": clean_polydata,
    "clean": clean_polydata,
    "shrink": shrink,
    "tube": tube,
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
    func = _FILTER_REGISTRY.get(_normalize_filter_name(filter_name))
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
