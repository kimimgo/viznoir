# Thermal Analysis Workflow

A complete 8-step conjugate heat transfer (CHT) post-processing workflow.

See the full pipeline definition: [`examples/thermal_analysis.json`](https://github.com/kimimgo/viznoir/blob/main/examples/thermal_analysis.json)

## Steps

### 1. Inspect data

```
> "Inspect the heatsink.foam file"
```

Discover available fields (T, U, p), timesteps, and mesh bounds.

### 2. Temperature overview

```
> "Render temperature with Inferno colormap at the latest timestep"
```

Cinematic-quality rendering with auto-framing and 3-point lighting.

### 3. Temperature cross-section

```
> "Slice the heatsink horizontally at z=0.005 showing temperature"
```

Reveals internal temperature gradients through the heat sink fins.

### 4. Wall temperature profile

```
> "Plot temperature along the heated wall from x=0 to x=0.1"
```

Extract 1D profile for validation against analytical solutions.

### 5. Heat flux computation

Uses the Pipeline DSL to compute temperature gradient magnitude:

```json
{
  "pipeline": [
    {"filter": "Gradient", "params": {"field": "T", "result_name": "gradT"}},
    {"filter": "Calculator", "params": {"expression": "mag(gradT)", "result_name": "heatFluxMag"}}
  ]
}
```

Heat flux: q = -k * gradT (gradient magnitude as proxy).

### 6. Statistics summary

```
> "Extract stats for T and U fields"
```

Min/max/mean/std of temperature and velocity.

### 7. Surface integration

```
> "Integrate temperature over the heated wall boundary"
```

Compute average wall temperature for Nusselt number calculation.

### 8. Time evolution

```
> "Animate temperature from cold start to steady state at 5x speed"
```

GIF animation showing thermal development.

## Recommended Colormaps

| Field | Colormap | Reason |
|-------|----------|--------|
| Temperature | Inferno | Perceptually uniform, heat intuition |
| Temperature (publication) | Black-Body Radiation | Physically motivated |
| Heat flux | Plasma | High contrast for gradients |
| Velocity | Viridis | Colorblind-safe default |
