# viznoir

**English** | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp" alt="viznoir showcase" width="720" />
  <br>
  <strong>VTK is all you need.</strong><br>
  Autonomous engineering analysis for AI agents.<br>
  <sub>Traditional post-processors show what you ask for. viznoir tells you what you need to see.</sub>
</p>

<p align="center">
  <b><a href="#quick-start">Quickstart</a></b> · <b><a href="https://kimimgo.github.io/viznoir/docs">Docs</a></b> · <b><a href="https://github.com/kimimgo/viznoir">GitHub</a></b>
</p>

<p align="center">
  <a href="https://github.com/kimimgo/viznoir/actions/workflows/ci.yml"><img src="https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/mcp-server-viznoir/"><img src="https://img.shields.io/pypi/v/mcp-server-viznoir" alt="PyPI"></a>
  <a href="https://github.com/kimimgo/viznoir/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/kimimgo/viznoir/stargazers"><img src="https://img.shields.io/github/stars/kimimgo/viznoir?style=flat" alt="Stars"></a>
</p>

[![viznoir MCP server](https://glama.ai/mcp/servers/kimimgo/viznoir/badges/card.svg)](https://glama.ai/mcp/servers/kimimgo/viznoir)

---

## What is viznoir?

An MCP server that gives AI agents **autonomous engineering analysis** — not just rendering. The agent inspects your simulation data, reasons about the physics, identifies what matters, and delivers actionable engineering insights with cinema-quality visuals. No ParaView GUI, no Jupyter notebooks, no display server. **All headless.**

---

## How it works

<table>
<tr>
<td align="center" width="33%">
<h3>01 &mdash; Inspect</h3>
<b>Point to your data</b><br><br>
<code>inspect_data("beam.vtu")</code><br>
<sub>AI discovers fields, topology, physics context</sub>
</td>
<td align="center" width="33%">
<h3>02 &mdash; Reason</h3>
<b>AI decides what matters</b><br><br>
<em>"Found stress tensor + displacement. Computing von Mises, safety factor, detecting hotspots..."</em>
</td>
<td align="center" width="33%">
<h3>03 &mdash; Deliver</h3>
<b>Engineering insights + cinema visuals</b><br><br>
SF maps &middot; hotspot annotations &middot; deformation overlays &middot; publication figures
</td>
</tr>
</table>

---

## The Autoresearch Pattern

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — AI agents that autonomously research, iterate, and build.

**Traditional post-processing:**
```
Engineer opens ParaView → selects field → adjusts colormap → positions camera → exports image
                          ↑ repeat for every view ↑
```

**viznoir autoresearch:**
```
Engineer: "Analyze this FEA result"
    → AI inspects data (fields, topology, mesh quality)
    → AI reasons (stress tensor → principal stresses, safety factor, failure criterion)
    → AI identifies hotspots, yield regions, critical load paths
    → AI renders publication figures with engineering annotations
    → AI delivers: "Max von Mises 342 MPa at node 12847, SF = 1.46. Two regions below SF 1.5."
```

This works because viznoir is built in two layers:

| Layer | Role | Analogy |
|-------|------|---------|
| **Engine** (L1) | Computation primitives — tensor decomposition, failure criteria, safety factor, deformation analysis | The hands |
| **Harness** (L3) | AI skill that reasons about data, selects the right analysis, composes primitives into workflows | The brain |

The engine provides **what** to compute. The harness decides **when** and **why**.

---

## Works with

<table>
<tr>
<td align="center" width="16%"><sub><b>Claude Code</b></sub></td>
<td align="center" width="16%"><sub><b>Cursor</b></sub></td>
<td align="center" width="16%"><sub><b>Windsurf</b></sub></td>
<td align="center" width="16%"><sub><b>Gemini CLI</b></sub></td>
<td align="center" width="16%"><sub><b>Codex</b></sub></td>
<td align="center" width="16%"><sub><b>Any MCP Client</b></sub></td>
</tr>
</table>

<p align="center"><em>If it speaks MCP, it reasons.</em></p>

---

## Right for you if

- ✅ You run CFD/FEA simulations and want **autonomous** post-processing
- ✅ You're an ME engineer who wants AI to analyze stress, deformation, and safety — not just render them
- ✅ You want cinema-quality renders without learning ParaView
- ✅ You need headless visualization in CI/CD pipelines
- ✅ You want one prompt to go from raw data to engineering insights + publication figures
- ✅ You process 50+ file formats (OpenFOAM, CGNS, Exodus, STL, ...)

---

## Features

<table>
<tr>
<td align="center" width="33%">
<h3>🎬 Cinema Render</h3>
3-point lighting, SSAO, FXAA, PBR materials. Publication-ready in one call.
</td>
<td align="center" width="33%">
<h3>🔬 Physics Analysis</h3>
Vortex detection, tensor decomposition, principal stresses, safety factor, failure criteria.
</td>
<td align="center" width="33%">
<h3>📊 Data Extraction</h3>
Line plots, surface integrals, time-series probes, statistical summaries.
</td>
</tr>
<tr>
<td align="center" width="33%">
<h3>🎞️ Animation</h3>
7 physics presets, 17 easing functions, scene transitions, video export.
</td>
<td align="center" width="33%">
<h3>🧩 50+ Formats</h3>
OpenFOAM, VTK, CGNS, Exodus, STL, glTF, NetCDF, PLOT3D, and more.
</td>
<td align="center" width="33%">
<h3>🤖 Autoresearch Harness</h3>
AI reasons about your data, selects analysis, delivers engineering insights autonomously.
</td>
</tr>
<tr>
<td align="center" width="33%">
<h3>📐 Adaptive Resolution</h3>
analyze 480p, preview 720p, publish 1080p. Context-aware quality scaling.
</td>
<td align="center" width="33%">
<h3>🔄 Pipeline DSL</h3>
Compose multi-step filter chains into a single executable pipeline.
</td>
<td align="center" width="33%">
<h3>🖥️ Headless GPU</h3>
EGL/OSMesa rendering, Docker support, no display server needed.
</td>
</tr>
</table>

---

## Without viznoir vs. With viznoir

<table>
<tr>
<th width="50%">Without viznoir</th>
<th width="50%">With viznoir</th>
</tr>
<tr>
<td>❌ Open ParaView GUI, click through menus, export manually</td>
<td>✅ One prompt, headless, cinema-quality, automated</td>
</tr>
<tr>
<td>❌ Write 200-line VTK Python scripts for each visualization</td>
<td>✅ Natural language — the agent writes the pipeline</td>
</tr>
<tr>
<td>❌ No rendering in CI/CD — need a display server</td>
<td>✅ EGL/OSMesa headless — runs anywhere, including Docker</td>
</tr>
<tr>
<td>❌ Manual camera placement, lighting, colormap tuning</td>
<td>✅ PCA auto-camera, 3-point lighting, adaptive resolution</td>
</tr>
<tr>
<td>❌ Manually compute safety factor, find hotspots, check yield regions</td>
<td>✅ AI inspects data → computes SF, detects hotspots, reports critical regions</td>
</tr>
<tr>
<td>❌ Post-processor shows what you ask for — you must know what to look for</td>
<td>✅ viznoir tells you what you need to see — autonomous engineering analysis</td>
</tr>
</table>

---

## What viznoir is NOT

| | |
|---|---|
| **Not a simulation solver** | It visualizes results, it does not run CFD/FEA solvers |
| **Not ParaView** | No GUI — pure headless API designed for AI agents |
| **Not a Jupyter widget** | MCP server, not an interactive notebook extension |
| **Not a mesh generator** | It reads meshes, it does not create them |

---

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

> *"Analyze beam.vtu — find stress concentrations, compute safety factor against 250 MPa yield, and show me the critical regions."*

---

## Numbers

**22** MCP tools · **12** resources · **4** prompts · **1505+** tests
**97%** coverage · **50+** file formats · **7** animation presets · **17** easing functions

---

## Documentation

**Homepage** — [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**Developer docs** — [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — full tool reference, domain gallery, architecture guide

---

## Contributing

Contributions are welcome. Please open an issue first to discuss what you would like to change.

```bash
pip install -e ".[dev]"
pytest --cov=viznoir -q
ruff check src/ tests/
```

---

## License

[MIT](LICENSE)

---

## Star History

<p align="center">
  <a href="https://star-history.com/#kimimgo/viznoir&Date">
    <img src="https://api.star-history.com/svg?repos=kimimgo/viznoir&type=Date" alt="Star History Chart" width="600" />
  </a>
</p>

---

<p align="center">
  <em>Open source under MIT. Built for engineers who'd rather reason than click.</em>
</p>