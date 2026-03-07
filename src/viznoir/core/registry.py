"""FilterRegistry and FormatRegistry — parameter schemas for all VTK filters and readers."""

from __future__ import annotations

from typing import Any

__all__ = [
    "FILTER_REGISTRY",
    "FORMAT_REGISTRY",
    "get_reader",
    "get_filter",
    "validate_filter_params",
]

# ---------------------------------------------------------------------------
# Filter Registry
# Each entry: vtk_class (VTK class name), params (schema), and optional
# setup template used by ScriptCompiler when the filter needs special config.
# ---------------------------------------------------------------------------

FILTER_REGISTRY: dict[str, dict[str, Any]] = {
    # --- Slicing / Clipping ---
    "Slice": {
        "vtk_class": "vtkCutter",
        "params": {
            "origin": {"type": "list[float]", "length": 3, "default": None},
            "normal": {"type": "list[float]", "length": 3, "default": [0, 0, 1]},
        },
    },
    "Clip": {
        "vtk_class": "vtkClipDataSet",
        "params": {
            "origin": {"type": "list[float]", "length": 3, "default": None},
            "normal": {"type": "list[float]", "length": 3, "default": [1, 0, 0]},
            "invert": {"type": "bool", "default": False},
        },
    },
    # --- Iso-surfaces / Threshold ---
    "Contour": {
        "vtk_class": "vtkContourFilter",
        "params": {
            "field": {"type": "str", "required": True},
            "association": {"type": "str", "default": "POINTS"},
            "isovalues": {"type": "list[float]", "required": True},
        },
    },
    "Threshold": {
        "vtk_class": "vtkThreshold",
        "params": {
            "field": {"type": "str", "required": True},
            "lower": {"type": "float", "required": True},
            "upper": {"type": "float", "required": True},
            "method": {"type": "str", "default": "Between"},
        },
    },
    # --- Flow visualization ---
    "StreamTracer": {
        "vtk_class": "vtkStreamTracer",
        "params": {
            "vectors": {"type": "list", "default": None},
            "seed_type": {"type": "str", "default": "Line"},
            "seed_point1": {"type": "list[float]", "length": 3, "default": None},
            "seed_point2": {"type": "list[float]", "length": 3, "default": None},
            "seed_resolution": {"type": "int", "default": 20},
            "max_length": {"type": "float", "default": 0.0},
            "direction": {"type": "str", "default": "BOTH"},
        },
    },
    "Glyph": {
        "vtk_class": "vtkGlyph3D",
        "params": {
            "orient": {"type": "str", "default": ""},
            "scale": {"type": "str", "default": ""},
            "scale_factor": {"type": "float", "default": 1.0},
            "glyph_type": {"type": "str", "default": "Arrow"},
            "max_points": {"type": "int", "default": 5000},
        },
    },
    # --- Computation ---
    "Calculator": {
        "vtk_class": "vtkArrayCalculator",
        "params": {
            "expression": {"type": "str", "required": True},
            "result_name": {"type": "str", "default": "Result"},
            "association": {"type": "str", "default": "POINTS"},
        },
    },
    "Gradient": {
        "vtk_class": "vtkGradientFilter",
        "params": {
            "field": {"type": "str", "required": True},
            "result_name": {"type": "str", "default": "Gradient"},
        },
    },
    "IntegrateVariables": {
        "vtk_class": "vtkIntegrateAttributes",
        "params": {},
    },
    "GenerateSurfaceNormals": {
        "vtk_class": "vtkPolyDataNormals",
        "params": {},
    },
    # --- Block / Surface extraction ---
    "ExtractBlock": {
        "vtk_class": "vtkExtractBlock",
        "params": {
            "selector": {"type": "str", "required": True},
            "match_mode": {"type": "str", "default": "contains"},  # contains|exact
        },
    },
    "ExtractSurface": {
        "vtk_class": "vtkDataSetSurfaceFilter",
        "params": {},
    },
    # --- Warp ---
    "WarpByVector": {
        "vtk_class": "vtkWarpVector",
        "params": {
            "vector": {"type": "str", "required": True},
            "scale_factor": {"type": "float", "default": 1.0},
        },
    },
    "WarpByScalar": {
        "vtk_class": "vtkWarpScalar",
        "params": {
            "scalars": {"type": "str", "required": True},
            "scale_factor": {"type": "float", "default": 1.0},
        },
    },
    # --- Data conversion ---
    "CellDatatoPointData": {
        "vtk_class": "vtkCellDataToPointData",
        "params": {},
    },
    "PointDatatoCellData": {
        "vtk_class": "vtkPointDataToCellData",
        "params": {},
    },
    # --- Sampling ---
    "PlotOverLine": {
        "vtk_class": "vtkProbeFilter",
        "params": {
            "point1": {"type": "list[float]", "length": 3, "required": True},
            "point2": {"type": "list[float]", "length": 3, "required": True},
            "resolution": {"type": "int", "default": 100},
        },
    },
    # --- Mesh processing ---
    "Decimate": {
        "vtk_class": "vtkDecimatePro",
        "params": {
            "reduction": {"type": "float", "default": 0.5},
        },
    },
    "Triangulate": {
        "vtk_class": "vtkTriangleFilter",
        "params": {},
    },
    # --- Smoothing / Cleaning ---
    "SmoothMesh": {
        "vtk_class": "vtkSmoothPolyDataFilter",
        "params": {
            "iterations": {"type": "int", "default": 20},
            "relaxation_factor": {"type": "float", "default": 0.1},
        },
    },
    "ProbePoint": {
        "vtk_class": "vtkProbeFilter",
        "params": {
            "point": {"type": "list[float]", "length": 3, "required": True},
        },
    },
    "CleanPolyData": {
        "vtk_class": "vtkCleanPolyData",
        "params": {
            "tolerance": {"type": "float", "default": 0.0},
        },
    },
    "Shrink": {
        "vtk_class": "vtkShrinkFilter",
        "params": {
            "shrink_factor": {"type": "float", "default": 0.5},
        },
    },
    "Tube": {
        "vtk_class": "vtkTubeFilter",
        "params": {
            "radius": {"type": "float", "default": 0.01},
            "sides": {"type": "int", "default": 6},
        },
    },
    # --- Programmable ---
    "ProgrammableFilter": {
        "vtk_class": "vtkProgrammableFilter",
        "params": {
            "script": {"type": "str", "required": True},
            "output_type": {"type": "str", "default": "Same as Input"},
        },
    },
}


# ---------------------------------------------------------------------------
# Format Registry — file extension → VTK reader class name
# ---------------------------------------------------------------------------

FORMAT_REGISTRY: dict[str, str] = {
    # Compound: VTK time-series wrappers (must be checked before single suffix)
    ".vtm.series": "vtkXMLMultiBlockDataReader",
    ".vtu.series": "vtkXMLUnstructuredGridReader",
    ".vtp.series": "vtkXMLPolyDataReader",
    ".vts.series": "vtkXMLStructuredGridReader",
    ".vti.series": "vtkXMLImageDataReader",
    ".vtr.series": "vtkXMLRectilinearGridReader",
    # Standard extensions
    ".foam": "vtkOpenFOAMReader",
    ".vtk": "vtkGenericDataObjectReader",
    ".vtu": "vtkXMLUnstructuredGridReader",
    ".vtp": "vtkXMLPolyDataReader",
    ".vts": "vtkXMLStructuredGridReader",
    ".vti": "vtkXMLImageDataReader",
    ".vtr": "vtkXMLRectilinearGridReader",
    ".vtm": "vtkXMLMultiBlockDataReader",
    ".pvd": "PVDReader",
    ".stl": "vtkSTLReader",
    ".ply": "vtkPLYReader",
    ".obj": "vtkOBJReader",
    ".csv": "vtkDelimitedTextReader",
    ".cgns": "vtkCGNSReader",
    ".exo": "vtkExodusIIReader",
    ".e": "vtkExodusIIReader",
    ".case": "vtkGenericEnSightReader",
    ".cas": "vtkFLUENTReader",
    ".dat": "vtkTecplotReader",
    ".xdmf": "vtkXdmf3Reader",
    ".xmf": "vtkXdmf3Reader",
}


def get_reader(filepath: str) -> str:
    """Return VTK reader class name for a file path."""
    from pathlib import Path

    p = Path(filepath)
    # Try compound suffix first (e.g., '.vtm.series')
    suffixes = p.suffixes
    if len(suffixes) >= 2:
        compound = "".join(suffixes[-2:]).lower()
        reader = FORMAT_REGISTRY.get(compound)
        if reader is not None:
            return reader
    ext = p.suffix.lower()
    reader = FORMAT_REGISTRY.get(ext)
    if reader is None:
        raise ValueError(f"Unsupported file format: '{ext}'. Supported: {sorted(FORMAT_REGISTRY)}")
    return reader


def get_filter(name: str) -> dict[str, Any]:
    """Return filter schema from registry. Raises KeyError if unknown.

    Accepts any casing: 'contour', 'Contour', 'CONTOUR' all resolve
    to the PascalCase registry key 'Contour'.
    """
    if name in FILTER_REGISTRY:
        return FILTER_REGISTRY[name]
    # Case-insensitive fallback
    lower = name.lower()
    for key in FILTER_REGISTRY:
        if key.lower() == lower:
            return FILTER_REGISTRY[key]
    available = sorted(FILTER_REGISTRY)
    raise KeyError(f"Unknown filter: '{name}'. Available: {available}")


def validate_filter_params(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Validate and fill defaults for filter parameters."""
    schema = get_filter(name)
    param_defs = schema["params"]
    result: dict[str, Any] = {}

    for key, definition in param_defs.items():
        if key in params:
            result[key] = params[key]
        elif "default" in definition:
            result[key] = definition["default"]
        elif definition.get("required"):
            raise ValueError(f"Filter '{name}' requires parameter '{key}'")

    return result
