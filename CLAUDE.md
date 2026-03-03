# parapilot

CAE post-processing plugin for AI coding assistants.

## Project Info
- **Group**: dev
- **Agent**: cc-kimtech
- **Repo**: kimimgo/parapilot
- **Language**: Python
- **MCP SDK**: fastmcp>=2.0.0
- **PyPI**: mcp-server-parapilot

## Purpose

개인 연구자를 위한 CAE 후처리 플러그인.
ParaView 헤드리스 렌더링 + meshio 형식 변환 + STL 분석을
Claude Code / Cursor / Gemini CLI에서 바로 사용.

## Architecture

```
Layer 3: Skills (자연어 인터페이스)
  cfd-postprocess  — CFD 결과 시각화 자동화
  mesh-inspect     — 메시/형상 분석
  report-generate  — 자동 보고서 생성

Layer 2: Agents (전문 서브에이전트)
  viz-agent    — 시각화 파이프라인 구성 (sonnet)
  mesh-agent   — 메시 분석/변환 (haiku)

Layer 1: MCP Server (mcp-server-parapilot)
  VTK direct API    → 헤드리스 렌더링 (ParaView 불필요)
  meshio            → 50+ 형식 변환
  trimesh           → STL/OBJ/PLY 분석
```

## Key Files

- `.claude-plugin/plugin.json` — 플러그인 메타데이터
- `skills/` — 3개 스킬 (cfd-postprocess, mesh-inspect, report-generate)
- `agents/` — 2개 에이전트 (viz-agent, mesh-agent)
- `src/parapilot/` — MCP 서버 소스 (pv-agent에서 마이그레이션)
- `pyproject.toml` — PyPI: mcp-server-parapilot

## Naming Convention

| 항목 | 값 |
|------|-----|
| Python package | `parapilot` |
| PyPI name | `mcp-server-parapilot` |
| CLI entry point | `mcp-server-parapilot` |
| MCP server name | `parapilot` |
| Resource URI scheme | `parapilot://` |
| ENV prefix | `PARAPILOT_*` |
| Docker container prefix | `parapilot_` |
| Docker image | `parapilot:latest` |

## Key Metrics

| 항목 | 수량 |
|------|------|
| Tools | 13 |
| Resources | 10 |
| Prompts | 3 |
| Tests | 310 |

## Competitors

- LLNL/paraview_mcp: GUI-attached, 32 stars — 기관의 도메인 전문성은 수십 년 축적
- Kitware/vtk-mcp: 문서 검색 중심 — VTK 원저자로 언제든 렌더링 확장 가능
- FreeCAD MCP 6개: CAD 모델링 전용, FEM 후처리 없음
- 상용(Ansys SimAI 등): $10k+/년, 법적 보증 + 엔터프라이즈 지원 포함

## Known Limitations

- VTK 예제 데이터셋으로만 검증됨 (수십 GB 산업 데이터 미검증)
- Headless 특성상 LLM 환각에 의한 물리적 왜곡 실시간 검증 불가
- 시뮬레이션 제어(Steering), 다중물리(Multi-physics), 불확실성 정량화(UQ) 미지원
- ParaView 자체에 MCP 인터페이스 통합 시 래퍼 성격의 한계
