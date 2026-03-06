# Reddit Launch Posts

---

## r/CFD

### Title
I built an MCP server that lets AI render OpenFOAM/VTK results headlessly — no ParaView GUI needed

### Body
Hey r/CFD,

I've been working on **parapilot**, an open-source MCP server that turns VTK rendering
into simple tool calls for AI coding assistants (Claude, Cursor, etc.).

**The problem**: Post-processing simulation results usually means launching ParaView,
clicking through menus, and manually setting up views. This doesn't work in headless
environments, CI/CD pipelines, or when you just want a quick slice of your flow field.

**What it does**:
- `render`: Visualize any VTK-compatible file (OpenFOAM .foam, VTK, EnSight, CGNS)
- `slice` / `clip` / `contour`: Standard CFD post-processing operations
- `streamlines`: Flow visualization with auto-seeded stream tracers
- `extract_stats`: Min/max/mean of any field
- `animate`: Time series or orbit animations
- `compare`: Side-by-side or diff comparison of two cases

All headless via EGL (GPU) or OSMesa (CPU). Just `pip install mcp-server-parapilot`.

Tested on DrivAerML (8.8M cells) — renders a full pressure contour in ~4 seconds.

1048 tests, 99% coverage, MIT license.

GitHub: https://github.com/kimimgo/parapilot

Would love feedback from the CFD community!

---

## r/OpenFOAM

### Title
Headless post-processing for .foam files via Claude/Cursor — no ParaView needed

### Body
Built an MCP server called **parapilot** that lets AI assistants render OpenFOAM
results headlessly.

Instead of opening ParaView, you can just ask your AI:
- "Render the pressure field on a slice at x=0.5"
- "Show me the velocity streamlines"
- "Extract min/max temperature over all timesteps"

It reads `.foam` files directly using VTK readers, applies filters (slice, clip,
contour, streamlines), and renders to PNG — all without a display server.

Works with Claude Code, Cursor, Windsurf, or any MCP-compatible client.

```bash
pip install mcp-server-parapilot
```

18 tools, 1048 tests, GPU EGL or CPU OSMesa rendering.
MIT license, contributions welcome.

https://github.com/kimimgo/parapilot

---

## r/MachineLearning

### Title
MCP server for scientific visualization — AI-native CAE post-processing (18 tools, 1048 tests)

### Body
Sharing **parapilot**, an MCP server that gives AI coding assistants the ability
to render engineering simulation data (CFD, FEA, scientific visualization).

**Why this matters for ML/AI**:
The Model Context Protocol (MCP) lets AI assistants call external tools.
parapilot implements 18 tools for headless VTK rendering, so your AI can:
- Inspect simulation datasets (fields, bounds, timesteps)
- Render visualizations to PNG
- Apply physics-aware filters (slice, contour, streamlines)
- Extract quantitative data (statistics, line plots, surface integrals)
- Create animations and comparisons

**Technical details**:
- Built on FastMCP 2.0 + VTK 9.4
- Headless rendering via EGL (GPU) or OSMesa (CPU)
- Pipeline DSL for complex multi-step workflows
- Cinematic rendering with PBR materials, 3-point lighting, SSAO
- 1048 tests, 99% coverage, MIT license

This fills a gap in the MCP ecosystem — scientific visualization is <0.03%
of the 18,000+ MCP servers that exist today.

GitHub: https://github.com/kimimgo/parapilot
