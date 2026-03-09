# viznoir

**English** | [한국어](README.ko.md)

> Headless CAE/CFD post-processing for AI terminals. No ParaView. No GUI.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kimimgo/viznoir/branch/main/graph/badge.svg)](https://codecov.io/gh/kimimgo/viznoir)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

![Science Storytelling: Physics Decomposition](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*One pipeline: `inspect_physics` → insight extraction → `cinematic_render` × 4 → LaTeX equations → `compose_assets` story*

## Quick Start

**Claude Code plugin:**

```bash
claude install kimimgo/viznoir
```

Then in a conversation:

> "Render the pressure field from cavity/cavity.foam with a jet colormap"

**pip:**

```bash
pip install mcp-server-viznoir
```

**Docker (GPU headless):**

```bash
docker compose up -d
```

Requires NVIDIA Container Toolkit. For CPU-only: `docker compose up viznoir-cpu -d`

**MCP config for Cursor / other clients:**

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

## What You Get

- **Headless Rendering** — EGL/OSMesa off-screen rendering.
  No display, no GUI, no ParaView install needed.

- **22 MCP Tools** — inspect, render, slice, contour, clip, streamlines,
  cinematic render, compare, animate, analyze data, compose stories, and more.

- **Science Storytelling** — Analyze datasets for physics insights,
  render LaTeX equations, compose cinematic story layouts, and export videos.

- **50+ Formats** — OpenFOAM, VTK, CGNS, STL, PLY, OBJ, Exodus, Ensight
  via VTK readers + meshio.

## Science Storytelling

Not just rendering — viznoir extracts physics insights and composes them into stories.

```
"Analyze the cavity flow and show me what's happening"

→ inspect_physics: 20 stagnation points, ω range [-15.2, +19.6]/s
→ cinematic_render × 4: velocity, pressure, vorticity, temperature
→ compose_assets: LaTeX equations + insight labels + story layout
```

![Multi-Physics Grid](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_grid.webp)

## See It In Action

All renders from single MCP tool calls — no post-processing.

| | | |
|---|---|---|
| ![Automotive CFD](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/drivaerml_cp.webp) | ![Medical CT](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/ct_head_contour.webp) | ![Blood Flow](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/streamlines.webp) |
| Automotive CFD | Medical CT | Blood flow |
| ![HVAC](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/office_flow.webp) | ![Structural FEA](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/arch_structural.webp) | ![Stanford Dragon](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/dragon.webp) |
| HVAC airflow | Structural FEA | Stanford Dragon |

[Full Gallery →](https://kimimgo.github.io/viznoir)

## vs Alternatives

| Feature | viznoir | ParaView (pvpython) | PyVista | VTK Python |
|---------|-----------|---------------------|---------|------------|
| MCP Integration | Native 22 tools | — | — | — |
| Headless | EGL/OSMesa | pvpython | Yes | Manual |
| Docker | GPU + CPU | Complex | — | — |
| Natural Language | AI-first | — | — | — |
| File Formats | 50+ (meshio) | 70+ | 30+ | ~20 |
| Installation | pip install | System package | pip install | pip install |
| Science Storytelling | LaTeX + timeline + video | — | — | — |
| Tests | 1315+ (97% cov) | N/A | Yes | N/A |

## Contributing

```bash
git clone https://github.com/kimimgo/viznoir
cd viznoir && pip install -e ".[dev]"
pytest  # 1315+ tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT
