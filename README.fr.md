# viznoir

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | **Français** | [Español](README.es.md) | [Português](README.pt.md)

> VTK is all you need. Visualisation scientifique cinématographique pour agents IA.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*Un prompt → analyse physique → rendus cinématographiques → équations LaTeX → publication prête.*

</div>

<br>

## Ce qu'il fait

Un serveur MCP qui donne aux agents IA un accès complet au pipeline de rendu VTK — pas d'interface ParaView, pas de Jupyter, pas de serveur d'affichage. Votre agent lit les données de simulation, applique des filtres, produit des images cinématographiques et exporte des animations — tout en mode headless.

**Compatible avec :** Claude Code · Cursor · Windsurf · Gemini CLI · tout client MCP

## Démarrage rapide

```bash
pip install mcp-server-viznoir
```

Ajouter à la configuration du client MCP :

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

Puis demander à votre agent IA :

> *« Ouvre cavity.foam, rends le champ de pression avec un éclairage cinématographique, puis crée une histoire de décomposition physique. »*

## Capacités

| Catégorie | Outils |
|-----------|--------|
| **Rendu** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **Filtres** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **Analyse** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **Sondage** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **Animation** | `animate` · `split_animate` |
| **Comparaison** | `compare` · `compose_assets` |
| **Export** | `preview_3d` · `execute_pipeline` |

**22 outils** · **12 ressources** · **4 prompts** · **50+ formats de fichiers** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## Architecture

```
  prompt                     "Rends la pression de cavity.foam"
    │
  Serveur MCP                22 outils · 12 ressources · 4 prompts
    │
  Moteur VTK                 lecteurs → filtres → moteur de rendu → caméra
    │                        EGL/OSMesa headless · éclairage cinématographique
  Couche physique            analyse topologique · parsing contextuel
    │                        détection de tourbillons · points d'arrêt
  Animation                  7 préréglages physiques · easing · timeline
    │                        transitions · compositeur · export vidéo
  Sortie                     PNG · WebP · MP4 · GLTF · LaTeX
```

## Chiffres

| | |
|---|---|
| **22** outils MCP | **24** filtres VTK |
| **10** domaines | **19** formats de fichiers natifs |
| **6/6** types de données VTK | **50+** formats via meshio |

## Documentation

**Page d'accueil :** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**Documentation développeur :** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — référence complète des outils, galerie de domaines, guide d'architecture

## Licence

MIT
