# viznoir

[English](README.md) | **한국어**

> VTK is all you need. AI 에이전트를 위한 시네마 퀄리티 과학 시각화.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

![Science Storytelling](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/cavity_story.webp)

프롬프트 한 줄 → 물리 분석 → 시네마틱 렌더 → LaTeX 수식 → 출판 품질 스토리.

## 빠른 시작

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
| **22** MCP 도구 | **1489+** 테스트 |
| **12** 리소스 | **97%** 커버리지 |
| **10** 도메인 | **50+** 파일 포맷 |
| **7** 애니메이션 프리셋 | **17** 이징 함수 |

## 문서

전체 도구 레퍼런스, 예제, 개발자 가이드: **[kimimgo.github.io/viznoir/docs](https://kimimgo.github.io/viznoir/docs)**

## 라이선스

MIT
