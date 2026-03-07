# Reddit r/CFD Post

## Title

I built an MCP server that lets AI assistants post-process CFD results — headless VTK rendering from the terminal

## Flair

Software

## Body

After years of context-switching between my terminal and ParaView for quick post-processing checks, I built **viznoir** — a headless VTK-based MCP server that lets AI coding assistants render CFD results directly.

### The problem

You run a simulation overnight. Next morning you want to check: Did the flow converge? What does the pressure field look like at the outlet? Is there recirculation in that corner?

The typical workflow: open ParaView, load files, set up the pipeline, adjust the camera, export an image. For a quick sanity check, that's a lot of clicks.

### What viznoir does

It exposes 13 MCP tools that AI assistants can call:

- **render** — Load any VTK/OpenFOAM result and render a field to PNG
- **slice** / **clip** — Cut through your domain at any plane
- **contour** — Extract isosurfaces (e.g., Q-criterion vortex structures)
- **streamlines** — Seed and trace flow paths
- **animate** — Generate time-series animations
- **inspect_data** — Get field names, ranges, cell counts without rendering

### OpenFOAM example

```
"Load my OpenFOAM case at ./cavity/cavity.foam,
 render the pressure field, then slice at y=0.05"
```

The AI reads the .foam file, calls `render` and `slice`, returns PNG images inline. No GUI needed.

### Technical details

- **Not a ParaView wrapper** — uses VTK Python API directly
- **GPU EGL headless** — runs on servers without X11/display
- **50+ formats** — VTK, .foam, STL, CGNS, Exodus, EnSight, meshio bridge
- **331 tests**, 13 tools, 10 resources, MIT license
- Docker image with NVIDIA EGL for GPU clusters

### Install

```bash
pip install mcp-server-viznoir
```

Works with Claude Code (as a plugin), Cursor, Codex CLI, or any MCP-compatible client.

- GitHub: https://github.com/kimimgo/viznoir
- Landing page: https://kimimgo.github.io/viznoir

I'd love feedback from the CFD community — especially on which post-processing workflows you'd want automated. The biggest limitation right now is that it's only been validated on VTK example datasets, not large-scale industrial meshes (10M+ cells). If anyone wants to test with real cases, I'd be very interested in the results.

## Posting Notes

- Flair: Software
- Best time: Tue-Thu, 10:00 AM EST
- Cross-post potential: r/computationalengineering
