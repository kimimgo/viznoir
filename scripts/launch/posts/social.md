# Social Media Launch Posts

---

## Twitter/X Post

Introducing viznoir — an open-source MCP server that lets AI assistants render CFD/FEA simulations headlessly.

18 tools. Headless VTK. One pip install.

Your AI can now slice, contour, animate, and extract stats from OpenFOAM/VTK data — no ParaView GUI needed.

pip install mcp-server-viznoir

https://github.com/kimimgo/viznoir

#MCP #CFD #OpenSource #AI

---

## LinkedIn Post

### AI Meets Computational Engineering: Introducing viznoir

Every computational engineer knows the workflow: run a simulation for hours (or days), then spend another chunk of time manually post-processing results in ParaView — clicking through menus, adjusting colormaps, setting up camera angles, exporting images. Multiply this by dozens of cases and it becomes a real bottleneck.

This problem gets worse in modern development environments. Headless servers, CI/CD pipelines, SSH sessions, and AI-assisted coding workflows have no display server. Traditional GUI-based post-processing simply doesn't work there.

I built **viznoir** to solve this.

viznoir is an open-source MCP (Model Context Protocol) server that turns VTK rendering into simple tool calls for AI coding assistants. Instead of launching a GUI, you describe what you want in natural language — and your AI assistant handles the rest.

**What it enables:**

- Render any VTK-compatible simulation data (OpenFOAM, EnSight, CGNS, VTK) to PNG
- Apply standard post-processing operations: slicing, clipping, contouring, streamlines
- Extract quantitative data: field statistics, line plots, surface integrals
- Create time series animations and case-by-case comparisons
- Cinematic-quality rendering with PBR materials, SSAO, and 3-point lighting

**Technical foundations:**

- Built on FastMCP 2.0 and VTK 9.4
- 18 specialized tools, each handling a distinct post-processing task
- Headless rendering via GPU (EGL) or CPU (OSMesa) — no display server required
- Pipeline DSL for orchestrating complex multi-step visualization workflows
- 1,048 tests at 99% coverage, with 5 quality gates on every PR
- Works with Claude Code, Cursor, Windsurf, and any MCP-compatible client

Validated on the DrivAerML benchmark (8.8M cells) — a full pressure contour renders in approximately 4 seconds.

Scientific visualization represents less than 0.03% of the 18,000+ MCP servers available today. viznoir aims to bridge the gap between computational engineering and AI-native tooling.

MIT licensed. Contributions and feedback welcome.

GitHub: https://github.com/kimimgo/viznoir
Documentation: https://kimimgo.github.io/viznoir
PyPI: https://pypi.org/project/mcp-server-viznoir/

#ComputationalEngineering #CFD #FEA #MCP #AIAssistants #OpenSource #PostProcessing #VTK #SimulationEngineering

---

## Discord/Slack Announcement

Hey everyone! Just released **viznoir** — an open-source MCP server that lets AI coding assistants (Claude, Cursor, Windsurf) render CFD/FEA simulation results headlessly. No ParaView GUI needed.

Ask your AI to visualize OpenFOAM or VTK data in natural language, and it handles the rendering for you.

**Key features:**
- 18 tools: render, slice, contour, clip, streamlines, animate, compare, stats, and more
- Headless VTK rendering (GPU EGL / CPU OSMesa)
- Pipeline DSL for multi-step workflows
- Cinematic rendering with PBR, SSAO, 3-point lighting
- 1,048 tests, 99% coverage, MIT license
- One-line install: `pip install mcp-server-viznoir`

Tested on DrivAerML (8.8M cells) — renders in ~4 seconds.

GitHub: https://github.com/kimimgo/viznoir
PyPI: https://pypi.org/project/mcp-server-viznoir/

Feedback, issues, and PRs all welcome!
