---
name: cfd-postprocess
description: |
  CFD simulation post-processing automation. Use when the user asks to
  visualize simulation results, render pressure/velocity fields, create
  contour plots, slice views, streamlines, or animations from OpenFOAM,
  DualSPHysics, or VTK-based simulation output files.
  Triggers: "시뮬레이션 결과", "CFD 후처리", "압력 분포", "유동 시각화",
  "render", "slice", "contour", "streamlines", "animate",
  ".foam", ".vtk", ".vtu", ".bi4", "OpenFOAM", "DualSPHysics"
allowed-tools: Read, Glob, Grep, Bash
---

# CFD Post-Processing Skill

You are a CFD post-processing expert. When the user wants to visualize or
analyze simulation results, follow this workflow:

## Step 1: Identify Data

1. Find simulation output files (`.foam`, `.vtk`, `.vtu`, `.vtp`, `.bi4`, `.case`, `.cgns`)
2. Use `inspect_data` MCP tool to check available fields, timesteps, and bounds
3. Report what's available to the user

## Step 2: Determine Visualization

Based on user intent, select appropriate tools:

| User Intent | MCP Tool | Key Parameters |
|-------------|----------|----------------|
| Field overview | `render` | field_name, colormap |
| Internal flow | `slice` | origin, normal |
| Iso-surface | `contour` | field_name, values |
| Flow patterns | `streamlines` | seed_type, num_seeds |
| Time evolution | `animate` | animation_type: "timestep" |
| Cross-section data | `plot_over_line` | point1, point2 |
| Force/flux | `integrate_surface` | field_name, boundary |
| Statistics | `extract_stats` | field_name |

## Step 3: Domain Presets

Apply appropriate presets based on simulation type:

- **External aero**: pressure coefficient, wall shear stress, streamlines
- **Internal flow**: velocity magnitude, pressure drop along line
- **Multiphase**: volume fraction iso-surface, interface tracking
- **Thermal**: temperature field, heat flux on boundaries
- **SPH particles**: pressure/velocity colormapped particles

## Step 4: Report

After generating visualizations:
1. Describe what the results show (physically meaningful interpretation)
2. Suggest additional views if relevant
3. Note any anomalies (non-physical values, divergence signs)
