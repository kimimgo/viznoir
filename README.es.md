# viznoir

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | **Español** | [Português](README.pt.md)

> VTK is all you need. Visualización científica de calidad cinematográfica para agentes de IA.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*Un prompt → análisis físico → renderizados cinematográficos → ecuaciones LaTeX → historia lista para publicar.*

</div>

<br>

## Qué hace

Un servidor MCP que da a los agentes de IA acceso completo al pipeline de renderizado de VTK — sin GUI de ParaView, sin Jupyter, sin servidor de pantalla. Tu agente lee datos de simulación, aplica filtros, renderiza imágenes de calidad cinematográfica y exporta animaciones — todo sin cabeza.

**Compatible con:** Claude Code · Cursor · Windsurf · Gemini CLI · cualquier cliente MCP

## Inicio rápido

```bash
pip install mcp-server-viznoir
```

Agregar a la configuración del cliente MCP:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

Luego pedir al agente de IA:

> *"Abre cavity.foam, renderiza el campo de presión con iluminación cinematográfica y crea una historia de descomposición física."*

## Capacidades

| Categoría | Herramientas |
|-----------|-------------|
| **Renderizado** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **Filtros** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **Análisis** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **Sondeo** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **Animación** | `animate` · `split_animate` |
| **Comparación** | `compare` · `compose_assets` |
| **Exportación** | `preview_3d` · `execute_pipeline` |

**22 herramientas** · **12 recursos** · **4 prompts** · **50+ formatos de archivo** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## Arquitectura

```
  prompt                     "Renderiza la presión de cavity.foam"
    │
  Servidor MCP               22 herramientas · 12 recursos · 4 prompts
    │
  Motor VTK                  lectores → filtros → renderizador → cámara
    │                        EGL/OSMesa headless · iluminación cinematográfica
  Capa física                análisis topológico · parsing de contexto
    │                        detección de vórtices · puntos de estancamiento
  Animación                  7 presets físicos · easing · timeline
    │                        transiciones · compositor · exportación de video
  Salida                     PNG · WebP · MP4 · GLTF · LaTeX
```

## Números

| | |
|---|---|
| **22** herramientas MCP | **24** filtros VTK |
| **10** dominios | **19** formatos de archivo nativos |
| **6/6** tipos de datos VTK | **50+** formatos vía meshio |

## Documentación

**Página principal:** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**Documentación para desarrolladores:** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — referencia completa de herramientas, galería de dominios, guía de arquitectura

## Licencia

MIT
