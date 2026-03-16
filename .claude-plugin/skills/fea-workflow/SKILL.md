---
name: fea-workflow
description: >-
  FEA post-processing workflow skill. Guides AI agents through finite element
  analysis visualization: stress distribution, deformation, mode shapes, and
  yield detection. Maps FEA domain vocabulary to viznoir MCP tool calls.
  Triggers: FEA, structural, stress, deformation, displacement, von Mises,
  yield, mode shape, 응력, 변형, 항복, 모드 형상
---

# FEA Post-Processing Workflow

## Standard Sequence
1. `inspect_data` → identify displacement, stress, strain fields
2. `cinematic_render(field="von_mises_stress", colormap="Cool to Warm")` → stress overview
3. `execute_pipeline` with WarpByVector → deformation visualization
4. `execute_pipeline` with Threshold(von_mises > yield) → critical regions
5. `extract_stats` → max stress, max displacement values

## WarpByVector Pattern
```json
{
  "source": {"file": "FILE_PATH"},
  "pipeline": [
    {"filter": "WarpByVector", "params": {"vector": "displacement", "scale_factor": 10.0}}
  ],
  "output": {"type": "image", "render": {"field": "von_mises_stress", "colormap": "Cool to Warm"}}
}
```
Scale factor: 10-100x for small deformations, 1x for large.

## Vocabulary → Tool Mapping
| Expert says | Tool | Params |
|-------------|------|--------|
| stress, 응력 집중 | cinematic_render | field="von_mises_stress" |
| deformation, 변형 | execute_pipeline | WarpByVector + render |
| yield exceeded, 항복 | execute_pipeline | Threshold(von_mises > yield_stress) |
| mode shape | cinematic_render | per-timestep displacement |
