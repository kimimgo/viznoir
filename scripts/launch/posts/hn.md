# Hacker News — Show HN Post

## Title

Show HN: viznoir – MCP server that lets AI render CFD/FEA simulations headlessly

## Body

I built an MCP server that lets Claude, Cursor, and other AI coding assistants
render engineering simulation results without a GUI.

One tool call = one PNG of your CFD/FEA data.

- 18 tools (render, slice, contour, clip, streamlines, animate, compare, stats)
- Headless VTK rendering (GPU EGL / CPU OSMesa)
- Pipeline DSL for complex multi-step workflows
- 1048 tests, 99% coverage, 5 quality gates on every PR
- Docker GPU support, pip installable

```
pip install mcp-server-viznoir
```

The problem: post-processing simulation results (OpenFOAM, VTK, EnSight) requires
launching ParaView or similar GUIs. This doesn't work in headless CI/CD pipelines,
SSH sessions, or AI coding workflows.

viznoir solves this by wrapping VTK's rendering pipeline as MCP tools.
Your AI assistant can inspect data, render slices, create animations,
and extract statistics — all through natural language.

Demo: 8.8M cell automotive CFD (DrivAerML) rendered in 4 seconds via Claude Code.

GitHub: https://github.com/kimimgo/viznoir
Docs: https://kimimgo.github.io/viznoir
PyPI: https://pypi.org/project/mcp-server-viznoir/

## Timing

Monday (Launch Day) — 한국시간 자정 = EST 10:00 AM
