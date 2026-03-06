# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# parapilot

CAE post-processing MCP server for AI coding assistants.

## Project Info
- **Repo**: kimimgo/parapilot
- **Language**: Python 3.10+
- **MCP SDK**: fastmcp>=2.0.0
- **PyPI**: mcp-server-parapilot
- **Entry point**: `mcp-server-parapilot` → `parapilot.server:main`

## Development Commands

```bash
# Install (editable with dev deps)
pip install -e ".[dev]"

# Run all tests (650 tests, async mode=auto)
pytest --cov=parapilot --cov-report=term-missing -q

# Run a single test file
pytest tests/test_engine/test_filters.py -q

# Run a single test function
pytest tests/test_engine/test_filters.py::test_slice_plane -q

# Lint
ruff check src/ tests/

# Lint + auto-fix
ruff check src/ tests/ --fix

# Type check
mypy src/parapilot/ --ignore-missing-imports

# Install with optional deps (meshio/trimesh or pillow/matplotlib)
pip install -e ".[mesh]"       # mesh format conversion
pip install -e ".[composite]"  # split_animate (Pillow + matplotlib)
pip install -e ".[all]"        # everything

# Run MCP server locally (stdio mode)
mcp-server-parapilot

# Landing page (www/)
cd www && npm install && npm run dev    # dev server
cd www && npm run build                 # production build

# Docker (GPU EGL headless)
docker compose build
docker compose up                       # stdio mode, GPU required
```

CI runs on Python 3.10 and 3.12: lint → type check → test.

## Architecture

```
Layer 3: Skills (자연어 인터페이스)        ← .claude-plugin/
  cfd-postprocess, mesh-inspect, report-generate

Layer 2: Agents (전문 서브에이전트)        ← agents/
  viz-agent (sonnet), mesh-agent (haiku)

Layer 1: MCP Server (mcp-server-parapilot)  ← src/parapilot/
  VTK direct API → 헤드리스 렌더링 (ParaView 불필요)
  meshio → 50+ 형식 변환, trimesh → STL/OBJ/PLY 분석
```

### Data Flow (Tool Call → PNG)

```
server.py (MCP tool)
  → tools/*.py (impl: build PipelineDefinition)
    → core/compiler.py (ScriptCompiler: PipelineDefinition → Python script string)
      → core/runner.py (VTKRunner: exec script via subprocess or Docker)
        → engine/*.py (VTK direct API: readers, filters, renderer, camera)
          → core/output.py (OutputHandler: RunResult → PipelineResult)
```

- `server.py`: FastMCP 인스턴스 + 15개 tool 등록, lazy import로 tool impl 로딩
- `tools/`: 각 tool의 비즈니스 로직 (render_impl, slice_impl 등)
- `pipeline/models.py`: Pydantic 모델 (SourceDef, FilterStep, RenderDef, OutputDef 등)
- `core/compiler.py`: PipelineDefinition → executable Python/VTK script 문자열 생성
- `core/runner.py`: VTKRunner — 로컬 subprocess 또는 Docker 컨테이너에서 스크립트 실행
- `core/registry.py`: PascalCase 키 (FilterRegistry, FormatRegistry)
- `engine/filters.py`: snake_case 키, 실제 VTK 필터 함수 (slice_plane, clip_plane 등)
- `engine/renderer.py`: 오프스크린 렌더링 (EGL/OSMesa), 싱글톤 vtkRenderWindow 재사용
- `engine/renderer_cine.py`: 시네마틱 렌더러 (lighting + SSAO + FXAA + auto-camera + PBR)
- `engine/camera_auto.py`: PCA 형상 분석 + frustum fitting 자동 카메라
- `engine/lighting.py`: 3-point lighting 프리셋 (cinematic/dramatic/studio/publication/outdoor)
- `engine/postfx.py`: SSAO + FXAA 후처리
- `engine/scene.py`: 배경 프리셋 + ground plane
- `engine/readers.py`: 파일 포맷별 VTK reader 팩토리

### Dual Registry Gotcha

`core/registry.py`는 PascalCase 키 (Slice, Clip), `engine/filters.py`는 snake_case 키 (slice_plane, clip_plane). `get_filter()`가 case-insensitive lookup으로 연결.

### VTK Headless Rendering

- `VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow` 환경변수로 EGL 활성화
- `vtkRenderWindow()` 사용 (NOT `vtkEGLRenderWindow()` — SIGSEGV 발생)
- `_protect_stdout()`: VTK C 코드의 stdout 오염으로부터 MCP JSON-RPC 스트림 보호

## Configuration (Environment Variables)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PARAPILOT_DATA_DIR` | None (무제한) | 데이터 디렉토리 제한 (Docker 보안) |
| `PARAPILOT_OUTPUT_DIR` | `/output` | 출력 디렉토리 |
| `PARAPILOT_PYTHON_BIN` | `sys.executable` | VTK 스크립트 실행 Python |
| `PARAPILOT_RENDER_BACKEND` | `gpu` | gpu/cpu/auto |
| `PARAPILOT_VTK_BACKEND` | `auto` | egl/osmesa/auto |
| `PARAPILOT_TIMEOUT` | `600` | 스크립트 실행 타임아웃 (초) |

## Naming Convention

| 항목 | 값 |
|------|-----|
| Python package | `parapilot` |
| PyPI name | `mcp-server-parapilot` |
| MCP server name | `parapilot` |
| Resource URI scheme | `parapilot://` |
| ENV prefix | `PARAPILOT_*` |

## Key Metrics

| 항목 | 수량 |
|------|------|
| Tools | 18 |
| Resources | 11 |
| Prompts | 3 |
| Tests | 826 |

## Test Structure

- `tests/test_engine/` — VTK 엔진 레이어 단위 테스트 (filters, readers, renderer, camera, colormaps)
- `tests/test_core/` — 컴파일러, 러너, 레지스트리, 컴포지터
- `tests/test_pipeline/` — 파이프라인 엔진 통합 테스트
- `tests/test_tools/` — MCP tool 레벨 테스트 (convenience, server, e2e_production)
- `tests/fixtures/` — 테스트 데이터 생성 헬퍼 (wavelet, create_data)
- pytest-asyncio `asyncio_mode = "auto"` — async 테스트 자동 감지

## Known Limitations

- VTK 예제 데이터셋으로만 검증됨 (수십 GB 산업 데이터 미검증)
- Headless 특성상 LLM 환각에 의한 물리적 왜곡 실시간 검증 불가
- 시뮬레이션 제어(Steering), 다중물리(Multi-physics), 불확실성 정량화(UQ) 미지원
- ParaView 자체에 MCP 인터페이스 통합 시 래퍼 성격의 한계
