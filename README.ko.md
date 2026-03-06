# parapilot

[English](README.md) | **한국어**

[![CI](https://github.com/kimimgo/parapilot/actions/workflows/ci.yml/badge.svg)](https://github.com/kimimgo/parapilot/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kimimgo/parapilot/branch/main/graph/badge.svg)](https://codecov.io/gh/kimimgo/parapilot)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-parapilot)](https://pypi.org/project/mcp-server-parapilot/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-parapilot)](https://pypi.org/project/mcp-server-parapilot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/kimimgo/parapilot/blob/main/LICENSE)

AI 코딩 어시스턴트를 위한 헤드리스 CAE 후처리 MCP 서버.

**[랜딩 페이지](https://kimimgo.github.io/parapilot)** · **[PyPI](https://pypi.org/project/mcp-server-parapilot/)** · **[이슈](https://github.com/kimimgo/parapilot/issues)**

```
pip install mcp-server-parapilot
```

![DrivAerML 자동차 CFD](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/drivaerml_cp.webp)
*880만 셀 SA-DDES 자동차 CFD — MCP 도구 한 번 호출, GUI 불필요*

## 소개

parapilot은 AI 어시스턴트(Claude Code, Cursor, Gemini CLI)가 GUI 없이 CFD/FEA 시뮬레이션 결과를 렌더링할 수 있게 해줍니다. VTK를 직접 사용하여 OpenFOAM, VTK, CGNS 등 50개 이상의 포맷에서 PNG 스크린샷, 통계, 애니메이션을 생성합니다.

## 빠른 시작

### Claude Code (플러그인)

```bash
claude install kimimgo/parapilot
```

대화에서:

> "cavity/cavity.foam에서 jet 컬러맵으로 압력장을 렌더링해줘"

### 독립 실행 MCP 서버

```json
{
  "mcpServers": {
    "parapilot": {
      "command": "mcp-server-parapilot"
    }
  }
}
```

### Docker (GPU 헤드리스)

```bash
docker compose up -d
```

GPU 렌더링에는 NVIDIA Container Toolkit이 필요합니다.

### Docker (CPU 전용, GPU 불필요)

```bash
docker compose up parapilot-cpu -d
```

OSMesa 소프트웨어 렌더링 — GPU 없는 머신에서도 동작합니다.

## 예제

[`examples/`](examples/) 디렉토리에서 전체 워크플로우 파이프라인을 확인하세요:

- **thermal_analysis.json** — 복합 열전달 후처리 (8단계)
- **aerodynamics_workflow.json** — 외부 공기역학: 압력, 유선, 후류 분석 (7단계)
- **structural_fea.json** — 구조 FEA: 본미세스 응력, 변위, 피로 경로 (7단계)

## 도구 (18개)

| 도구 | 설명 |
|------|------|
| `inspect_data` | 파일 메타데이터 — 필드, 타임스텝, 경계 |
| `render` | 단일 필드 PNG 스크린샷 |
| `slice` | 절단면 시각화 |
| `contour` | 등치면 시각화 |
| `clip` | 클리핑 영역 시각화 |
| `streamlines` | 벡터장 유선 시각화 |
| `cinematic_render` | 논문 품질 렌더링 (SSAO, PBR, 3점 조명) |
| `compare` | 두 데이터셋 나란히 또는 차이 비교 |
| `probe_timeseries` | 한 점에서 타임스텝별 필드값 추출 |
| `batch_render` | 여러 필드를 한 번에 렌더링 |
| `preview_3d` | glTF/glB 내보내기 (인터랙티브 3D 뷰) |
| `extract_stats` | 필드 최솟값/최댓값/평균/표준편차 |
| `plot_over_line` | 직선 위의 값 샘플링 |
| `integrate_surface` | 표면 위의 힘/플럭스 적분 |
| `animate` | 시계열 또는 카메라 궤도 애니메이션 |
| `split_animate` | 다중 패널 동기화 애니메이션 (GIF) |
| `execute_pipeline` | 고급 워크플로우를 위한 파이프라인 DSL |
| `pv_isosurface` | DualSPHysics bi4 → VTK 표면 메시 |

## 리소스 (11개)

| URI | 내용 |
|-----|------|
| `parapilot://formats` | 지원 파일 포맷 및 리더 |
| `parapilot://filters` | 사용 가능한 필터 파라미터 |
| `parapilot://colormaps` | 컬러맵 프리셋 |
| `parapilot://cameras` | 카메라 각도 프리셋 + PCA 자동 카메라 |
| `parapilot://cinematic` | 조명, 재질, 배경, 품질 프리셋 |
| `parapilot://representations` | 렌더링 표현 방식 |
| `parapilot://case-presets` | 도메인별 케이스 프리셋 |
| `parapilot://physics-defaults` | 물리 기반 렌더링 기본값 |
| `parapilot://pipelines/cfd` | CFD 파이프라인 예제 |
| `parapilot://pipelines/fea` | FEA 파이프라인 예제 |
| `parapilot://pipelines/split-animate` | 분할 애니메이션 예제 |

## 쇼케이스

아래 렌더링은 모두 MCP 도구 한 번 호출로 생성 — 후처리 없음.

| | | |
|---|---|---|
| ![CT 두개골](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/ct_head_contour.webp) | ![유선](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/streamlines.webp) | ![드래곤](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/dragon.webp) |
| 뼈 등치면 (contour) | 경동맥 혈류 (streamlines) | 스탠포드 드래곤 (render) |
| ![CT 볼륨](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/ct_volume.webp) | ![사무실 기류](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/office_flow.webp) | ![아르마딜로 클립](https://raw.githubusercontent.com/kimimgo/parapilot/main/www/public/showcase/armadillo_clip.webp) |
| 볼륨 레이캐스팅 (render) | HVAC 기류 (streamlines) | 메시 클립 (clip) |

**12개 공학 도메인** — 해양, 기계, 항공, 전자, 의생명, 지구과학, 환경, 화학공정, 구조, 선박, 과학, 도시.

전체 갤러리: **[kimimgo.github.io/parapilot](https://kimimgo.github.io/parapilot)**

## 아키텍처

```
┌─────────────────────────────────────────────┐
│  AI 어시스턴트 (Claude / Cursor / Gemini)    │
│  ↕ MCP 프로토콜 (stdio)                     │
├─────────────────────────────────────────────┤
│  parapilot MCP 서버 (FastMCP)               │
│  ├── tools/     18개 MCP 도구               │
│  ├── resources/ 11개 MCP 리소스             │
│  └── prompts/   3개 MCP 프롬프트            │
├─────────────────────────────────────────────┤
│  엔진 레이어 (VTK 직접 API)                 │
│  ├── readers    OpenFOAM, VTK, CGNS, ...    │
│  ├── filters    Slice, Contour, Clip, ...   │
│  ├── renderer   오프스크린 VTK 렌더링       │
│  ├── camera     프리셋 + 커스텀 위치        │
│  ├── colormaps  과학용 컬러 스키마          │
│  ├── overlay    스칼라바, 라벨, 텍스트      │
│  ├── physics    필드 타입 자동 감지         │
│  └── export     PNG, VTK, CSV 출력          │
├─────────────────────────────────────────────┤
│  코어 레이어                                │
│  ├── compiler   파이프라인 → VTK 스크립트   │
│  ├── runner     로컬 / Docker 실행          │
│  ├── registry   필터 & 포맷 스키마          │
│  └── output     결과 수집                   │
└─────────────────────────────────────────────┘
```

## 워크플로우

```
inspect_data → render / slice / contour → extract_stats → animate
```

1. **검사** — 필드, 타임스텝, 경계 탐색
2. **시각화** — 렌더링, 슬라이스, 등치면, 클리핑, 유선
3. **추출** — 통계, 라인 플롯, 표면 적분
4. **애니메이션** — 시계열 또는 다중 패널 비교

## 지원 포맷

OpenFOAM (.foam), VTK (.vti/.vtp/.vtu/.vtm), CGNS (.cgns), Ensight (.case), Exodus (.exo), STL (.stl), PLY (.ply), OBJ (.obj) 등 VTK 리더를 통해 30개 이상 지원.

## 기여하기

기여를 환영합니다! [오픈 이슈](https://github.com/kimimgo/parapilot/issues)를 확인하세요 — 특히 [`good first issue`](https://github.com/kimimgo/parapilot/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 라벨이 붙은 이슈를 추천합니다.

```bash
git clone https://github.com/kimimgo/parapilot
cd parapilot
pip install -e ".[dev]"
pytest                     # 1128 테스트
ruff check src/ tests/     # 린트
mypy src/parapilot/        # 타입 체크
```

자세한 설정, 아키텍처 가이드, 새로운 필터/리더 추가 방법은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 대안 비교

| | parapilot | LLNL/paraview_mcp | FEA-MCP | openfoam-mcp | Blender MCP |
|---|---|---|---|---|---|
| 초점 | 범용 CAE 후처리 | ParaView 시각화 | ETABS/LUSAS FEA | OpenFOAM 설정 | 3D 모델링 |
| 렌더링 | 헤드리스 VTK (GUI 불필요) | GUI 연결 ParaView | GUI 연결 | 없음 | GUI Blender |
| 테스트 | 1128 | 0 | 0 | 0 | 0 |
| 커버리지 | 99% | — | — | — | — |
| Docker | GPU (EGL) + CPU (OSMesa) | 없음 | 없음 | 없음 | 없음 |
| MCP 도구 | 18 | 23 | N/A | N/A | N/A |
| 포맷 | 20+ | ParaView 네이티브 | ETABS/LUSAS | .foam만 | Blender 네이티브 |
| 보안 | CodeQL + pip-audit + Scorecard | 없음 | 없음 | 없음 | 없음 |
| 플러그인 | Claude Code 플러그인 | 없음 | 없음 | 없음 | 없음 |

## 알려진 제한사항

- VTK 예제 데이터셋으로만 검증됨 — 대규모 산업 데이터(1억+ 셀)는 미검증
- 헤드리스 렌더링 특성상 LLM이 생성한 파라미터 오류를 실시간 시각적으로 검증 불가
- 시뮬레이션 제어, 다중물리 커플링, 불확실성 정량화 미지원
- ParaView가 자체적으로 MCP를 통합하면 이 래퍼 방식은 중복될 수 있음

## 기여자

<!-- ALL-CONTRIBUTORS-LIST:START -->
| [<img src="https://avatars.githubusercontent.com/u/21175731?v=4" width="60px;" alt="kimimgo"/><br /><sub><b>kimimgo</b></sub>](https://github.com/kimimgo) |
| :---: |
<!-- ALL-CONTRIBUTORS-LIST:END -->

## 라이선스

MIT
