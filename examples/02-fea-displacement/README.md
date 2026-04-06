# Example 02: Structural FEA — Displacement and Stress

**Domain**: Structural Finite Element Analysis (FEA)
**Typical data**: CalculiX `.vtu`, Abaqus ODB export, ANSYS `.vtu`
**Key fields**: `vonMises` (stress), `displacement` (nodal displacement vector)

## Overview

This workflow visualizes stress concentration and deformation in a structural FEA result. The contour step isolates yield-threshold zones for safety margin assessment.

```
inspect_data → render (stress) → contour (yield isosurface) → clip (section) → extract_stats → plot_over_line
```

## Step 1: Inspect Mesh and Fields

```json
{
  "tool": "inspect_data",
  "arguments": {
    "file_path": "/data/fea/bracket.vtu"
  }
}
```

Check that `vonMises` and `displacement` fields are present. Note the stress range — it informs the contour isovalue.

## Step 2: Render von Mises Stress

```json
{
  "tool": "render",
  "arguments": {
    "file_path": "/data/fea/bracket.vtu",
    "field_name": "vonMises",
    "colormap": "Turbo",
    "camera": "isometric",
    "purpose": "preview"
  }
}
```

`Turbo` is preferred for stress because it gives clear visual separation near the maximum. Use `purpose: "publish"` for reports.

## Step 3: Contour at Yield Threshold

```json
{
  "tool": "contour",
  "arguments": {
    "file_path": "/data/fea/bracket.vtu",
    "field_name": "vonMises",
    "values": [250.0],
    "colormap": "Reds",
    "purpose": "preview"
  }
}
```

Set `values` to the material yield stress (MPa). The resulting isosurface marks the yield boundary.

## Step 4: Cross-Section Clip

```json
{
  "tool": "clip",
  "arguments": {
    "file_path": "/data/fea/bracket.vtu",
    "field_name": "vonMises",
    "origin": [0.05, 0.0, 0.0],
    "normal": [1.0, 0.0, 0.0],
    "colormap": "Turbo",
    "purpose": "preview"
  }
}
```

Clips the mesh at `x = 0.05` to reveal internal stress gradients.

## Step 5: Field Statistics

```json
{
  "tool": "extract_stats",
  "arguments": {
    "file_path": "/data/fea/bracket.vtu",
    "fields": ["vonMises", "displacement"]
  }
}
```

Use the max von Mises value to compute the safety factor: `SF = yield_stress / vonMises_max`.

## Step 6: Stress Profile Along Load Path

```json
{
  "tool": "plot_over_line",
  "arguments": {
    "file_path": "/data/fea/bracket.vtu",
    "field_name": "vonMises",
    "point1": [0.0, 0.0, 0.0],
    "point2": [0.1, 0.0, 0.0],
    "resolution": 100
  }
}
```

Returns a CSV-style table of stress vs arc length along the critical load path.

## Tips

- Use `viznoir://filters` to check available VTK filters (e.g., `Warp By Vector` for deformed shape).
- Use `viznoir://pipelines/fea` for the full FEA pipeline DSL reference.
- See `../structural_fea.json` for a complete 7-step workflow with deformed shape visualization.
- The fixture file `tests/fixtures/vtu/notch_disp.vtu` demonstrates displacement field on a notched specimen.
