# viznoir

Headless CAE post-processing MCP server for AI coding assistants.

**viznoir** lets AI assistants (Claude Code, Cursor, Gemini CLI) render CFD/FEA simulation results without a GUI. It uses VTK directly to produce PNG screenshots, statistics, and animations from OpenFOAM, VTK, CGNS, and 30+ other formats.

## Key Features

- **18 MCP tools** — inspect, render, slice, contour, clip, streamlines, cinematic render, compare, animate, and more
- **11 MCP resources** — formats, filters, colormaps, cameras, presets, pipeline templates
- **Headless rendering** — GPU (EGL) or CPU (OSMesa), no display needed
- **Pipeline DSL** — declarative JSON filter chains for complex workflows
- **Physics-aware** — auto-detects field types and suggests optimal colormaps/ranges

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [Tools Overview](tools/overview.md)
- [API Reference](api/server.md)
- [GitHub](https://github.com/kimimgo/viznoir)
- [PyPI](https://pypi.org/project/mcp-server-viznoir/)
