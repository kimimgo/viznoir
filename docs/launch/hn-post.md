# Hacker News — Show HN Post

## Title

Show HN: viznoir – Headless CAE post-processing server that speaks MCP

## Body

I built viznoir because I got tired of opening ParaView every time I needed to check CFD results. It's a headless VTK-based post-processing server that exposes 13 MCP tools — so AI coding assistants (Claude Code, Cursor, Codex CLI) can render slices, contours, streamlines, and animations directly from simulation data.

**What it does:**

- Reads 50+ mesh formats (VTK, OpenFOAM .foam, STL, CGNS, Exodus...)
- GPU EGL headless rendering — no X server, no GUI
- 13 tools: render, slice, clip, contour, streamlines, animate, and more
- Works as a Claude Code plugin, Cursor MCP server, or standalone

**Tech stack:** Python, VTK (direct API, not ParaView wrapper), FastMCP 2.0, Docker w/ NVIDIA EGL

**Install:**

```bash
pip install mcp-server-viznoir
```

**Try it:**

```json
// .mcp.json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

Then ask your AI assistant: "Render a slice of my simulation at z=0.5 with the pressure field"

Landing page: https://kimimgo.github.io/viznoir
GitHub: https://github.com/kimimgo/viznoir

331 tests, MIT license. Feedback welcome.

## Tags / Notes

- Category: Show HN
- Best posting time: Tue-Thu, 10:00 AM EST (HN peak engagement)
- Character count: ~290 words (HN prefers concise, technical posts)
