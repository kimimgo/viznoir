# viznoir

**English** | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp" alt="viznoir showcase" width="720" />
  <br>
  <strong>VTK is all you need.</strong><br>
  Cinema-quality science visualization for AI agents.
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

---

## What is viznoir?

An MCP server that gives AI agents full access to VTK's rendering pipeline — no ParaView GUI, no Jupyter notebooks, no display server. Your agent reads simulation data, applies physics filters, renders cinema-quality images, and exports animations. **All headless.**

---

## How it works

<table>
<tr>
<td align="center" width="33%">
<h3>01</h3>
<b>Point to your data</b><br><br>
<code>inspect_data("cavity.foam")</code>
</td>
<td align="center" width="33%">
<h3>02</h3>
<b>Ask in natural language</b><br><br>
<em>"Render pressure with cinematic lighting"</em>
</td>
<td align="center" width="33%">
<h3>03</h3>
<b>Get cinema-quality output</b><br><br>
PNG &middot; MP4 &middot; glTF &middot; LaTeX
</td>
</tr>
</table>

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

<p align="center"><em>If it speaks MCP, it renders.</em></p>

---

## Right for you if

- ✅ You run CFD/FEA simulations and want automated post-processing
- ✅ You want cinema-quality renders without learning ParaView
- ✅ You need headless visualization in CI/CD pipelines
- ✅ You want one prompt to go from raw data to publication figures
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
Vortex detection, stagnation points, gradient stats, Reynolds number.
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
<h3>🤖 Agent Harness</h3>
<code>auto_postprocess</code> meta-tool with MCP sampling for full autonomy.
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

> *"Open cavity.foam, render the pressure field with cinematic lighting, then create a physics decomposition story."*

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
  <em>Open source under MIT. Built for engineers who'd rather prompt than click.</em>
</p>
