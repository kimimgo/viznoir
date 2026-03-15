# viznoir

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | **Português**

> VTK is all you need. Visualização científica de qualidade cinematográfica para agentes de IA.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*Um prompt → análise física → renderizações cinematográficas → equações LaTeX → história pronta para publicação.*

</div>

<br>

## O que faz

Um servidor MCP que dá aos agentes de IA acesso completo ao pipeline de renderização do VTK — sem GUI do ParaView, sem Jupyter, sem servidor de display. Seu agente lê dados de simulação, aplica filtros, renderiza imagens de qualidade cinematográfica e exporta animações — tudo headless.

**Compatível com:** Claude Code · Cursor · Windsurf · Gemini CLI · qualquer cliente MCP

## Início rápido

```bash
pip install mcp-server-viznoir
```

Adicionar à configuração do cliente MCP:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

Então peça ao agente de IA:

> *"Abra cavity.foam, renderize o campo de pressão com iluminação cinematográfica e crie uma história de decomposição física."*

## Capacidades

| Categoria | Ferramentas |
|-----------|------------|
| **Renderização** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **Filtros** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **Análise** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **Sondagem** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **Animação** | `animate` · `split_animate` |
| **Comparação** | `compare` · `compose_assets` |
| **Exportação** | `preview_3d` · `execute_pipeline` |

**22 ferramentas** · **12 recursos** · **4 prompts** · **50+ formatos de arquivo** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## Arquitetura

```
  prompt                     "Renderize a pressão do cavity.foam"
    │
  Servidor MCP               22 ferramentas · 12 recursos · 4 prompts
    │
  Motor VTK                  leitores → filtros → renderizador → câmera
    │                        EGL/OSMesa headless · iluminação cinematográfica
  Camada física              análise topológica · parsing de contexto
    │                        detecção de vórtices · pontos de estagnação
  Animação                   7 presets físicos · easing · timeline
    │                        transições · compositor · exportação de vídeo
  Saída                      PNG · WebP · MP4 · GLTF · LaTeX
```

## Números

| | |
|---|---|
| **22** ferramentas MCP | **24** filtros VTK |
| **10** domínios | **19** formatos de arquivo nativos |
| **6/6** tipos de dados VTK | **50+** formatos via meshio |
| **2 ms** renderização GPU | 720p, RTX 4090 ([benchmark](benchmarks/)) |

## Documentação

**Página principal:** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**Documentação para desenvolvedores:** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — referência completa de ferramentas, galeria de domínios, guia de arquitetura

## Licença

MIT
