"""Physics-aware smart defaults — detect field type and recommend visualization settings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import sqrt
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import vtk

__all__ = [
    "PhysicsType",
    "SmartCamera",
    "SmartRepresentation",
    "VisualizationTechnique",
    "SmartDefaults",
    "detect_physics",
    "smart_defaults",
    "analyze_camera",
    "smart_representation",
    "recommend_techniques",
]


# ======================================================================
# 1. Physics type detection
# ======================================================================


@dataclass(frozen=True, slots=True)
class PhysicsType:
    """Detected physical quantity with visualization recommendations."""

    name: str
    category: str  # "scalar", "vector", "tensor"
    colormap: str
    diverging: bool
    log_scale: bool
    camera_2d: str
    camera_3d: str
    representation: str  # "surface", "surface_with_edges", "wireframe", "points"
    warp: bool
    streamlines: bool

    @property
    def is_vector(self) -> bool:
        return self.category == "vector"


_PHYSICS_PATTERNS: list[tuple[str, dict[str, Any]]] = [
    (
        r"^p$|^pressure$|^p_rgh$|^pd$",
        {
            "name": "pressure",
            "category": "scalar",
            "colormap": "coolwarm",
            "diverging": True,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^U$|^velocity$|^v$|^vel$",
        {
            "name": "velocity",
            "category": "vector",
            "colormap": "viridis",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "front",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": True,
        },
    ),
    (
        r"^T$|^temperature$|^temp$|^theta$",
        {
            "name": "temperature",
            "category": "scalar",
            "colormap": "inferno",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^k$|^epsilon$|^omega$|^nut$|^nuTilda$|^tke$|^tdr$",
        {
            "name": "turbulence",
            "category": "scalar",
            "colormap": "plasma",
            "diverging": False,
            "log_scale": True,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^sigma$|^stress$|^S$|^vonMises$|^von_mises$|^sxx$|^syy$|^szz$",
        {
            "name": "stress",
            "category": "scalar",
            "colormap": "jet",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^D$|^displacement$|^disp$|^deformation$",
        {
            "name": "displacement",
            "category": "vector",
            "colormap": "viridis",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": True,
            "streamlines": False,
        },
    ),
    (
        r"^alpha\.?\w*$|^vof$|^volume.?fraction$",
        {
            "name": "vof",
            "category": "scalar",
            "colormap": "blues",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "front",
            "camera_3d": "front",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^vorticity$|^omega_z$|^curl_U$|^Q$|^lambda2$",
        {
            "name": "vorticity",
            "category": "vector",
            "colormap": "coolwarm",
            "diverging": True,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": True,
        },
    ),
    (
        r"^quality$|^skewness$|^orthogonality$|^aspect.?ratio$|^cell.?quality$",
        {
            "name": "mesh_quality",
            "category": "scalar",
            "colormap": "rdylgn",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface_with_edges",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^rho$|^density$",
        {
            "name": "density",
            "category": "scalar",
            "colormap": "viridis",
            "diverging": False,
            "log_scale": False,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
    (
        r"^wallShearStress$|^wss$|^tau_w$",
        {
            "name": "wall_shear",
            "category": "vector",
            "colormap": "plasma",
            "diverging": False,
            "log_scale": True,
            "camera_2d": "top",
            "camera_3d": "isometric",
            "representation": "surface",
            "warp": False,
            "streamlines": False,
        },
    ),
]

_FALLBACK_SCALAR = PhysicsType(
    name="unknown_scalar",
    category="scalar",
    colormap="cool to warm",
    diverging=False,
    log_scale=False,
    camera_2d="top",
    camera_3d="isometric",
    representation="surface",
    warp=False,
    streamlines=False,
)

_FALLBACK_VECTOR = PhysicsType(
    name="unknown_vector",
    category="vector",
    colormap="viridis",
    diverging=False,
    log_scale=False,
    camera_2d="front",
    camera_3d="isometric",
    representation="surface",
    warp=False,
    streamlines=False,
)


def detect_physics(
    field_name: str,
    num_components: int = 1,
    data_range: tuple[float, float] | None = None,
) -> PhysicsType:
    """Detect physical quantity from field name and data characteristics."""
    category = "vector" if num_components >= 3 else ("tensor" if num_components >= 6 else "scalar")

    for pattern, props in _PHYSICS_PATTERNS:
        if re.match(pattern, field_name, re.IGNORECASE):
            pt = PhysicsType(**props)
            if data_range is not None and not pt.diverging:
                if data_range[0] < 0 < data_range[1]:
                    pt = PhysicsType(**{**props, "diverging": True, "colormap": "coolwarm"})
            return pt

    fallback = _FALLBACK_VECTOR if category == "vector" else _FALLBACK_SCALAR
    if data_range is not None and data_range[0] < 0 < data_range[1]:
        return PhysicsType(
            name=fallback.name,
            category=fallback.category,
            colormap="coolwarm",
            diverging=True,
            log_scale=False,
            camera_2d=fallback.camera_2d,
            camera_3d=fallback.camera_3d,
            representation=fallback.representation,
            warp=fallback.warp,
            streamlines=fallback.streamlines,
        )
    return fallback


# ======================================================================
# 2. Smart Camera — View Frustum Analysis
# ======================================================================


@dataclass(frozen=True, slots=True)
class SmartCamera:
    """Camera recommendation from bounding box frustum analysis."""

    preset: str
    reason: str
    flat_axis: int | None  # 0=X, 1=Y, 2=Z flat; None=3D
    aspect_ratios: tuple[float, float, float]  # normalized (dx, dy, dz) / max
    is_2d: bool


def analyze_camera(
    bounds: tuple[float, float, float, float, float, float],
    physics: PhysicsType | None = None,
) -> SmartCamera:
    """Analyze dataset bounds to find optimal camera position.

    Strategy: maximize visible area by looking along the thinnest axis.
    For 2D data, view perpendicular to the flat plane.
    For elongated 3D data, view from the side that shows the largest face.
    Physics hints override when ambiguous (e.g., VOF always side view).

    Args:
        bounds: (xmin, xmax, ymin, ymax, zmin, zmax).
        physics: Optional physics type for domain-specific overrides.

    Returns:
        SmartCamera with preset name, reason, and analysis.
    """
    dx = abs(bounds[1] - bounds[0])
    dy = abs(bounds[3] - bounds[2])
    dz = abs(bounds[5] - bounds[4])
    diag = sqrt(dx * dx + dy * dy + dz * dz)

    if diag < 1e-30:
        return SmartCamera("isometric", "degenerate bounds", None, (0.0, 0.0, 0.0), False)

    # Normalized dimensions
    max_dim = max(dx, dy, dz, 1e-30)
    rx, ry, rz = dx / max_dim, dy / max_dim, dz / max_dim
    ratios = (rx, ry, rz)

    # Detect flat axis: dimension < 1% of diagonal
    flat_threshold = 0.01
    flat_axes = []
    if dx / diag < flat_threshold:
        flat_axes.append(0)
    if dy / diag < flat_threshold:
        flat_axes.append(1)
    if dz / diag < flat_threshold:
        flat_axes.append(2)

    is_2d = len(flat_axes) == 1
    flat_axis = flat_axes[0] if is_2d else None

    # --- Physics override: domain-specific camera regardless of geometry ---
    if physics is not None:
        if is_2d:
            reason = f"2D {physics.name}: flat axis={_axis_name(flat_axis)}"
            return SmartCamera(physics.camera_2d, reason, flat_axis, ratios, True)
        return SmartCamera(physics.camera_3d, f"3D {physics.name}", None, ratios, False)

    # --- Geometry-based selection ---
    if is_2d:
        # View perpendicular to the flat plane
        preset = _flat_axis_to_preset(flat_axis)  # type: ignore[arg-type]
        return SmartCamera(preset, f"2D: flat {_axis_name(flat_axis)}-axis", flat_axis, ratios, True)

    if len(flat_axes) >= 2:
        # 1D line-like data: view from perpendicular to line direction
        return SmartCamera("front", "1D line-like geometry", None, ratios, False)

    # 3D: find the axis with maximum visible area (product of other two dims)
    # View along the axis that gives largest projected area
    areas = [dy * dz, dx * dz, dx * dy]  # area visible from X, Y, Z
    best_view_axis = areas.index(max(areas))

    # Also check if isometric is better (when aspect ratios are similar)
    min_ratio = min(rx, ry, rz)
    if min_ratio > 0.3:
        # Nearly cubic → isometric gives best overview
        return SmartCamera("isometric", "near-cubic geometry", None, ratios, False)

    # Elongated: view along thinnest axis (largest face visible)
    preset_map = {0: "right", 1: "front", 2: "top"}
    preset = preset_map[best_view_axis]
    reason = f"elongated: largest face visible from {preset} ({_axis_name(best_view_axis)}-axis view)"
    return SmartCamera(preset, reason, None, ratios, False)


# ======================================================================
# 3. Smart Representation
# ======================================================================

# All supported VTK representation types
REPRESENTATION_TYPES: dict[str, dict[str, Any]] = {
    "surface": {
        "vtk_value": 2,
        "description": "Filled surface rendering (default for most data)",
        "use_when": "Scalar/vector fields on surfaces, general visualization",
    },
    "surface_with_edges": {
        "vtk_value": 2,  # surface + edge_visibility=True
        "description": "Surface with mesh edges overlaid",
        "use_when": "Mesh quality inspection, structural analysis, small meshes",
    },
    "wireframe": {
        "vtk_value": 1,
        "description": "Mesh edges only (no filled faces)",
        "use_when": "Mesh topology inspection, overlaying on surface renders",
    },
    "points": {
        "vtk_value": 0,
        "description": "Points only (each vertex as a dot)",
        "use_when": "Point clouds, SPH particles (small datasets)",
    },
    "point_gaussian": {
        "vtk_value": 0,  # points + gaussian splat (custom shader)
        "description": "Gaussian-splatted points for smooth particle rendering",
        "use_when": "SPH particles, DEM particles, large point clouds",
    },
}


@dataclass(frozen=True, slots=True)
class SmartRepresentation:
    """Representation recommendation for rendering."""

    primary: str  # "surface", "wireframe", "points", "point_gaussian", "surface_with_edges"
    edge_visibility: bool
    edge_opacity: float  # 0.0-1.0, for subtle edge overlay
    opacity: float  # actor opacity
    point_size: float  # for points/point_gaussian
    line_width: float  # for wireframe


def smart_representation(
    dataset: vtk.vtkDataObject,
    physics: PhysicsType | None = None,
) -> SmartRepresentation:
    """Recommend rendering representation based on data type and physics.

    Logic:
    - Volume mesh (unstructured 3D) → surface
    - Surface mesh with <10k cells → surface_with_edges
    - No cells but has points → points or point_gaussian
    - Structural with warp → surface_with_edges
    - Mesh quality → surface_with_edges
    """
    ds = _ensure_dataset(dataset)
    if ds is None:
        return SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0)

    n_cells = ds.GetNumberOfCells()
    n_points = ds.GetNumberOfPoints()

    # Physics-driven override
    if physics is not None:
        if physics.representation == "surface_with_edges":
            return SmartRepresentation("surface", True, 0.1, 1.0, 2.0, 1.0)
        if physics.warp:
            return SmartRepresentation("surface", True, 0.05, 1.0, 2.0, 1.0)

    # Point-only data (SPH particles, point clouds)
    if n_cells == 0 and n_points > 0:
        if n_points > 50000:
            return SmartRepresentation("point_gaussian", False, 0.0, 0.8, _auto_point_size(ds), 1.0)
        return SmartRepresentation("points", False, 0.0, 1.0, _auto_point_size(ds), 1.0)

    # Small surface mesh → show edges
    if n_cells < 10000 and n_cells > 0:
        return SmartRepresentation("surface", True, 0.05, 1.0, 2.0, 1.0)

    # Default: clean surface
    return SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0)


def _auto_point_size(ds: vtk.vtkDataSet) -> float:
    """Estimate point size from average point spacing."""
    n = ds.GetNumberOfPoints()
    if n < 2:
        return 5.0
    bounds = ds.GetBounds()
    dx = bounds[1] - bounds[0]
    dy = bounds[3] - bounds[2]
    dz = bounds[5] - bounds[4]
    volume = max(dx * dy * dz, 1e-30)
    # Approximate spacing: cube root of volume per point
    spacing = (volume / n) ** (1.0 / 3.0)
    diag = sqrt(dx * dx + dy * dy + dz * dz)
    # Point size as fraction of diagonal (aim for ~2% of screen)
    size = max(1.0, min(20.0, spacing / diag * 500.0))
    return float(round(size, 1))


# ======================================================================
# 4. Visualization Technique Recommendations
# ======================================================================


@dataclass(frozen=True, slots=True)
class VisualizationTechnique:
    """A recommended visualization technique."""

    technique: str  # "glyph", "isosurface", "streamlines", "warp", "contour_lines"
    params: dict[str, Any]
    reason: str
    priority: int  # 1=primary, 2=supplementary, 3=optional


def recommend_techniques(
    dataset: vtk.vtkDataObject,
    field_name: str,
    physics: PhysicsType | None = None,
) -> list[VisualizationTechnique]:
    """Recommend visualization techniques for a dataset + field.

    Returns a prioritized list of techniques. Priority 1 should be applied
    by default, priority 2 can enhance the visualization, priority 3 is optional.
    """
    ds = _ensure_dataset(dataset)
    if ds is None:
        return []

    if physics is None:
        arr, _ = _find_array(ds, field_name)
        nc = arr.GetNumberOfComponents() if arr else 1
        dr = arr.GetRange(-1 if nc > 1 else 0) if arr else None
        physics = detect_physics(field_name, nc, dr)

    techniques: list[VisualizationTechnique] = []
    bounds = ds.GetBounds()

    # --- Vector field: glyph arrows ---
    if physics.is_vector:
        scale = _auto_glyph_scale(ds)
        techniques.append(
            VisualizationTechnique(
                technique="glyph",
                params={
                    "array_name": field_name,
                    "scale_factor": scale,
                    "glyph_type": "arrow",
                    "max_points": min(ds.GetNumberOfPoints(), 5000),
                },
                reason=f"Vector field '{field_name}': arrow glyphs show direction and magnitude",
                priority=2,
            )
        )

    # --- Streamlines for flow fields ---
    if physics.streamlines:
        seed_p1, seed_p2 = _auto_seed_line(bounds)
        techniques.append(
            VisualizationTechnique(
                technique="streamlines",
                params={
                    "vectors": field_name,
                    "seed_point1": list(seed_p1),
                    "seed_point2": list(seed_p2),
                    "seed_resolution": 20,
                    "max_length": _diagonal(bounds) * 2.0,
                },
                reason=f"Flow field '{field_name}': streamlines visualize flow paths",
                priority=1,
            )
        )

    # --- WarpByVector for displacement ---
    if physics.warp:
        warp_scale = _auto_warp_scale(ds, field_name)
        techniques.append(
            VisualizationTechnique(
                technique="warp",
                params={
                    "vector": field_name,
                    "scale_factor": warp_scale,
                },
                reason=f"Displacement '{field_name}': warp mesh to show deformation",
                priority=1,
            )
        )

    # --- Isosurface for scalar fields ---
    if physics.category == "scalar" and not physics.log_scale:
        arr, _ = _find_array(ds, field_name)
        if arr is not None:
            lo, hi = arr.GetRange(0)
            if abs(hi - lo) > 1e-30:
                # Special case: VOF → isosurface at 0.5
                if physics.name == "vof":
                    techniques.append(
                        VisualizationTechnique(
                            technique="isosurface",
                            params={"array_name": field_name, "value": 0.5},
                            reason="VOF field: isosurface at 0.5 shows free surface",
                            priority=1,
                        )
                    )
                else:
                    # Auto-compute 3 evenly spaced isovalues
                    step = (hi - lo) / 4.0
                    isovalues = [round(lo + step * i, 6) for i in range(1, 4)]
                    techniques.append(
                        VisualizationTechnique(
                            technique="isosurface",
                            params={"array_name": field_name, "isovalues": isovalues},
                            reason=f"Scalar field '{field_name}': isosurfaces at {isovalues}",
                            priority=3,
                        )
                    )

    # --- Contour lines for 2D scalar fields ---
    is_2d = _is_2d_dataset(bounds)
    if is_2d and physics.category == "scalar":
        arr, _ = _find_array(ds, field_name)
        if arr is not None:
            lo, hi = arr.GetRange(0)
            if abs(hi - lo) > 1e-30:
                step = (hi - lo) / 10.0
                isovalues = [round(lo + step * i, 6) for i in range(1, 10)]
                techniques.append(
                    VisualizationTechnique(
                        technique="contour_lines",
                        params={"array_name": field_name, "isovalues": isovalues},
                        reason=f"2D scalar: contour lines for '{field_name}'",
                        priority=2,
                    )
                )

    return sorted(techniques, key=lambda t: t.priority)


# ======================================================================
# 5. Unified Smart Defaults
# ======================================================================


@dataclass(frozen=True, slots=True)
class SmartDefaults:
    """Complete visualization recommendation for a dataset + field."""

    physics: PhysicsType
    camera: SmartCamera
    representation: SmartRepresentation
    colormap: str
    log_scale: bool
    scalar_range: tuple[float, float] | None
    techniques: list[VisualizationTechnique] = field(default_factory=list)


def smart_defaults(
    dataset: vtk.vtkDataObject,
    field_name: str | None = None,
) -> SmartDefaults:
    """Compute complete smart visualization defaults for a dataset.

    Analyzes dataset geometry, field characteristics, and physics to recommend:
    - Camera position (view frustum analysis)
    - Colormap and scale
    - Representation (surface, wireframe, points, ...)
    - Additional techniques (glyph, isosurface, streamlines, warp)
    """
    ds = _ensure_dataset(dataset)
    if ds is None:
        return SmartDefaults(
            physics=_FALLBACK_SCALAR,
            camera=SmartCamera("isometric", "empty dataset", None, (0.0, 0.0, 0.0), False),
            representation=SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0),
            colormap="cool to warm",
            log_scale=False,
            scalar_range=None,
            techniques=[],
        )

    # Auto-detect field
    if field_name is None:
        field_name = _first_array_name(ds)

    # Get array info
    num_components = 1
    data_range: tuple[float, float] | None = None
    if field_name is not None:
        arr, _ = _find_array(ds, field_name)
        if arr is not None:
            num_components = arr.GetNumberOfComponents()
            data_range = arr.GetRange(-1 if num_components > 1 else 0)

    # Detect physics
    physics = detect_physics(field_name or "unknown", num_components, data_range)

    # Analyze camera
    bounds = ds.GetBounds()
    camera = analyze_camera(bounds, physics)

    # Smart representation
    rep = smart_representation(dataset, physics)

    colormap = physics.colormap

    # Techniques
    techniques: list[VisualizationTechnique] = []
    if field_name is not None:
        techniques = recommend_techniques(dataset, field_name, physics)

    return SmartDefaults(
        physics=physics,
        camera=camera,
        representation=rep,
        colormap=colormap,
        log_scale=physics.log_scale,
        scalar_range=data_range,
        techniques=techniques,
    )


# ======================================================================
# Internal helpers
# ======================================================================


def _axis_name(axis: int | None) -> str:
    return {0: "X", 1: "Y", 2: "Z"}.get(axis or -1, "?")


def _flat_axis_to_preset(flat_axis: int) -> str:
    """Map flat axis to camera preset that looks perpendicular to it."""
    return {0: "right", 1: "front", 2: "top"}[flat_axis]


def _diagonal(bounds: tuple[float, float, float, float, float, float]) -> float:
    dx = bounds[1] - bounds[0]
    dy = bounds[3] - bounds[2]
    dz = bounds[5] - bounds[4]
    return sqrt(dx * dx + dy * dy + dz * dz)


def _is_2d_dataset(bounds: tuple[float, float, float, float, float, float]) -> bool:
    dx = abs(bounds[1] - bounds[0])
    dy = abs(bounds[3] - bounds[2])
    dz = abs(bounds[5] - bounds[4])
    diag = sqrt(dx * dx + dy * dy + dz * dz)
    if diag < 1e-30:
        return False
    return min(dx, dy, dz) / diag < 0.01


def _ensure_dataset(data: vtk.vtkDataObject) -> vtk.vtkDataSet | None:
    import vtk

    if isinstance(data, vtk.vtkDataSet):
        return data
    if isinstance(data, vtk.vtkMultiBlockDataSet):
        return _largest_leaf(data)
    return None


def _largest_leaf(mb: vtk.vtkMultiBlockDataSet) -> vtk.vtkDataSet | None:
    import vtk

    best: vtk.vtkDataSet | None = None
    best_cells = -1
    for i in range(mb.GetNumberOfBlocks()):
        block = mb.GetBlock(i)
        if block is None:
            continue
        if isinstance(block, vtk.vtkMultiBlockDataSet):
            leaf = _largest_leaf(block)
            if leaf is not None and leaf.GetNumberOfCells() > best_cells:
                best = leaf
                best_cells = leaf.GetNumberOfCells()
        elif isinstance(block, vtk.vtkDataSet) and block.GetNumberOfCells() > best_cells:
            best = block
            best_cells = block.GetNumberOfCells()
    return best


def _first_array_name(ds: vtk.vtkDataSet) -> str | None:
    pd = ds.GetPointData()
    if pd and pd.GetNumberOfArrays() > 0:
        name = pd.GetArrayName(0)
        if name:
            return str(name)
    cd = ds.GetCellData()
    if cd and cd.GetNumberOfArrays() > 0:
        name = cd.GetArrayName(0)
        if name:
            return str(name)
    return None


def _find_array(ds: vtk.vtkDataSet, name: str) -> tuple[Any, str]:
    pd = ds.GetPointData()
    if pd:
        arr = pd.GetArray(name)
        if arr is not None:
            return arr, "point"
    cd = ds.GetCellData()
    if cd:
        arr = cd.GetArray(name)
        if arr is not None:
            return arr, "cell"
    return None, "point"


def _auto_glyph_scale(ds: vtk.vtkDataSet) -> float:
    """Auto-compute glyph scale factor: ~2% of diagonal."""
    bounds = ds.GetBounds()
    diag = _diagonal(bounds)
    return round(diag * 0.02, 6) if diag > 0 else 1.0


def _auto_seed_line(
    bounds: tuple[float, float, float, float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Auto-compute seed line for streamlines: across the shortest dimension center."""
    cx = (bounds[0] + bounds[1]) / 2
    cy = (bounds[2] + bounds[3]) / 2
    cz = (bounds[4] + bounds[5]) / 2
    dx = bounds[1] - bounds[0]
    dy = bounds[3] - bounds[2]
    dz = bounds[5] - bounds[4]

    # Seed along the axis perpendicular to the longest dimension
    dims = [(dx, 0), (dy, 1), (dz, 2)]
    dims.sort(key=lambda d: d[0])
    seed_axis = dims[1][1]  # middle axis = good seed direction

    p1 = [cx, cy, cz]
    p2 = [cx, cy, cz]
    half = [dx / 2, dy / 2, dz / 2]
    p1[seed_axis] = [bounds[0], bounds[2], bounds[4]][seed_axis] + half[seed_axis] * 0.1
    p2[seed_axis] = [bounds[1], bounds[3], bounds[5]][seed_axis] - half[seed_axis] * 0.1

    return (p1[0], p1[1], p1[2]), (p2[0], p2[1], p2[2])


def _auto_warp_scale(ds: vtk.vtkDataSet, field_name: str) -> float:
    """Auto-compute warp scale: deformation visible but not excessive."""
    arr, _ = _find_array(ds, field_name)
    if arr is None:
        return 1.0
    # Max displacement magnitude
    max_disp = arr.GetRange(-1)[1] if arr.GetNumberOfComponents() > 1 else arr.GetRange(0)[1]
    if max_disp < 1e-30:
        return 1.0

    bounds = ds.GetBounds()
    diag = _diagonal(bounds)
    if diag < 1e-30:
        return 1.0

    # Target: deformation ~10% of model size
    return float(round(diag * 0.1 / max_disp, 4))
