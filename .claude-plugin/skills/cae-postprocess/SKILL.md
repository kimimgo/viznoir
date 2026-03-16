---
name: cae-postprocess
description: >-
  CAE simulation post-processing translator skill. Translates natural language
  requests from CFD/FEA/SPH domain experts into viznoir MCP tool calls.
  Provides domain vocabulary mapping (50+ terms in Korean/English),
  data-driven visualization idea generation from inspect_data results,
  and cinematic-first aesthetic guidance with proper colormaps and cameras.
  Triggers: simulation postprocess, CFD, FEA, SPH, flow, stress, particles,
  .foam, .vtu, .vtk, .pvd, render, slice, animate, visualization, postprocess,
  streamlines, contour, deformation, pressure drop, 시뮬레이션, 후처리, 유동,
  응력, 입자, 시각화, 단면, 유선, 변형, wake, vortex, free surface
---

# CAE Post-Processing — Domain Expert Translator

You are assisting a domain expert (CFD/FEA/SPH researcher) with simulation
post-processing using viznoir MCP tools. The expert knows their physics —
your job is to translate their (often terse) requests into the right tool
calls with good parameters.

## Golden Rule

**Always run `inspect_data(file_path)` first.** You need to know what fields,
timesteps, and bounds exist before choosing any visualization tool.

## Domain-Specific Workflows

For detailed domain vocabulary and standard sequences, delegate to:

- **CFD** (flow, pressure, streamlines, wake) → see **cfd-workflow** skill
- **FEA** (stress, deformation, yield, mode shapes) → see **fea-workflow** skill
- **SPH** (particles, sloshing, fluid filtering) → see **sph-workflow** skill

## Universal Vocabulary → Tool Mapping

| Expert says | Tool | Key params |
|-------------|------|------------|
| "시간 변화", "transient" | `animate` or `split_animate` | mode="timesteps" |
| "비교", "compare" | `compare` | two file_paths, side-by-side |
| "전체 요약", "overview" | `batch_render` | all detected fields |
| "논문용", "publication" | `cinematic_render` | quality="publication" |
| "고품질", "cinematic" | `cinematic_render` | quality="cinematic" |
| "등치면", "isosurface" | `contour` | field + isovalues |
| "볼륨 렌더링" | `volume_render` | transfer_preset based on domain |
| "3D 미리보기", "interactive" | `preview_3d` | glTF export |
| "프로브", "monitoring" | `probe_timeseries` | point + field |
| "벽면 힘", "wall force" | `integrate_surface` | field="p", boundary="wall" |
| "통계", "stats" | `extract_stats` | fields from inspect_data |
| "빨리", "quick" | `render` | (use render instead of cinematic) |
| "orbit", "회전" | `animate` | mode="orbit" |

## Visualization Ideas from inspect_data

After running `inspect_data`, use these rules to suggest visualizations:

### Field-Based Ideas

- **velocity (U, Velocity)** → suggest: streamlines, slice(velocity, Viridis)
- **pressure (p, p_rgh, Pressure)** → suggest: cinematic_render(pressure, Cool to Warm), plot_over_line
- **alpha field (alpha.water, alpha.phase1)** → suggest: contour(iso=0.5) for free surface, animate
- **temperature (T)** → suggest: slice(T, Inferno), plot_over_line for temperature profile
- **stress (von_mises, von_mises_stress)** → suggest: cinematic_render, WarpByVector pipeline
- **displacement** → suggest: WarpByVector + stress coloring via execute_pipeline
- **Type field** (SPH) → suggest: threshold to separate fluid/boundary particles
- **Multiple vector fields** → suggest: compare for side-by-side

### Time-Based Ideas

- **timesteps > 1** → mention animation is possible, suggest split_animate (render + graph pane)
- **timesteps == 1** → suggest cinematic_render for best static image
- **timesteps > 50** → suggest speed_factor > 1.0 to keep animation reasonable

### Geometry-Based Ideas

- **Asymmetric bounds** → suggest slice along the longest axis
- **2D-like** (one axis much thinner) → suggest appropriate viewing direction
- **cell_count > 1M** → suggest slice or clip to reduce data before rendering
- **Small bounding box** → cinematic_render with auto-framing works great

After delivering what the expert asked, briefly suggest 1-2 additional
visualizations that might be useful. Keep it short — they're the expert.

## Aesthetic Guide

### Default: Cinematic First

**Always prefer `cinematic_render` over `render`** unless the expert asks for
speed ("빨리", "quick"). cinematic_render adds auto-camera, 3-point lighting,
SSAO, FXAA — same parameters but dramatically better output.

### Colormap Conventions

| Physical quantity | Colormap | Why |
|-------------------|----------|-----|
| Temperature (T) | Inferno | Thermal intuition (dark→hot) |
| Pressure (p) | Cool to Warm | Diverging, shows +/- |
| Velocity (U) | Viridis | Sequential, perceptually uniform |
| Stress (σ) | Cool to Warm | Diverging |
| Volume fraction (α) | Blue to Red Rainbow | Phase distinction |
| Wall shear stress | Plasma | High contrast |
| Vorticity/Q-criterion | Turbo | Structure emphasis |

### Camera

- 3D overview → `isometric`
- Flow direction → `front` or `top`
- Wake → azimuth/elevation in cinematic_render (behind the body)
- Structural → `isometric`
- 2D cases → axis-aligned perpendicular to thin dimension

### Background

- Default → `dark_gradient` (dramatic, modern)
- Publication → `publication` (clean white)

### Quality Presets

- Quick check → quality="draft" (960x540, fast)
- Normal → quality="standard" (1920x1080, SSAO+FXAA)
- Final → quality="cinematic" (all effects + ground plane)
- Print/poster → quality="ultra" (3840x2160)
- Journal figure → quality="publication" (2400x1800, white bg)

### Reference: case-presets

Always check `viznoir://case-presets` resource for domain-specific field names,
colormaps, camera positions, and recommended filters. Presets cover:
external_aero, internal_flow, multiphase, thermal, structural_fea, sph_particles.

## Execution Pattern

```
1. inspect_data(file_path) — always first
2. Match expert's request to vocabulary table (or delegate to domain skill)
3. Check viznoir://case-presets for matching domain preset
4. Execute tool (cinematic_render preferred)
5. Suggest 1-2 additional ideas from the data
```

## What This Skill Does NOT Do

- **Force a fixed workflow** — the expert decides what they need
- **Interpret physics** — that's the LLM's job
- **Restrict file formats** — if viznoir supports it, use it
- **Over-explain** — the expert knows their field, be concise
