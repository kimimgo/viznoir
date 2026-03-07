# viznoir

[English](README.md) | **한국어**

> AI 터미널을 위한 헤드리스 CAE/CFD 후처리. ParaView 불필요. GUI 불필요.

[![CI](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/viznoir/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kimimgo/viznoir/branch/main/graph/badge.svg)](https://codecov.io/gh/kimimgo/viznoir)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-viznoir)](https://pypi.org/project/mcp-server-viznoir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/viznoir/blob/main/LICENSE)

![DrivAerML 자동차 CFD](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/drivaerml_cp.webp)

## 빠른 시작

**Claude Code 플러그인:**

```bash
claude install kimimgo/viznoir
```

대화에서:

> "cavity/cavity.foam에서 jet 컬러맵으로 압력장을 렌더링해줘"

**pip:**

```bash
pip install mcp-server-viznoir
```

**Docker (GPU 헤드리스):**

```bash
docker compose up -d
```

NVIDIA Container Toolkit 필요. CPU 전용: `docker compose up viznoir-cpu -d`

**Cursor 등 다른 클라이언트용 MCP 설정:**

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

## 주요 기능

- **헤드리스 렌더링** — EGL/OSMesa 오프스크린 렌더링.
  디스플레이, GUI, ParaView 설치 불필요.

- **18개 MCP 도구** — 검사, 렌더링, 슬라이스, 등치면, 클리핑, 유선,
  시네마틱 렌더링, 비교, 애니메이션, 통계 추출 등.

- **50+ 포맷** — OpenFOAM, VTK, CGNS, STL, PLY, OBJ, Exodus, Ensight
  등 VTK 리더 + meshio 지원.

## 렌더링 갤러리

모든 렌더링은 MCP 도구 한 번 호출로 생성 — 후처리 없음.

| | | |
|---|---|---|
| ![자동차 CFD](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/drivaerml_cp.webp) | ![의료 CT](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/ct_head_contour.webp) | ![혈류](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/streamlines.webp) |
| 자동차 CFD | 의료 CT | 혈류 시각화 |
| ![HVAC](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/office_flow.webp) | ![구조 FEA](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/arch_structural.webp) | ![스탠포드 드래곤](https://raw.githubusercontent.com/kimimgo/viznoir/main/www/public/showcase/dragon.webp) |
| HVAC 기류 | 구조 FEA | 스탠포드 드래곤 |

[전체 갤러리 →](https://kimimgo.github.io/viznoir)

## 대안 비교

| 기능 | viznoir | ParaView (pvpython) | PyVista | VTK Python |
|------|-----------|---------------------|---------|------------|
| MCP 통합 | 네이티브 18개 도구 | — | — | — |
| 헤드리스 | EGL/OSMesa | pvpython | 지원 | 수동 설정 |
| Docker | GPU + CPU | 복잡 | — | — |
| 자연어 | AI 우선 | — | — | — |
| 파일 포맷 | 50+ (meshio) | 70+ | 30+ | ~20 |
| 설치 | pip install | 시스템 패키지 | pip install | pip install |
| 테스트 | 1134 (99% 커버리지) | N/A | 있음 | N/A |

## 기여하기

```bash
git clone https://github.com/kimimgo/viznoir
cd viznoir && pip install -e ".[dev]"
pytest  # 1134 테스트, 99% 커버리지
```

자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 라이선스

MIT
