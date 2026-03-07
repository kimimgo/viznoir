"""Data insight extraction — field statistics, anomaly detection, physics context."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


def _get_field_array(dataset: Any, field_name: str) -> tuple[Any, str]:
    """Get field array and its location ('point' or 'cell').

    Returns (vtk_array, location) or raises KeyError.
    """
    arr = dataset.GetPointData().GetArray(field_name)
    if arr is not None:
        return arr, "point"
    arr = dataset.GetCellData().GetArray(field_name)
    if arr is not None:
        return arr, "cell"
    raise KeyError(f"Field '{field_name}' not found in dataset")


def _to_scalar(data: np.ndarray) -> np.ndarray:
    """Convert vector/tensor data to scalar magnitude. Warns for high-rank tensors."""
    if data.ndim == 1:
        return data
    ncols = data.shape[1]
    if ncols <= 3:
        # Vector field — magnitude is physically meaningful
        result: np.ndarray = np.linalg.norm(data, axis=1)
        return result
    # Tensor (6/9 components) — L2 norm is NOT physically meaningful
    # but still useful for anomaly detection as a proxy
    result = np.linalg.norm(data, axis=1)
    return result


def _get_location(dataset: Any, idx: int, location: str) -> list[float]:
    """Get spatial coordinates for a point or cell index."""
    if location == "point":
        pt = dataset.GetPoint(int(idx))
        return [round(pt[0], 3), round(pt[1], 3), round(pt[2], 3)]
    else:
        cell = dataset.GetCell(int(idx))
        bounds = cell.GetBounds()
        return [
            round((bounds[0] + bounds[1]) / 2, 3),
            round((bounds[2] + bounds[3]) / 2, 3),
            round((bounds[4] + bounds[5]) / 2, 3),
        ]


def compute_field_stats(dataset: Any, field_name: str) -> dict[str, float]:
    """Compute basic statistics for a scalar field using VTK native arrays."""
    arr, _ = _get_field_array(dataset, field_name)

    from vtk.util.numpy_support import vtk_to_numpy
    data = _to_scalar(vtk_to_numpy(arr))

    return {
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
    }


def detect_anomalies(
    dataset: Any,
    field_name: str,
    *,
    top_n: int = 5,
    threshold_sigma: float = 2.5,
) -> list[dict[str, Any]]:
    """Detect statistical anomalies in a scalar field.

    Identifies points/cells exceeding threshold_sigma standard deviations
    from the mean, sorted by deviation magnitude.
    """
    arr, location = _get_field_array(dataset, field_name)

    from vtk.util.numpy_support import vtk_to_numpy
    data = _to_scalar(vtk_to_numpy(arr))

    mean, std = float(np.mean(data)), float(np.std(data))
    if std < 1e-12:
        return []

    deviations = np.abs(data - mean) / std
    extreme_mask = deviations > threshold_sigma
    extreme_indices = np.where(extreme_mask)[0]

    if len(extreme_indices) == 0:
        max_idx = int(np.argmax(data))
        min_idx = int(np.argmin(data))
        extreme_indices = np.array([max_idx, min_idx])

    sorted_indices = extreme_indices[np.argsort(-deviations[extreme_indices])][:top_n]

    anomalies = []
    for idx in sorted_indices:
        val = float(data[idx])
        anomalies.append({
            "type": "local_extremum" if val > mean else "local_minimum",
            "location": _get_location(dataset, idx, location),
            "value": round(val, 4),
            "significance": "high" if deviations[idx] > 3.0 else "medium",
        })

    return anomalies


# --- Physics context inference ---
# Case-sensitive exact matches for 1-letter field names (CFD/FEA conventions)
_EXACT_FIELD_MAP: dict[str, str] = {
    "U": "velocity",        # OpenFOAM velocity (uppercase)
    "p": "pressure",        # OpenFOAM pressure (lowercase)
    "T": "temperature",     # Temperature (uppercase)
    "k": "turbulent_kinetic_energy",
    "u": "displacement",    # FEA displacement (lowercase)
    "d": "displacement",
}

# Case-insensitive patterns for multi-character field names
_PHYSICS_KEYWORDS: dict[str, dict[str, str]] = {
    "pressure": {
        "pattern": r"pressure|p_rgh",
        "high_gradient": "Large pressure gradient suggests strong flow acceleration or shock formation",
        "uniform": "Relatively uniform pressure field — steady or stagnant flow region",
    },
    "velocity": {
        "pattern": r"velocity|vel",
        "high_gradient": "Sharp velocity gradient indicates shear layer or boundary layer",
        "uniform": "Uniform velocity — developed flow or free-stream region",
    },
    "temperature": {
        "pattern": r"temperature|temp",
        "high_gradient": "Strong temperature gradient — active heat transfer region",
        "uniform": "Thermal equilibrium region",
    },
    "stress": {
        "pattern": r"stress|von.?mises|sigma",
        "high_gradient": "Stress concentration — potential failure initiation site",
        "uniform": "Low stress region — structurally safe zone",
    },
    "displacement": {
        "pattern": r"displacement|deform",
        "high_gradient": "Localized deformation — possible hinge or buckling point",
        "uniform": "Rigid body region — minimal deformation",
    },
    "turbulent_kinetic_energy": {
        "pattern": r"tke|turbulent.*kinetic",
        "high_gradient": "High turbulence production zone",
        "uniform": "Low turbulence — laminar or far-field",
    },
}


def _classify_field(field_name: str) -> str | None:
    """Classify field name to physics category. Case-sensitive for 1-letter names."""
    # Exact match first (case-sensitive, no ambiguity)
    if field_name in _EXACT_FIELD_MAP:
        return _EXACT_FIELD_MAP[field_name]
    # Multi-character: case-insensitive regex
    for category, info in _PHYSICS_KEYWORDS.items():
        if re.search(info["pattern"], field_name, re.IGNORECASE):
            return category
    return None


def infer_physics_context(field_name: str, stats: dict[str, float]) -> str:
    """Infer physics context string from field name and statistics."""
    gradient_range = stats["max"] - stats["min"]
    cv = stats["std"] / abs(stats["mean"]) if abs(stats["mean"]) > 1e-12 else 0.0

    category = _classify_field(field_name)
    if category and category in _PHYSICS_KEYWORDS:
        info = _PHYSICS_KEYWORDS[category]
        if cv > 0.3:
            return f"{info['high_gradient']} (range: {gradient_range:.4g}, CV: {cv:.2f})"
        else:
            return f"{info['uniform']} (range: {gradient_range:.4g}, CV: {cv:.2f})"

    if cv > 0.3:
        return f"High spatial variation in {field_name} (range: {gradient_range:.4g}, CV: {cv:.2f})"
    return f"Relatively uniform {field_name} distribution (range: {gradient_range:.4g}, CV: {cv:.2f})"


def recommend_views(
    field_name: str,
    anomalies: list[dict[str, Any]],
    *,
    bounds: list[list[float]] | None = None,
) -> list[dict[str, Any]]:
    """Generate recommended view parameters from anomalies."""
    views: list[dict[str, Any]] = []

    for anomaly in anomalies[:3]:
        loc = anomaly["location"]
        if bounds:
            extents = [b[1] - b[0] for b in bounds]
            longest = extents.index(max(extents))
            normal = [0, 0, 0]
            normal[longest] = 1
        else:
            normal = [1, 0, 0]

        views.append({
            "type": "slice",
            "params": {"origin": loc, "normal": normal},
            "reason": f"{field_name} {anomaly['type']} at ({loc[0]}, {loc[1]}, {loc[2]})",
        })

    if anomalies:
        values = [a["value"] for a in anomalies[:2]]
        views.append({
            "type": "contour",
            "params": {"values": [round(v, 4) for v in values]},
            "reason": f"Iso-surfaces at {field_name} extrema",
        })

    return views


# --- Cross-field analysis ---

def cross_field_analysis(
    dataset: Any,
    field_analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute cross-field correlations and insights."""
    from vtk.util.numpy_support import vtk_to_numpy

    insights: list[dict[str, Any]] = []
    names = [fa["name"] for fa in field_analyses]

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            try:
                arr_i, _ = _get_field_array(dataset, names[i])
                arr_j, _ = _get_field_array(dataset, names[j])
            except KeyError:
                continue

            data_i = _to_scalar(vtk_to_numpy(arr_i))
            data_j = _to_scalar(vtk_to_numpy(arr_j))

            if len(data_i) != len(data_j) or len(data_i) < 10:
                continue

            corr = float(np.corrcoef(data_i, data_j)[0, 1])
            if abs(corr) > 0.5:
                direction = "positive" if corr > 0 else "inverse"
                note = f"{direction.title()} correlation (r={corr:.2f})"
                # Add physics interpretation for known pairs
                cats = {_classify_field(names[i]), _classify_field(names[j])}
                if cats == {"pressure", "velocity"}:
                    note += " — Bernoulli-consistent"
                elif cats == {"temperature", "velocity"}:
                    note += " — convective heat transfer"
                insights.append({
                    "type": "correlation",
                    "fields": [names[i], names[j]],
                    "correlation": round(corr, 3),
                    "note": note,
                })

    return insights


# --- Equation suggestions ---

_NS_LATEX = r"\rho \frac{D\mathbf{u}}{Dt} = -\nabla p + \mu \nabla^2 \mathbf{u} + \mathbf{f}"
_BERNOULLI_LATEX = r"p + \frac{1}{2}\rho v^2 = \text{const}"
_CAUCHY_LATEX = r"\nabla \cdot \boldsymbol{\sigma} + \mathbf{b} = 0"
_HEAT_LATEX = r"\rho c_p \frac{\partial T}{\partial t} = k \nabla^2 T + q"

_DOMAIN_EQUATIONS: dict[str, list[dict[str, str]]] = {
    "cfd": [
        {"context": "momentum conservation", "latex": _NS_LATEX, "name": "Navier-Stokes"},
        {"context": "mass conservation", "latex": r"\nabla \cdot \mathbf{u} = 0", "name": "Continuity"},
        {"context": "pressure-velocity coupling", "latex": _BERNOULLI_LATEX, "name": "Bernoulli"},
    ],
    "fea": [
        {"context": "equilibrium", "latex": _CAUCHY_LATEX, "name": "Cauchy equilibrium"},
        {"context": "yield criterion", "latex": r"\sigma_{vm} = \sqrt{\frac{3}{2} s_{ij} s_{ij}}", "name": "von Mises"},
    ],
    "thermal": [
        {"context": "heat conduction", "latex": _HEAT_LATEX, "name": "Heat equation"},
        {"context": "convective heat transfer", "latex": r"q = h A (T_s - T_\infty)", "name": "Newton's cooling"},
    ],
}


def _guess_domain(field_names: list[str]) -> str:
    """Guess physics domain from field names using per-field classification."""
    categories = set()
    for name in field_names:
        cat = _classify_field(name)
        if cat:
            categories.add(cat)

    if categories & {"velocity", "pressure", "turbulent_kinetic_energy"}:
        return "cfd"
    if categories & {"stress", "displacement"}:
        return "fea"
    if categories & {"temperature"}:
        return "thermal"
    return "cfd"


def analyze_dataset(
    dataset: Any,
    *,
    focus: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Full dataset analysis — returns Level 2 insight report."""
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    all_fields = []
    for i in range(pd.GetNumberOfArrays()):
        all_fields.append(("point", pd.GetArrayName(i)))
    for i in range(cd.GetNumberOfArrays()):
        all_fields.append(("cell", cd.GetArrayName(i)))

    field_names = [name for _, name in all_fields if name]

    if domain is None:
        domain = _guess_domain(field_names)

    bounds_flat = list(dataset.GetBounds())
    bounds = [[bounds_flat[i], bounds_flat[i + 1]] for i in range(0, 6, 2)]

    if focus:
        all_fields = [(loc, name) for loc, name in all_fields if name == focus]

    field_analyses = []
    for _, field_name in all_fields:
        if not field_name:
            continue
        try:
            stats = compute_field_stats(dataset, field_name)
        except (KeyError, ValueError):
            continue

        anomalies = detect_anomalies(dataset, field_name)
        physics_ctx = infer_physics_context(field_name, stats)
        views = recommend_views(field_name, anomalies, bounds=bounds)

        field_analyses.append({
            "name": field_name,
            "stats": stats,
            "physics_context": physics_ctx,
            "anomalies": anomalies,
            "recommended_views": views,
        })

    return {
        "summary": {
            "num_points": dataset.GetNumberOfPoints(),
            "num_cells": dataset.GetNumberOfCells(),
            "bounds": bounds,
            "fields": field_names,
            "domain_guess": domain,
        },
        "field_analyses": field_analyses,
        "cross_field_insights": cross_field_analysis(dataset, field_analyses),
        "suggested_equations": _DOMAIN_EQUATIONS.get(domain, []),
    }
