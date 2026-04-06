# viznoir Example Gallery

viznoir is a VTK-based MCP server that exposes 22 tools for cinema-quality science visualization. AI agents can call these tools directly — no ParaView GUI needed.

Each example below shows a realistic post-processing workflow as a sequence of MCP tool calls. Copy the JSON blocks into any MCP client (Claude Desktop, Cursor, Zed, etc.) to reproduce the analysis.

## How to Use

1. Connect to viznoir via your MCP client.
2. Point `file_path` at your simulation output.
3. Run each step in order — `inspect_data` first, then visualization tools.
4. Explore available options via viznoir resources: `viznoir://colormaps`, `viznoir://filters`, `viznoir://cameras`.

## Example Index

| # | Directory | Domain | Tools Used |
|---|-----------|--------|------------|
| 1 | [01-cfd-pressure](01-cfd-pressure/) | CFD External Aerodynamics | `inspect_data`, `render`, `slice`, `streamlines`, `extract_stats` |
| 2 | [02-fea-displacement](02-fea-displacement/) | Structural FEA | `inspect_data`, `render`, `contour`, `clip`, `extract_stats`, `plot_over_line` |
| 3 | [03-thermal-analysis](03-thermal-analysis/) | Thermal / CHT | `inspect_data`, `volume_render`, `slice`, `plot_over_line`, `extract_stats` |
| 4 | [04-medical-imaging](04-medical-imaging/) | Medical CT / MRI | `inspect_data`, `volume_render`, `clip`, `cinematic_render` |
| 5 | [05-openfoam-cavity](05-openfoam-cavity/) | OpenFOAM CFD | `inspect_data`, `inspect_physics`, `render`, `animate`, `split_animate` |

## Workflow Patterns

| Pattern | When to Use |
|---------|-------------|
| `inspect_data` → `render` | Quick field overview |
| `inspect_data` → `slice` → `streamlines` | Flow analysis |
| `inspect_data` → `contour` → `clip` | Stress hotspot isolation |
| `inspect_data` → `volume_render` | Volumetric scalar data (CT, temperature) |
| `inspect_data` → `animate` → `split_animate` | Time-series with synchronized graphs |
| `inspect_data` → `cinematic_render` | Publication / presentation quality |

## Existing JSON Workflows

The root `examples/` directory also contains three standalone JSON pipeline files:

- `aerodynamics_workflow.json` — Full 7-step external aerodynamics pipeline
- `structural_fea.json` — Structural bracket analysis with stress hotspot detection
- `thermal_analysis.json` — CHT heatsink with time-series animation

These can be passed to the `execute_pipeline` MCP tool directly.
