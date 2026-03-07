"""Data insight extraction — field statistics, anomaly detection, physics context."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


def compute_field_stats(dataset: Any, field_name: str) -> dict[str, float]:
    """Compute basic statistics for a scalar field using VTK native arrays."""
    arr = dataset.GetPointData().GetArray(field_name)
    if arr is None:
        arr = dataset.GetCellData().GetArray(field_name)
    if arr is None:
        raise KeyError(f"Field '{field_name}' not found in dataset")

    from vtk.util.numpy_support import vtk_to_numpy
    data = vtk_to_numpy(arr)

    # Handle vector fields — compute magnitude
    if data.ndim > 1:
        data = np.linalg.norm(data, axis=1)

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
    """Detect local extrema and anomalies in a scalar field."""
    arr = dataset.GetPointData().GetArray(field_name)
    if arr is None:
        arr = dataset.GetCellData().GetArray(field_name)
    if arr is None:
        raise KeyError(f"Field '{field_name}' not found")

    from vtk.util.numpy_support import vtk_to_numpy
    data = vtk_to_numpy(arr)
    if data.ndim > 1:
        data = np.linalg.norm(data, axis=1)

    mean, std = np.mean(data), np.std(data)
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
        pt = dataset.GetPoint(int(idx))
        val = float(data[idx])
        anomalies.append({
            "type": "local_extremum" if val > mean else "local_minimum",
            "location": [round(pt[0], 3), round(pt[1], 3), round(pt[2], 3)],
            "value": round(val, 4),
            "significance": "high" if deviations[idx] > 3.0 else "medium",
        })

    return anomalies


_PHYSICS_KEYWORDS: dict[str, dict[str, str]] = {
    r"^p$|pressure|p_rgh": {
        "name": "pressure",
        "high_gradient": "Large pressure gradient suggests strong flow acceleration or shock formation",
        "uniform": "Relatively uniform pressure field — steady or stagnant flow region",
    },
    r"^U$|velocity|vel": {
        "name": "velocity",
        "high_gradient": "Sharp velocity gradient indicates shear layer or boundary layer",
        "uniform": "Uniform velocity — developed flow or free-stream region",
    },
    r"temperature|^T$|temp": {
        "name": "temperature",
        "high_gradient": "Strong temperature gradient — active heat transfer region",
        "uniform": "Thermal equilibrium region",
    },
    r"stress|von.?mises|sigma": {
        "name": "stress",
        "high_gradient": "Stress concentration — potential failure initiation site",
        "uniform": "Low stress region — structurally safe zone",
    },
    r"displacement|deform|^d$|^u$": {
        "name": "displacement",
        "high_gradient": "Localized deformation — possible hinge or buckling point",
        "uniform": "Rigid body region — minimal deformation",
    },
    r"k$|tke|turbulent.*kinetic": {
        "name": "turbulent_kinetic_energy",
        "high_gradient": "High turbulence production zone",
        "uniform": "Low turbulence — laminar or far-field",
    },
}


def infer_physics_context(field_name: str, stats: dict[str, float]) -> str:
    """Infer physics context string from field name and statistics."""
    gradient_range = stats["max"] - stats["min"]
    cv = stats["std"] / abs(stats["mean"]) if abs(stats["mean"]) > 1e-12 else 0.0

    for pattern, info in _PHYSICS_KEYWORDS.items():
        if re.search(pattern, field_name, re.IGNORECASE):
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
    """Guess physics domain from field names."""
    names_lower = " ".join(f.lower() for f in field_names)
    if any(kw in names_lower for kw in ["velocity", "pressure", " u ", " p "]):
        return "cfd"
    if any(kw in names_lower for kw in ["stress", "displacement", "strain"]):
        return "fea"
    if any(kw in names_lower for kw in ["temperature", "heat", "thermal"]):
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
        "suggested_equations": _DOMAIN_EQUATIONS.get(domain, []),
    }
