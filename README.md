# viznoir

**English** | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

> VTK is all you need. Cinema-quality science visualization for AI agents.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)
[![Mentioned in Awesome VTK](https://awesome.re/mentioned-badge.svg)](https://github.com/tkoyama010/awesome-vtk)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*One prompt → physics analysis → cinematic renders → LaTeX equations → publication-ready story.*

</div>

<br>

## What it does

An MCP server that gives AI agents full access to VTK's rendering pipeline — no ParaView GUI, no Jupyter notebooks, no display server. Your agent reads simulation data, applies filters, renders cinema-quality images, and exports animations, all headless.

**Works with:** Claude Code · Cursor · Windsurf · Gemini CLI · any MCP client

## Quick Start

```bash
pip install mcp-server-viznoir
```

Add to your MCP client config:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

Then ask your AI agent:

> *"Open cavity.foam, render the pressure field with cinematic lighting, then create a physics decomposition story."*

## Capabilities

| Category | Tools |
|----------|-------|
| **Rendering** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **Filters** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **Analysis** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **Probing** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **Animation** | `animate` · `split_animate` |
| **Comparison** | `compare` · `compose_assets` |
| **Export** | `preview_3d` · `execute_pipeline` |

**22 tools** · **12 resources** · **4 prompts** · **50+ file formats** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## Architecture

```
  prompt                    "Render pressure from cavity.foam"
    │
  MCP Server                22 tools · 12 resources · 4 prompts
    │
  VTK Engine                readers → filters → renderer → camera
    │                       EGL/OSMesa headless · cinematic lighting
  Physics Layer             topology analysis · context parsing
    │                       vortex detection · stagnation points
  Animation                 7 physics presets · easing · timeline
    │                       transitions · compositor · video export
  Output                    PNG · WebP · MP4 · GLTF · LaTeX
```

## Numbers

| | |
|---|---|
| **22** MCP tools | **1489+** tests |
| **12** resources | **97%** coverage |
| **10** domains | **50+** file formats |
| **7** animation presets | **17** easing functions |

## Documentation

**Homepage:** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**Developer docs:** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — full tool reference, domain gallery, architecture guide

## License

MIT
