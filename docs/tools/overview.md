# Tools Overview

viznoir provides 18 MCP tools organized by function:

## Visualization Tools

| Tool | Description |
|------|-------------|
| `render` | Single-field PNG screenshot |
| `slice` | Cut-plane visualization |
| `contour` | Iso-surface visualization |
| `clip` | Clipped region visualization |
| `streamlines` | Vector field flow visualization |
| `cinematic_render` | Publication-quality render (SSAO, PBR, 3-point lighting) |
| `compare` | Side-by-side or diff comparison of two datasets |
| `batch_render` | Render multiple fields in one call |
| `preview_3d` | Export to glTF/glB for interactive 3D browser viewing |

## Data Extraction Tools

| Tool | Description |
|------|-------------|
| `inspect_data` | File metadata — fields, timesteps, bounds |
| `extract_stats` | Min/max/mean/std for fields |
| `plot_over_line` | Sample values along a line |
| `integrate_surface` | Force/flux integration over surfaces |
| `probe_timeseries` | Sample field at a point across timesteps |

## Animation Tools

| Tool | Description |
|------|-------------|
| `animate` | Time series or camera orbit animation |
| `split_animate` | Multi-pane synchronized animation (GIF) |

## Advanced Tools

| Tool | Description |
|------|-------------|
| `execute_pipeline` | Full pipeline DSL for complex workflows |
| `pv_isosurface` | DualSPHysics bi4 to VTK surface mesh |
