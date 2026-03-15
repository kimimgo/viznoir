# viznoir

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | **日本語** | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

> VTK is all you need. AIエージェントのためのシネマ品質科学可視化。

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*プロンプト一行 → 物理解析 → シネマティックレンダリング → LaTeX数式 → 出版品質ストーリー。*

</div>

<br>

## 何ができるか

AIエージェントにVTKレンダリングパイプライン全体へのアクセスを提供するMCPサーバー。ParaView GUIなし、Jupyterなし、ディスプレイサーバーなし — エージェントがシミュレーションデータを読み込み、フィルターを適用し、シネマ品質の画像をレンダリングし、アニメーションをエクスポートします。すべてヘッドレスで。

**対応：** Claude Code · Cursor · Windsurf · Gemini CLI · すべてのMCPクライアント

## クイックスタート

```bash
pip install mcp-server-viznoir
```

MCPクライアント設定に追加：

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

AIエージェントに依頼：

> *「cavity.foamを開いて、シネマティック照明で圧力場をレンダリングして、物理分解ストーリーを作成して。」*

## 機能

| カテゴリ | ツール |
|----------|--------|
| **レンダリング** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **フィルター** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **解析** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **プロービング** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **アニメーション** | `animate` · `split_animate` |
| **比較** | `compare` · `compose_assets` |
| **エクスポート** | `preview_3d` · `execute_pipeline` |

**22ツール** · **12リソース** · **4プロンプト** · **50+ファイル形式** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## アーキテクチャ

```
  プロンプト                  「cavity.foamの圧力をレンダリングして」
    │
  MCPサーバー                 22ツール · 12リソース · 4プロンプト
    │
  VTKエンジン                 リーダー → フィルター → レンダラー → カメラ
    │                        EGL/OSMesaヘッドレス · シネマティック照明
  物理レイヤー                トポロジー解析 · コンテキストパース
    │                        渦検出 · よどみ点 · 境界条件
  アニメーション              7つの物理プリセット · イージング · タイムライン
    │                        トランジション · コンポジター · 動画エクスポート
  出力                       PNG · WebP · MP4 · GLTF · LaTeX
```

## 数値

| | |
|---|---|
| **22** MCP ツール | **24** VTK フィルター |
| **10** ドメイン | **19** ネイティブファイル形式 |
| **6/6** VTK データ型 | **50+** フォーマット（meshio 経由） |

## ドキュメント

**ホームページ：** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**開発者ドキュメント：** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — 完全ツールリファレンス、ドメインギャラリー、アーキテクチャガイド

## ライセンス

MIT
