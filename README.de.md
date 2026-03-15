# viznoir

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | **Deutsch** | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

> VTK is all you need. Kinoqualität-Wissenschaftsvisualisierung für KI-Agenten.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*Ein Prompt → Physikanalyse → Kinematisches Rendering → LaTeX-Gleichungen → Publikationsreifer Bericht.*

</div>

<br>

## Was es macht

Ein MCP-Server, der KI-Agenten vollen Zugriff auf die VTK-Rendering-Pipeline gibt — kein ParaView-GUI, keine Jupyter-Notebooks, kein Display-Server. Ihr Agent liest Simulationsdaten, wendet Filter an, rendert kinoqualitative Bilder und exportiert Animationen — alles headless.

**Kompatibel mit:** Claude Code · Cursor · Windsurf · Gemini CLI · jedem MCP-Client

## Schnellstart

```bash
pip install mcp-server-viznoir
```

Zur MCP-Client-Konfiguration hinzufügen:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

Dann den KI-Agenten fragen:

> *„Öffne cavity.foam, rendere das Druckfeld mit kinematischer Beleuchtung und erstelle eine Physik-Zerlegungsgeschichte."*

## Fähigkeiten

| Kategorie | Werkzeuge |
|-----------|-----------|
| **Rendering** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **Filter** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **Analyse** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **Abtastung** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **Animation** | `animate` · `split_animate` |
| **Vergleich** | `compare` · `compose_assets` |
| **Export** | `preview_3d` · `execute_pipeline` |

**22 Werkzeuge** · **12 Ressourcen** · **4 Prompts** · **50+ Dateiformate** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## Architektur

```
  Prompt                     "Rendere den Druck aus cavity.foam"
    │
  MCP-Server                 22 Werkzeuge · 12 Ressourcen · 4 Prompts
    │
  VTK-Engine                 Reader → Filter → Renderer → Kamera
    │                        EGL/OSMesa headless · Kinematische Beleuchtung
  Physik-Schicht             Topologieanalyse · Kontextparsing
    │                        Wirbelerkennung · Staupunkte
  Animation                  7 Physik-Presets · Easing · Timeline
    │                        Übergänge · Compositing · Videoexport
  Ausgabe                    PNG · WebP · MP4 · GLTF · LaTeX
```

## Zahlen

| | |
|---|---|
| **22** MCP-Werkzeuge | **24** VTK-Filter |
| **10** Domänen | **19** native Dateiformate |
| **6/6** VTK-Datentypen | **50+** Formate über meshio |

## Dokumentation

**Homepage:** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**Entwicklerdokumentation:** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — Vollständige Werkzeugreferenz, Domänengalerie, Architekturguide

## Lizenz

MIT
