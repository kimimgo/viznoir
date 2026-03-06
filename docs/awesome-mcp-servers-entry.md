# awesome-mcp-servers PR Draft

## Entry (add to Science category, alphabetical order)

```markdown
- [kimimgo/parapilot](https://github.com/kimimgo/parapilot) 🐍 🏠 🐧 - Headless CAE post-processing with VTK: render, slice, contour, streamlines, cinematic visualization for CFD/FEA simulations (18 tools, 50+ formats).
```

## PR Title

```
Add parapilot - headless CAE/CFD post-processing MCP server
```

## PR Body

```markdown
## What does this server do?

parapilot is a headless CAE post-processing MCP server that lets AI assistants
(Claude Code, Cursor, Gemini CLI) render CFD/FEA simulation results without a
GUI. It uses VTK directly to produce PNG screenshots, statistics, and animations
from OpenFOAM, VTK, CGNS, and 50+ other formats.

## Key features

- **18 tools**: inspect, render, slice, contour, clip, streamlines, cinematic_render,
  compare, probe_timeseries, batch_render, preview_3d, extract_stats, plot_over_line,
  integrate_surface, animate, split_animate, execute_pipeline, pv_isosurface
- **11 resources** + **3 prompts** for guided workflows
- **Headless rendering**: EGL (GPU) + OSMesa (CPU) — no GUI required
- **Publication quality**: PBR materials, SSAO, FXAA, 3-point lighting, auto-camera
- **50+ file formats** via VTK + meshio fallback
- **Docker images**: GPU (EGL) and CPU-only (OSMesa)
- **1128 tests, 99% coverage**, CodeQL + pip-audit security scanning
- **Claude Code plugin**: `claude install kimimgo/parapilot`

## Category

Science (simulation post-processing / scientific visualization)

## Links

- **Repository**: https://github.com/kimimgo/parapilot
- **PyPI**: https://pypi.org/project/mcp-server-parapilot/
- **Docs**: https://kimimgo.github.io/parapilot/docs/
```
