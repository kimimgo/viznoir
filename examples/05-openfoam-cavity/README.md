# Example 05: OpenFOAM Cavity — Lid-Driven Flow Time Series

**Domain**: OpenFOAM CFD (incompressible laminar flow)
**Data**: `tests/fixtures/foam/OpenFOAM/cavity/case.foam`
**Key fields**: `U` (velocity), `p` (pressure)
**Timesteps**: 0, 0.5, 1, 1.5, 2, 2.5 s

## Overview

The lid-driven cavity is the canonical OpenFOAM tutorial. This workflow uses the bundled test fixture to demonstrate the full viznoir pipeline: physics inspection, field rendering, time-series animation, and synchronized multi-pane animation.

```
inspect_data → inspect_physics → render (velocity) → animate (time series) → split_animate (multi-pane)
```

## Resources

Before running, fetch the available pipeline presets:

```
viznoir://pipelines/cfd          — CFD pipeline DSL reference
viznoir://pipelines/split-animate — split_animate layout reference
viznoir://case-presets           — OpenFOAM case configuration presets
```

## Step 1: Inspect Data

```json
{
  "tool": "inspect_data",
  "arguments": {
    "file_path": "tests/fixtures/foam/OpenFOAM/cavity/case.foam"
  }
}
```

Expected output: fields `U` and `p`, timesteps `[0, 0.5, 1.0, 1.5, 2.0, 2.5]`, 3D cell count.

## Step 2: Inspect Physics (L2 Topology + L3 Context)

```json
{
  "tool": "inspect_physics",
  "arguments": {
    "file_path": "tests/fixtures/foam/OpenFOAM/cavity/case.foam",
    "timestep": "latest"
  }
}
```

`inspect_physics` layers OpenFOAM boundary conditions, transport properties (nu, Re), and mesh quality metrics on top of the raw VTK topology. It also reports vortex cores and critical points.

## Step 3: Render Velocity Field

```json
{
  "tool": "render",
  "arguments": {
    "file_path": "tests/fixtures/foam/OpenFOAM/cavity/case.foam",
    "field_name": "U",
    "colormap": "Turbo",
    "camera": "front",
    "timestep": "latest",
    "purpose": "preview"
  }
}
```

The velocity magnitude at the final timestep shows the primary recirculation vortex.

## Step 4: Animate Time Series

```json
{
  "tool": "animate",
  "arguments": {
    "file_path": "tests/fixtures/foam/OpenFOAM/cavity/case.foam",
    "field_name": "U",
    "mode": "timesteps",
    "colormap": "Turbo",
    "fps": 6,
    "output_format": "gif"
  }
}
```

Produces a GIF showing vortex formation from t=0 to t=2.5 s. Adjust `fps` for slower/faster playback.

## Step 5: Multi-Pane Synchronized Animation

```json
{
  "tool": "split_animate",
  "arguments": {
    "file_path": "tests/fixtures/foam/OpenFOAM/cavity/case.foam",
    "field_name": "U",
    "layout": "2x1",
    "pane_fields": ["U", "p"],
    "colormaps": ["Turbo", "Cool to Warm"],
    "fps": 6,
    "output_format": "gif"
  }
}
```

Side-by-side animation: velocity (left) and pressure (right), synchronized across timesteps. See `viznoir://pipelines/split-animate` for 3- and 4-pane layout options.

## Tips

- Replace the fixture path with your own `.foam` file to run the same workflow on production data.
- For large cases, use `purpose: "preview"` (480p) during exploration and `purpose: "publish"` (1080p) for the final render.
- The cavity case also works with `probe_timeseries` to sample velocity at the cavity center `[0.05, 0.05, 0.005]` across all timesteps.
