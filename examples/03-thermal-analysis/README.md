# Example 03: Thermal / CHT Analysis — Temperature Field

**Domain**: Conjugate Heat Transfer (CHT), Thermal Simulation
**Typical data**: OpenFOAM `.foam`, Fluent `.vtu`, heatsink VTI
**Key fields**: `T` (temperature in K), `U` (coolant velocity), `p` (pressure)

## Overview

This workflow inspects a thermal dataset, renders temperature volumetrically, slices through the domain, and plots a temperature profile for validation against analytical solutions.

```
inspect_data → volume_render (temperature) → slice (cross-section) → plot_over_line → extract_stats
```

## Step 1: Inspect Data

```json
{
  "tool": "inspect_data",
  "arguments": {
    "file_path": "/data/thermal/heatsink.foam",
    "timestep": "latest"
  }
}
```

Confirm field `T` is available and note the temperature range (e.g., 293 K ambient to 380 K hot spot).

## Step 2: Volume Render — Temperature Distribution

```json
{
  "tool": "volume_render",
  "arguments": {
    "file_path": "/data/thermal/heatsink.foam",
    "field_name": "T",
    "colormap": "Inferno",
    "timestep": "latest",
    "purpose": "preview"
  }
}
```

`Inferno` is perceptually uniform and maps naturally to heat (dark = cool, bright = hot). Use `Black-Body Radiation` for publication.

## Step 3: Horizontal Temperature Slice

```json
{
  "tool": "slice",
  "arguments": {
    "file_path": "/data/thermal/heatsink.foam",
    "field_name": "T",
    "origin": [0.0, 0.0, 0.005],
    "normal": [0.0, 0.0, 1.0],
    "colormap": "Inferno",
    "timestep": "latest",
    "purpose": "preview"
  }
}
```

The z-normal slice at `z = 0.005` cuts through the mid-height of the heatsink fins.

## Step 4: Temperature Profile Along Wall

```json
{
  "tool": "plot_over_line",
  "arguments": {
    "file_path": "/data/thermal/heatsink.foam",
    "field_name": "T",
    "point1": [0.0, 0.0, 0.0],
    "point2": [0.1, 0.0, 0.0],
    "resolution": 200,
    "timestep": "latest"
  }
}
```

Returns temperature vs position along the heated wall. Compare against the analytical 1D conduction solution to validate mesh convergence.

## Step 5: Field Statistics

```json
{
  "tool": "extract_stats",
  "arguments": {
    "file_path": "/data/thermal/heatsink.foam",
    "fields": ["T", "U"],
    "timestep": "latest"
  }
}
```

Use `T_max` to check that the hot spot stays below the component's maximum rated temperature.

## Tips

- For time-dependent simulations, add `"mode": "timesteps"` to `animate` to visualize the temperature evolution (see `../thermal_analysis.json`).
- Use `viznoir://case-presets` for pre-configured thermal colormaps and camera positions.
- `heat_flux = -k * grad(T)` — use `execute_pipeline` with the `Gradient` filter to derive heat flux from `T`.
- See `../thermal_analysis.json` for an extended 8-step workflow including heat flux computation and animation.
