# viznoir

[English](README.md) | [한국어](README.ko.md) | **中文** | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

> VTK is all you need. 面向AI代理的影院级科学可视化。

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*一句提示词 → 物理分析 → 影院级渲染 → LaTeX公式 → 出版级故事。*

</div>

<br>

## 这是什么

一个为AI代理提供VTK完整渲染管线的MCP服务器。无需ParaView GUI、无需Jupyter、无需显示服务器 — 代理读取仿真数据、应用滤波器、渲染影院级图像、导出动画，全部无头运行。

**兼容：** Claude Code · Cursor · Windsurf · Gemini CLI · 任何MCP客户端

## 快速开始

```bash
pip install mcp-server-viznoir
```

添加到MCP客户端配置：

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

然后向AI代理请求：

> *"打开cavity.foam，用影院级灯光渲染压力场，然后创建物理分解故事。"*

## 功能

| 类别 | 工具 |
|------|------|
| **渲染** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **滤波器** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **分析** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **探针** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **动画** | `animate` · `split_animate` |
| **比较** | `compare` · `compose_assets` |
| **导出** | `preview_3d` · `execute_pipeline` |

**22个工具** · **12个资源** · **4个提示词** · **50+文件格式** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## 架构

```
  提示词                     "渲染cavity.foam的压力场"
    │
  MCP服务器                   22工具 · 12资源 · 4提示词
    │
  VTK引擎                    读取器 → 滤波器 → 渲染器 → 相机
    │                        EGL/OSMesa无头 · 影院级灯光
  物理层                     拓扑分析 · 上下文解析
    │                        涡旋检测 · 驻点 · 边界条件
  动画                       7种物理预设 · 缓动 · 时间轴
    │                        过渡效果 · 合成 · 视频导出
  输出                       PNG · WebP · MP4 · GLTF · LaTeX
```

## 数据

| | |
|---|---|
| **22** MCP 工具 | **24** VTK 滤波器 |
| **10** 领域 | **19** 原生文件格式 |
| **6/6** VTK 数据类型 | **50+** 格式（通过 meshio） |

## 文档

**主页：** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**开发者文档：** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — 完整工具参考、领域画廊、架构指南

## 许可证

MIT
