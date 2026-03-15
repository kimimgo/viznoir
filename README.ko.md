# viznoir

[English](README.md) | **한국어** | [中文](README.zh.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Español](README.es.md) | [Português](README.pt.md)

> VTK is all you need. AI 에이전트를 위한 시네마 퀄리티 과학 시각화.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

<br>

<div align="center">

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

*프롬프트 한 줄 → 물리 분석 → 시네마틱 렌더 → LaTeX 수식 → 출판 품질 스토리.*

</div>

<br>

## 무엇을 하는가

AI 에이전트에게 VTK 렌더링 파이프라인 전체를 제공하는 MCP 서버. ParaView GUI 없이, Jupyter 없이, 디스플레이 서버 없이 — 에이전트가 시뮬레이션 데이터를 읽고, 필터를 적용하고, 시네마틱 이미지를 렌더링하고, 애니메이션을 내보냅니다. 전부 헤드리스.

**호환:** Claude Code · Cursor · Windsurf · Gemini CLI · 모든 MCP 클라이언트

## 빠른 시작

```bash
pip install mcp-server-viznoir
```

MCP 클라이언트 설정에 추가:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

그리고 AI에게 요청:

> *"cavity.foam 열고, 압력 필드를 시네마틱 조명으로 렌더링한 다음, 물리 분해 스토리 만들어줘."*

## 기능

| 카테고리 | 도구 |
|----------|------|
| **렌더링** | `render` · `cinematic_render` · `batch_render` · `volume_render` |
| **필터** | `slice` · `contour` · `clip` · `streamlines` · `pv_isosurface` |
| **분석** | `inspect_data` · `inspect_physics` · `extract_stats` · `analyze_data` |
| **프로빙** | `plot_over_line` · `integrate_surface` · `probe_timeseries` |
| **애니메이션** | `animate` · `split_animate` |
| **비교** | `compare` · `compose_assets` |
| **내보내기** | `preview_3d` · `execute_pipeline` |

**22 도구** · **12 리소스** · **4 프롬프트** · **50+ 파일 포맷** (OpenFOAM, VTK, CGNS, Exodus, STL, glTF, …)

## 아키텍처

```
  프롬프트                   "cavity.foam에서 압력 렌더링해줘"
    │
  MCP 서버                   22 도구 · 12 리소스 · 4 프롬프트
    │
  VTK 엔진                   리더 → 필터 → 렌더러 → 카메라
    │                        EGL/OSMesa 헤드리스 · 시네마틱 조명
  물리 레이어                 토폴로지 분석 · 컨텍스트 파싱
    │                        와류 탐지 · 정체점 · 경계조건 파싱
  애니메이션                  7 물리 프리셋 · 이징 · 타임라인
    │                        전환 효과 · 합성 · 비디오 내보내기
  출력                       PNG · WebP · MP4 · GLTF · LaTeX
```

## 수치

| | |
|---|---|
| **22** MCP 도구 | **24** VTK 필터 |
| **10** 도메인 | **19** 네이티브 파일 포맷 |
| **6/6** VTK 데이터 타입 | **50+** 포맷 (meshio) |

## 문서

**홈페이지:** [kimimgo.github.io/viznoir](https://kimimgo.github.io/viznoir/)

**개발자 문서:** [kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs) — 전체 도구 레퍼런스, 도메인 갤러리, 아키텍처 가이드

## 라이선스

MIT
