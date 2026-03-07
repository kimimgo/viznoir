"""Transfer function presets for volume rendering."""

from __future__ import annotations

from typing import Any

import vtk

TRANSFER_PRESETS: dict[str, dict[str, Any]] = {
    "generic": {
        "description": "General-purpose ramp — transparent low, opaque high",
        "opacity_points": [
            (0.0, 0.0),
            (0.2, 0.0),
            (0.4, 0.05),
            (1.0, 0.5),
        ],
    },
    "ct_bone": {
        "description": "CT scan — bones opaque, soft tissue transparent",
        "opacity_points": [
            (0.0, 0.0),
            (0.3, 0.0),
            (0.5, 0.0),
            (0.7, 0.1),
            (0.85, 0.6),
            (1.0, 0.9),
        ],
    },
    "ct_tissue": {
        "description": "CT scan — soft tissue visible, bones semi-transparent",
        "opacity_points": [
            (0.0, 0.0),
            (0.15, 0.0),
            (0.3, 0.15),
            (0.5, 0.3),
            (0.7, 0.1),
            (1.0, 0.05),
        ],
    },
    "mri_brain": {
        "description": "MRI brain — mid-range intensities highlighted",
        "opacity_points": [
            (0.0, 0.0),
            (0.1, 0.0),
            (0.3, 0.1),
            (0.5, 0.4),
            (0.7, 0.3),
            (0.9, 0.1),
            (1.0, 0.0),
        ],
    },
    "thermal": {
        "description": "Thermal/CFD — smooth gradient for temperature fields",
        "opacity_points": [
            (0.0, 0.02),
            (0.25, 0.05),
            (0.5, 0.15),
            (0.75, 0.35),
            (1.0, 0.6),
        ],
    },
    "isosurface_like": {
        "description": "Sharp band — mimics isosurface at a narrow range",
        "opacity_points": [
            (0.0, 0.0),
            (0.45, 0.0),
            (0.48, 0.8),
            (0.52, 0.8),
            (0.55, 0.0),
            (1.0, 0.0),
        ],
    },
}


def list_presets() -> list[str]:
    """Return sorted list of available transfer function preset names."""
    return sorted(TRANSFER_PRESETS.keys())


def build_opacity_function(
    preset_name: str,
    scalar_range: tuple[float, float],
    opacity_scale: float = 1.0,
) -> vtk.vtkPiecewiseFunction:
    """Build vtkPiecewiseFunction from a named preset."""
    if preset_name not in TRANSFER_PRESETS:
        raise KeyError(f"Unknown transfer function preset: {preset_name}")

    preset = TRANSFER_PRESETS[preset_name]
    lo, hi = scalar_range
    span = hi - lo

    otf = vtk.vtkPiecewiseFunction()
    for rel_val, opacity in preset["opacity_points"]:
        otf.AddPoint(lo + rel_val * span, opacity * opacity_scale)

    return otf
