"""MCP Prompt registration — domain-specific post-processing guides."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


_registered_instances: set[int] = set()


def register_prompts(mcp: FastMCP) -> None:
    """Register all MCP prompts (idempotent per mcp instance)."""
    mcp_id = id(mcp)
    if mcp_id in _registered_instances:
        return
    _registered_instances.add(mcp_id)

    @mcp.prompt()
    def cfd_postprocess(simulation_type: str = "general") -> str:
        """CFD post-processing guide. Choose simulation_type:
        external_aero, internal_flow, multiphase, thermal, general."""
        guides = {
            "external_aero": _EXTERNAL_AERO_GUIDE,
            "internal_flow": _INTERNAL_FLOW_GUIDE,
            "multiphase": _MULTIPHASE_GUIDE,
            "thermal": _THERMAL_GUIDE,
            "general": _GENERAL_CFD_GUIDE,
        }
        return guides.get(simulation_type, _GENERAL_CFD_GUIDE)

    @mcp.prompt()
    def fea_postprocess(analysis_type: str = "static") -> str:
        """FEA post-processing guide. Choose analysis_type:
        static, modal, fatigue, contact."""
        guides = {
            "static": _STATIC_FEA_GUIDE,
            "modal": _MODAL_FEA_GUIDE,
        }
        return guides.get(analysis_type, _STATIC_FEA_GUIDE)

    @mcp.prompt()
    def visualization_guide(goal: str = "general") -> str:
        """Visualization best practices guide."""
        return _VIZ_GUIDE


# ---------------------------------------------------------------------------
# Guide content
# ---------------------------------------------------------------------------

_GENERAL_CFD_GUIDE = """\
# CFD Post-Processing Guide

## Standard Workflow
1. **inspect_data** — Check available fields, timesteps, bounds, and blocks
2. **render** — Overview visualization of the full domain
3. **slice** — Cut planes at key locations to examine internal flow
4. **extract_stats** — Get min/max/mean of key fields (p, U, T)
5. **plot_over_line** — Profile extraction along lines of interest
6. **animate** — Single-field time series animation
7. **split_animate** — Multi-pane synchronized animation (3D views + graphs → GIF)

## Key Fields
- **p**: Pressure (kinematic or static)
- **U**: Velocity vector
- **T**: Temperature
- **k**: Turbulent kinetic energy
- **epsilon/omega**: Turbulent dissipation

## Tips
- Use `timestep="latest"` for steady-state results
- Use `blocks=["internalMesh"]` to exclude boundaries
- For velocity magnitude: use Calculator with `mag(U)`
"""

_EXTERNAL_AERO_GUIDE = """\
# External Aerodynamics Post-Processing

## Key Analyses
1. **Surface pressure** — render(field="p") on wall boundaries
2. **Drag/Lift forces** — integrate_surface on wall with pressure
3. **Wake analysis** — streamlines downstream
4. **Boundary layer** — plot_over_line normal to wall

## Pipeline: Force Calculation
```json
{
  "source": {"file": "/data/case.foam", "timestep": "latest"},
  "pipeline": [
    {"filter": "ExtractBlock", "params": {"selector": "wall"}},
    {"filter": "GenerateSurfaceNormals"},
    {"filter": "Calculator", "params": {"expression": "p*Normals", "result_name": "F"}},
    {"filter": "IntegrateVariables"}
  ],
  "output": {"type": "data", "data": {"fields": ["F"]}}
}
```
"""

_INTERNAL_FLOW_GUIDE = """\
# Internal Flow Post-Processing

## Key Analyses
1. **Pressure drop** — extract_stats on inlet vs outlet
2. **Flow distribution** — slice at multiple cross-sections
3. **Wall shear stress** — render wallShearStress on walls
4. **Recirculation** — streamlines in problematic regions

## Tips
- Compute pressure drop: inlet_mean_p - outlet_mean_p
- Use Threshold to highlight low-velocity (stagnation) regions
"""

_MULTIPHASE_GUIDE = """\
# Multiphase Flow Post-Processing

## Key Analyses
1. **Free surface** — contour(field="alpha.water", isovalues=[0.5])
2. **Volume fraction** — render(field="alpha.water", colormap="Blue to Red Rainbow")
3. **Sloshing** — animate for time evolution
4. **Interface area** — integrate iso-surface
5. **Multi-field comparison** — split_animate for synchronized views

## Tips
- alpha.water = 0.5 is the conventional free surface location
- Use "Blue to Red Rainbow" colormap for volume fraction
- For sloshing: animate with time_range to capture the motion
- Use split_animate to show alpha.water + pressure side-by-side with time-series graphs
"""

_THERMAL_GUIDE = """\
# Thermal Analysis Post-Processing

## Key Analyses
1. **Temperature distribution** — render(field="T", colormap="Inferno")
2. **Heat flux** — compute gradient of T, then surface integral
3. **Nusselt number** — requires wall temperature gradient
4. **Thermal boundary layer** — plot_over_line normal to heated wall

## Tips
- Use "Inferno" or "Black-Body Radiation" colormap for temperature
- Heat transfer coefficient: h = -k * dT/dn / (T_wall - T_bulk)
"""

_STATIC_FEA_GUIDE = """\
# Static FEA Post-Processing

## Key Analyses
1. **Deformation** — WarpByVector with displacement field
2. **Stress distribution** — render von_mises_stress
3. **Critical regions** — Threshold above yield stress
4. **Reaction forces** — IntegrateVariables on fixed boundaries

## Tips
- Scale factor for WarpByVector: use 10-100x for small deformations
- Compare max von Mises stress against material yield strength
"""

_MODAL_FEA_GUIDE = """\
# Modal Analysis Post-Processing

## Key Analyses
1. **Mode shapes** — WarpByVector with each mode's displacement
2. **Frequency response** — extract eigenfrequencies from metadata
3. **Effective mass** — identify dominant modes

## Tips
- Each timestep typically corresponds to one mode
- Scale factor should emphasize the mode shape geometry
"""

_VIZ_GUIDE = """\
# Visualization Best Practices

## Colormap Selection
| Data Type | Recommended | Avoid |
|-----------|-------------|-------|
| Diverging (centered on zero) | Cool to Warm | Jet |
| Sequential (0 to max) | Viridis, Inferno | Rainbow |
| Categorical | Qualitative sets | Sequential |

## Camera Tips
- **isometric**: Good default for 3D overview
- **front/top/right**: Best for 2D slices
- Adjust zoom if geometry is very elongated

## Resolution
- 1920x1080: Standard HD (default)
- 3840x2160: 4K for publications
- 800x600: Quick preview

## Publication Quality
- Use Viridis or Cool to Warm (colorblind-safe)
- Enable scalar_bar for quantitative reference
- White background: background=[1, 1, 1]
"""
