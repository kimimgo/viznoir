"""Case-type rendering presets — camera, colormap, representation defaults.

Each preset provides sensible defaults for a simulation domain.
AI agents use these as starting points, then adjust per-case.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Camera Presets (reusable across case types)
# Values: position, focal_point, view_up
# ---------------------------------------------------------------------------

CAMERAS: dict[str, dict[str, list[float]]] = {
    "isometric": {
        "position": [1.0, -1.0, 0.8],  # normalized — scaled by bounds at runtime
        "focal_point": [0.0, 0.0, 0.0],
        "view_up": [0.0, 0.0, 1.0],
    },
    "top": {
        "position": [0.0, 0.0, 1.0],
        "focal_point": [0.0, 0.0, 0.0],
        "view_up": [0.0, 1.0, 0.0],
    },
    "front": {
        "position": [0.0, -1.0, 0.0],
        "focal_point": [0.0, 0.0, 0.0],
        "view_up": [0.0, 0.0, 1.0],
    },
    "right": {
        "position": [1.0, 0.0, 0.0],
        "focal_point": [0.0, 0.0, 0.0],
        "view_up": [0.0, 0.0, 1.0],
    },
    "left": {
        "position": [-1.0, 0.0, 0.0],
        "focal_point": [0.0, 0.0, 0.0],
        "view_up": [0.0, 0.0, 1.0],
    },
    "back": {
        "position": [0.0, 1.0, 0.0],
        "focal_point": [0.0, 0.0, 0.0],
        "view_up": [0.0, 0.0, 1.0],
    },
}

# ---------------------------------------------------------------------------
# Case-Type Presets
# ---------------------------------------------------------------------------

CASE_PRESETS: dict[str, dict[str, Any]] = {
    # ── External Aerodynamics ──
    "external_aero": {
        "description": "External aerodynamics — vehicles, airfoils, buildings",
        "views": {
            "overview": {
                "camera": "isometric",
                "description": "3D overview of the full domain",
            },
            "wake": {
                "camera": {
                    "position": [-2.0, 0.0, 0.3],
                    "focal_point": [0.0, 0.0, 0.0],
                    "view_up": [0.0, 0.0, 1.0],
                },
                "description": "Downstream wake view",
            },
            "surface_detail": {
                "camera": "front",
                "description": "Front view of body surface",
            },
        },
        "fields": {
            "pressure": {
                "field": "p",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
                "description": "Surface pressure distribution",
            },
            "velocity": {
                "field": "U",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Surface",
                "description": "Velocity magnitude",
                "calculator": {"expression": "mag(U)", "result_name": "Umag"},
            },
            "wall_shear": {
                "field": "wallShearStress",
                "association": "CELLS",
                "colormap": "Plasma",
                "representation": "Surface",
                "description": "Wall shear stress magnitude",
            },
            "vorticity": {
                "field": "Q",
                "association": "POINTS",
                "colormap": "Turbo",
                "representation": "Surface",
                "opacity": 0.6,
                "description": "Q-criterion iso-surfaces (vortex identification)",
            },
        },
        "common_filters": [
            {"filter": "StreamTracer", "use_case": "Flow visualization around body"},
            {"filter": "Slice", "use_case": "Symmetry plane, wake cross-sections"},
            {"filter": "Contour", "use_case": "Q-criterion iso-surfaces"},
        ],
        "background": [0.32, 0.34, 0.43],
    },

    # ── Internal Flow ──
    "internal_flow": {
        "description": "Internal flow — pipes, HVAC, mixing chambers",
        "views": {
            "cross_section": {
                "camera": "front",
                "description": "Cross-section perpendicular to flow",
            },
            "longitudinal": {
                "camera": "top",
                "description": "Longitudinal cut along flow direction",
            },
            "overview": {
                "camera": "isometric",
                "description": "3D overview",
            },
        },
        "fields": {
            "velocity": {
                "field": "U",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Surface",
                "calculator": {"expression": "mag(U)", "result_name": "Umag"},
            },
            "pressure": {
                "field": "p",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
            },
            "mesh": {
                "field": "p",
                "association": "POINTS",
                "colormap": "Grayscale",
                "representation": "Surface With Edges",
                "description": "Mesh quality inspection",
            },
        },
        "common_filters": [
            {"filter": "Slice", "use_case": "Cross-section velocity profiles"},
            {"filter": "PlotOverLine", "use_case": "Centerline pressure drop"},
            {
                "filter": "Threshold",
                "use_case": "Recirculation zones (low velocity)",
                "params": {"field": "Umag", "lower": 0.0, "upper": 0.1},
            },
        ],
        "background": [0.32, 0.34, 0.43],
    },

    # ── Multiphase / Sloshing ──
    "multiphase": {
        "description": "Multiphase flow — sloshing, wave tanks, free surface",
        "views": {
            "front": {
                "camera": "front",
                "description": "Front view for free surface tracking",
            },
            "side": {
                "camera": "right",
                "description": "Side view for wave profile",
            },
            "overview": {
                "camera": "isometric",
                "description": "3D overview",
            },
        },
        "fields": {
            "volume_fraction": {
                "field": "alpha.water",
                "association": "POINTS",
                "colormap": "Blue to Red Rainbow",
                "representation": "Surface",
                "scalar_range": [0.0, 1.0],
                "description": "Volume fraction (water=1, air=0)",
            },
            "free_surface": {
                "field": "alpha.water",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
                "description": "Free surface iso-contour at alpha=0.5",
                "contour_values": [0.5],
            },
            "velocity_on_surface": {
                "field": "U",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Surface",
                "calculator": {"expression": "mag(U)", "result_name": "Umag"},
                "description": "Velocity on free surface",
            },
            "pressure": {
                "field": "p_rgh",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
                "description": "Dynamic pressure",
            },
        },
        "common_filters": [
            {
                "filter": "Contour",
                "use_case": "Free surface extraction",
                "params": {"field": "alpha.water", "isovalues": [0.5]},
            },
            {"filter": "Clip", "use_case": "Symmetry plane visualization"},
            {"filter": "Threshold", "use_case": "Show water phase only (alpha > 0.5)"},
        ],
        "animation": {
            "mode": "timesteps",
            "fps": 25,
            "description": "Time-series free surface evolution",
        },
        "background": [0.32, 0.34, 0.43],
    },

    # ── Thermal / Conjugate Heat Transfer ──
    "thermal": {
        "description": "Thermal analysis — CHT, natural convection, heating",
        "views": {
            "cross_section": {
                "camera": "front",
                "description": "Cross-section showing temperature gradient",
            },
            "overview": {
                "camera": "isometric",
                "description": "3D temperature distribution",
            },
        },
        "fields": {
            "temperature": {
                "field": "T",
                "association": "POINTS",
                "colormap": "Inferno",
                "representation": "Surface",
                "description": "Temperature field",
            },
            "temperature_bw": {
                "field": "T",
                "association": "POINTS",
                "colormap": "Black-Body Radiation",
                "representation": "Surface",
                "description": "Temperature (black-body colormap for publications)",
            },
            "heat_flux": {
                "field": "T",
                "association": "POINTS",
                "colormap": "Plasma",
                "representation": "Surface",
                "description": "Temperature gradient magnitude (heat flux proxy)",
                "requires_gradient": True,
            },
            "velocity": {
                "field": "U",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Surface",
                "calculator": {"expression": "mag(U)", "result_name": "Umag"},
            },
        },
        "common_filters": [
            {"filter": "Slice", "use_case": "Temperature cross-sections"},
            {"filter": "Gradient", "use_case": "Heat flux computation (∇T)"},
            {"filter": "Glyph", "use_case": "Heat flux vectors"},
            {"filter": "PlotOverLine", "use_case": "Temperature profile along wall"},
        ],
        "background": [0.32, 0.34, 0.43],
    },

    # ── Structural FEA ──
    "structural_fea": {
        "description": "Structural FEA — stress, deformation, fatigue",
        "views": {
            "deformed": {
                "camera": "isometric",
                "description": "Deformed shape with stress coloring",
            },
            "undeformed_overlay": {
                "camera": "isometric",
                "description": "Deformed vs. original comparison",
            },
            "detail": {
                "camera": "front",
                "description": "Close-up on stress concentration",
            },
        },
        "fields": {
            "von_mises": {
                "field": "von_mises_stress",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Surface",
                "description": "Von Mises equivalent stress",
            },
            "displacement": {
                "field": "displacement",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Surface",
                "description": "Displacement magnitude",
                "calculator": {"expression": "mag(displacement)", "result_name": "Dmag"},
            },
            "original_mesh": {
                "field": "von_mises_stress",
                "association": "POINTS",
                "colormap": "Grayscale",
                "representation": "Wireframe",
                "opacity": 0.3,
                "description": "Original undeformed mesh overlay",
            },
        },
        "common_filters": [
            {
                "filter": "WarpByVector",
                "use_case": "Deformed shape visualization",
                "params": {"vector": "displacement", "scale_factor": 10.0},
            },
            {
                "filter": "Threshold",
                "use_case": "Regions above yield stress",
                "params": {"field": "von_mises_stress"},
            },
            {"filter": "ExtractSurface", "use_case": "Surface-only view"},
        ],
        "warp_scale_hint": "Use 10-100x for small deformations, 1x for large",
        "background": [1.0, 1.0, 1.0],  # White for publication
    },

    # ── DualSPHysics / SPH Particles ──
    "sph_particles": {
        "description": "SPH particle methods — DualSPHysics, wave tanks, fluid-structure",
        "views": {
            "front": {
                "camera": "front",
                "description": "Front view for wave profile",
            },
            "side": {
                "camera": "right",
                "description": "Side view for wave propagation",
            },
            "overview": {
                "camera": "isometric",
                "description": "3D particle overview",
            },
        },
        "fields": {
            "velocity": {
                "field": "Velocity",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Point Gaussian",
                "point_size": 2.0,
                "description": "Particle velocity magnitude",
                "calculator": {"expression": "mag(Velocity)", "result_name": "Vmag"},
            },
            "pressure": {
                "field": "Pressure",
                "association": "POINTS",
                "colormap": "Cool to Warm",
                "representation": "Point Gaussian",
                "point_size": 2.0,
                "description": "Particle pressure",
            },
            "type": {
                "field": "Type",
                "association": "POINTS",
                "colormap": "Viridis",
                "representation": "Point Gaussian",
                "point_size": 1.5,
                "description": "Particle type (fluid=0, bound=1, etc.)",
            },
        },
        "common_filters": [
            {
                "filter": "Threshold",
                "use_case": "Fluid particles only (exclude boundary)",
                "params": {"field": "Type", "lower": 0, "upper": 0},
            },
            {"filter": "Calculator", "use_case": "Velocity magnitude"},
        ],
        "animation": {
            "mode": "timesteps",
            "fps": 30,
            "description": "Time-series particle evolution",
        },
        "background": [0.15, 0.15, 0.15],  # Dark for particle visibility
    },
}

# ---------------------------------------------------------------------------
# Colormap Reference (for AI context)
# ---------------------------------------------------------------------------

COLORMAP_GUIDE: dict[str, dict[str, str]] = {
    "Cool to Warm": {"type": "diverging", "use": "Pressure, symmetric data, general"},
    "Coolwarm": {"type": "diverging", "use": "Alias for Cool to Warm — symmetric data"},
    "Viridis": {"type": "sequential", "use": "Velocity, magnitude, colorblind-safe"},
    "Inferno": {"type": "sequential", "use": "Temperature, heat maps"},
    "Plasma": {"type": "sequential", "use": "Wall shear stress, magnitude fields"},
    "Turbo": {"type": "rainbow", "use": "High contrast, vorticity"},
    "Jet": {"type": "rainbow", "use": "Legacy only — avoid for publications"},
    "Rainbow Desaturated": {"type": "sequential", "use": "General-purpose, perceptually uniform"},
    "Blues": {"type": "sequential", "use": "Single-variable intensity, density, depth"},
    "RdYlGn": {"type": "diverging", "use": "Red-Yellow-Green, quality/performance metrics"},
    "Black-Body Radiation": {"type": "sequential", "use": "Temperature (publication)"},
    "Grayscale": {"type": "sequential", "use": "Printing, mesh overlay"},
    "Terrain": {"type": "sequential", "use": "Topography, elevation, bathymetry"},
    "Magma": {"type": "sequential", "use": "Heat maps, similar to inferno but softer"},
    "Cividis": {"type": "sequential", "use": "Colorblind-safe, optimized for CVD viewers"},
    "Twilight": {"type": "cyclic", "use": "Phase, angle, cyclic data (wraps at endpoints)"},
    "Blue to Red Rainbow": {"type": "rainbow", "use": "Volume fraction, multiphase flow"},
    "X Ray": {"type": "sequential", "use": "Density, opacity, medical imaging"},
}

# ---------------------------------------------------------------------------
# Representation Reference
# ---------------------------------------------------------------------------

REPRESENTATION_GUIDE: dict[str, str] = {
    "Surface": "Default solid rendering — most cases",
    "Surface With Edges": "Mesh inspection, internal flow, FEA",
    "Wireframe": "Mesh-only, overlay on deformed shape",
    "Point Gaussian": "SPH particles, point clouds — GPU accelerated",
    "Volume": "Direct volume rendering (3D scalar fields)",
    "Points": "Basic point rendering (legacy, prefer Point Gaussian)",
    "Outline": "Bounding box only",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_preset(case_type: str) -> dict[str, Any]:
    """Get rendering preset for a case type. Raises KeyError if unknown."""
    if case_type not in CASE_PRESETS:
        available = sorted(CASE_PRESETS)
        raise KeyError(f"Unknown case type: '{case_type}'. Available: {available}")
    return CASE_PRESETS[case_type]


def list_presets() -> dict[str, str]:
    """Return {case_type: description} for all available presets."""
    return {k: v["description"] for k, v in CASE_PRESETS.items()}
