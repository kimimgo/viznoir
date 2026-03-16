---
name: sph-workflow
description: >-
  SPH/DualSPHysics post-processing workflow skill. Guides AI agents through
  particle method visualization: fluid filtering, sloshing animations,
  isosurface mesh extraction, and particle distribution analysis. Maps SPH
  domain vocabulary to viznoir MCP tool calls. Triggers: SPH, DualSPHysics,
  particles, sloshing, fluid, Type field, bi4, 입자, 슬로싱, 유체
---

# SPH Post-Processing Workflow

## Standard Sequence
1. `inspect_data` → identify Velocity, Pressure, Type fields, timestep count
2. `cinematic_render(field="Velocity", colormap="Viridis")` → particle overview
3. `execute_pipeline` with Threshold(Type, 0, 0) → fluid-only particles
4. `animate(mode="timesteps")` → time evolution
5. `pv_isosurface` → smooth surface mesh from particles (if needed)

## Fluid-Only Filtering
DualSPHysics uses Type field: 0=fluid, >0=boundary. To show fluid only:
```json
{
  "source": {"file": "FILE_PATH"},
  "pipeline": [
    {"filter": "Threshold", "params": {"field": "Type", "range": [0, 0]}}
  ],
  "output": {"type": "image", "render": {"field": "Velocity", "colormap": "Viridis"}}
}
```

## Vocabulary → Tool Mapping
| Expert says | Tool | Params |
|-------------|------|--------|
| particles, 입자 | render or cinematic_render | field="Velocity" |
| fluid only | execute_pipeline | Threshold(Type, 0, 0) |
| sloshing, 슬로싱 | animate | mode="timesteps", field="Velocity" |
| wave, 파도 | animate | mode="timesteps" |
| isosurface mesh | pv_isosurface | bi4_dir, output_dir |
