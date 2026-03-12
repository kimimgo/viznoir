# viznoir

**English** | [한국어](README.ko.md)

> VTK is all you need. Cinema-quality science visualization for AI agents.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

One prompt → physics analysis → cinematic renders → LaTeX equations → publication-ready story.

## Quick Start

```bash
pip install mcp-server-viznoir
```

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

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

Full tool reference, examples, and developer guide: **[kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs)**

## License

MIT
