"""FilterRegistry and FormatRegistry — parameter schemas for all ParaView filters and readers."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Filter Registry
# Each entry: pv_class (ParaView proxy name), params (schema), and optional
# setup template used by ScriptCompiler when the filter needs special config.
# ---------------------------------------------------------------------------

FILTER_REGISTRY: dict[str, dict[str, Any]] = {
    # --- Slicing / Clipping ---
    "Slice": {
        "pv_class": "Slice",
        "params": {
            "origin": {"type": "list[float]", "length": 3, "required": True},
            "normal": {"type": "list[float]", "length": 3, "default": [0, 0, 1]},
        },
    },
    "Clip": {
        "pv_class": "Clip",
        "params": {
            "origin": {"type": "list[float]", "length": 3, "default": [0, 0, 0]},
            "normal": {"type": "list[float]", "length": 3, "default": [1, 0, 0]},
            "invert": {"type": "bool", "default": False},
        },
    },
    # --- Iso-surfaces / Threshold ---
    "Contour": {
        "pv_class": "Contour",
        "params": {
            "field": {"type": "str", "required": True},
            "association": {"type": "str", "default": "POINTS"},
            "isovalues": {"type": "list[float]", "required": True},
        },
    },
    "Threshold": {
        "pv_class": "Threshold",
        "params": {
            "field": {"type": "str", "required": True},
            "lower": {"type": "float", "required": True},
            "upper": {"type": "float", "required": True},
            "method": {"type": "str", "default": "Between"},
        },
    },
    # --- Flow visualization ---
    "StreamTracer": {
        "pv_class": "StreamTracer",
        "params": {
            "vectors": {"type": "list", "default": None},
            "seed_type": {"type": "str", "default": "Line"},
            "seed_point1": {"type": "list[float]", "length": 3, "default": [0, 0, 0]},
            "seed_point2": {"type": "list[float]", "length": 3, "default": [1, 0, 0]},
            "seed_resolution": {"type": "int", "default": 20},
            "max_length": {"type": "float", "default": 1.0},
            "direction": {"type": "str", "default": "BOTH"},
        },
    },
    "Glyph": {
        "pv_class": "Glyph",
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
        "pv_class": "Calculator",
        "params": {
            "expression": {"type": "str", "required": True},
            "result_name": {"type": "str", "default": "Result"},
            "association": {"type": "str", "default": "POINTS"},
        },
    },
    "Gradient": {
        "pv_class": "Gradient",
        "params": {
            "field": {"type": "str", "required": True},
            "result_name": {"type": "str", "default": "Gradient"},
        },
    },
    "IntegrateVariables": {
        "pv_class": "IntegrateVariables",
        "params": {},
    },
    "GenerateSurfaceNormals": {
        "pv_class": "GenerateSurfaceNormals",
        "params": {},
    },
    # --- Block / Surface extraction ---
    "ExtractBlock": {
        "pv_class": "ExtractBlock",
        "params": {
            "selector": {"type": "str", "required": True},
            "match_mode": {"type": "str", "default": "contains"},  # contains|exact
        },
    },
    "ExtractSurface": {
        "pv_class": "ExtractSurface",
        "params": {},
    },
    # --- Warp ---
    "WarpByVector": {
        "pv_class": "WarpByVector",
        "params": {
            "vector": {"type": "str", "required": True},
            "scale_factor": {"type": "float", "default": 1.0},
        },
    },
    "WarpByScalar": {
        "pv_class": "WarpByScalar",
        "params": {
            "scalars": {"type": "str", "required": True},
            "scale_factor": {"type": "float", "default": 1.0},
        },
    },
    # --- Data conversion ---
    "CellDatatoPointData": {
        "pv_class": "CellDatatoPointData",
        "params": {},
    },
    "PointDatatoCellData": {
        "pv_class": "PointDatatoCellData",
        "params": {},
    },
    # --- Sampling ---
    "PlotOverLine": {
        "pv_class": "PlotOverLine",
        "params": {
            "point1": {"type": "list[float]", "length": 3, "required": True},
            "point2": {"type": "list[float]", "length": 3, "required": True},
            "resolution": {"type": "int", "default": 100},
        },
    },
    # --- Mesh processing ---
    "Decimate": {
        "pv_class": "Decimate",
        "params": {
            "reduction": {"type": "float", "default": 0.5},
        },
    },
    "Triangulate": {
        "pv_class": "Triangulate",
        "params": {},
    },
    # --- Programmable ---
    "ProgrammableFilter": {
        "pv_class": "ProgrammableFilter",
        "params": {
            "script": {"type": "str", "required": True},
            "output_type": {"type": "str", "default": "Same as Input"},
        },
    },
}


# ---------------------------------------------------------------------------
# Format Registry — file extension → ParaView reader class name
# ---------------------------------------------------------------------------

FORMAT_REGISTRY: dict[str, str] = {
    # Compound: ParaView time-series wrappers (must be checked before single suffix)
    ".vtm.series": "XMLMultiBlockDataReader",
    ".vtu.series": "XMLUnstructuredGridReader",
    ".vtp.series": "XMLPolyDataReader",
    ".vts.series": "XMLStructuredGridReader",
    ".vti.series": "XMLImageDataReader",
    ".vtr.series": "XMLRectilinearGridReader",
    # Standard extensions
    ".foam": "OpenFOAMReader",
    ".vtk": "LegacyVTKReader",
    ".vtu": "XMLUnstructuredGridReader",
    ".vtp": "XMLPolyDataReader",
    ".vts": "XMLStructuredGridReader",
    ".vti": "XMLImageDataReader",
    ".vtr": "XMLRectilinearGridReader",
    ".vtm": "XMLMultiBlockDataReader",
    ".pvd": "PVDReader",
    ".stl": "STLReader",
    ".ply": "PLYReader",
    ".obj": "OBJReader",
    ".csv": "CSVReader",
    ".cgns": "CGNSSeriesReader",
    ".exo": "ExodusIIReader",
    ".e": "ExodusIIReader",
    ".case": "EnSightReader",
    ".cas": "FluentCaseReader",
    ".dat": "TecplotReader",
    ".xdmf": "XDMFReader",
    ".xmf": "XDMFReader",
}


def get_reader(filepath: str) -> str:
    """Return ParaView reader class name for a file path."""
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
    """Return filter schema from registry. Raises KeyError if unknown."""
    if name not in FILTER_REGISTRY:
        available = sorted(FILTER_REGISTRY)
        raise KeyError(f"Unknown filter: '{name}'. Available: {available}")
    return FILTER_REGISTRY[name]


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
