# Example 01: CFD External Aerodynamics — Pressure and Velocity

**Domain**: CFD External Aerodynamics
**Typical data**: DrivAerML, WindsorML, or any `.vtu`/`.foam` surface/volume mesh
**Key fields**: `p` (pressure), `U` (velocity magnitude)

## Overview

This workflow extracts pressure coefficient distribution and velocity field from an external aerodynamics CFD result. Steps progress from data discovery to statistical summary.

```
inspect_data → render (pressure) → slice (velocity mid-plane) → streamlines → extract_stats
```

## Step 1: Discover Available Fields

```json
{
  "tool": "inspect_data",
  "arguments": {
    "file_path": "/data/aero/surface.vtu"
  }
}
```

Expected output: field names (`p`, `U`, `nut`), bounds, cell/point counts, timestep list.

## Step 2: Render Pressure Field

```json
{
  "tool": "render",
  "arguments": {
    "file_path": "/data/aero/surface.vtu",
    "field_name": "p",
    "colormap": "Cool to Warm",
    "camera": "front",
    "purpose": "preview"
  }
}
```

Use `viznoir://colormaps` to browse available colormaps. `Cool to Warm` is standard for pressure coefficient.

## Step 3: Velocity Mid-Plane Slice

```json
{
  "tool": "slice",
  "arguments": {
    "file_path": "/data/aero/volume.vtu",
    "field_name": "U",
    "origin": [0.0, 0.0, 0.0],
    "normal": [0.0, 1.0, 0.0],
    "colormap": "Turbo",
    "purpose": "preview"
  }
}
```

The `normal: [0,1,0]` produces the symmetry (y=0) plane. Adjust `origin` to shift the slice.

## Step 4: Streamlines for Flow Topology

```json
{
  "tool": "streamlines",
  "arguments": {
    "file_path": "/data/aero/volume.vtu",
    "field_name": "U",
    "n_seeds": 150,
    "colormap": "Viridis",
    "purpose": "preview"
  }
}
```

Streamlines reveal separation zones, recirculation, and wake structure. Increase `n_seeds` for denser coverage.

## Step 5: Field Statistics Summary

```json
{
  "tool": "extract_stats",
  "arguments": {
    "file_path": "/data/aero/surface.vtu",
    "fields": ["p", "U"]
  }
}
```

Returns min, max, mean, and std for each field. Use these values to set manual colormap ranges in subsequent renders.

## Tips

- Use `purpose: "publish"` for final 1080p renders submitted to reports.
- For `.foam` files (OpenFOAM), add `"timestep": "latest"` to all tool calls.
- See `viznoir://pipelines/cfd` for the full CFD pipeline DSL reference.
- See `../aerodynamics_workflow.json` for an extended 7-step workflow including force integration and comparison.
