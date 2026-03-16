---
name: cfd-workflow
description: >-
  CFD post-processing workflow skill. Guides AI agents through computational
  fluid dynamics visualization: pressure/velocity fields, streamlines, wall
  shear stress, boundary layers, and pressure drop analysis. Maps CFD domain
  vocabulary (Korean/English) to viznoir MCP tool calls. Triggers: CFD,
  flow visualization, pressure drop, streamlines, boundary layer, wake,
  recirculation, wall shear, 유동, 압력강하, 유선, 경계층, 후류
---

# CFD Post-Processing Workflow

## Standard Sequence
1. `inspect_data` → identify velocity (U), pressure (p), turbulence (k, epsilon)
2. `cinematic_render(field="p", colormap="Cool to Warm")` → pressure overview
3. `cinematic_render(field="U", colormap="Viridis")` or `slice` at mid-plane
4. `streamlines(vector_field="U")` → flow patterns, wake, recirculation
5. `plot_over_line` → pressure drop (inlet→outlet), velocity profiles
6. `extract_stats` → quantitative summary (min/max/mean)

## Vocabulary → Tool Mapping
| Expert says | Tool | Params |
|-------------|------|--------|
| wake, 후류 | streamlines | seed downstream of body |
| pressure drop, 압력강하 | plot_over_line | field="p", point1=inlet, point2=outlet |
| boundary layer, 경계층 | slice + plot_over_line | wall-normal direction |
| wall shear | cinematic_render | field="wallShearStress", colormap="Plasma" |
| recirculation, 재순환 | streamlines | seed in low-velocity region |
| turbulence | slice | field="k" or "nut", colormap="Turbo" |

## Colormaps
- Pressure: Cool to Warm (diverging)
- Velocity: Viridis (sequential)
- Temperature: Inferno (thermal)
- Wall shear: Plasma (high contrast)
- Turbulence: Turbo (structure emphasis)
