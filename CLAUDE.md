# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# viznoir

VTK is all you need. Cinema-quality science visualization for AI agents.

## Project Info
- **Repo**: kimimgo/viznoir
- **Language**: Python 3.10+
- **MCP SDK**: fastmcp>=2.0.0
- **PyPI**: mcp-server-viznoir
- **Entry point**: `mcp-server-viznoir` → `viznoir.server:main`

## Development Commands

```bash
# Install (editable with dev deps)
pip install -e ".[dev]"

# Run all tests (1134 tests, async mode=auto)
pytest --cov=viznoir --cov-report=term-missing -q

# Run a single test file
pytest tests/test_engine/test_filters.py -q

# Run a single test function
pytest tests/test_engine/test_filters.py::test_slice_plane -q

# Lint
ruff check src/ tests/

# Lint + auto-fix
ruff check src/ tests/ --fix

# Type check
mypy src/viznoir/ --ignore-missing-imports

# Install with optional deps (meshio/trimesh or pillow/matplotlib)
pip install -e ".[mesh]"       # mesh format conversion
pip install -e ".[composite]"  # split_animate (Pillow + matplotlib)
pip install -e ".[all]"        # everything

# Run MCP server locally (stdio mode)
mcp-server-viznoir

# Landing page (www/)
cd www && npm install && npm run dev    # dev server
cd www && npm run build                 # production build

# Docker (GPU EGL headless)
docker compose build
docker compose up                       # stdio mode, GPU required
```

CI runs on Python 3.10, 3.11, 3.12, 3.13: lint → type check → test. Coverage threshold ≥80% enforced on 3.12.

## Architecture

```
Layer 3: Skills (자연어 인터페이스)        ← .claude-plugin/
  cfd-postprocess, mesh-inspect, report-generate

Layer 2: Agents (전문 서브에이전트)        ← agents/
  viz-agent (sonnet), mesh-agent (haiku)

Layer 1: MCP Server (mcp-server-viznoir)  ← src/viznoir/
  VTK direct API → 헤드리스 렌더링 (ParaView 불필요)
  meshio → 50+ 형식 변환, trimesh → STL/OBJ/PLY 분석
```

### Data Flow (Tool Call → PNG)

```
server.py (MCP tool)
  → tools/*.py (impl: build PipelineDefinition)
    → core/compiler.py (ScriptCompiler: PipelineDefinition → Python script string)
      → core/runner.py (VTKRunner: in-process executor or Docker)
        → engine/*.py (VTK direct API: readers, filters, renderer, camera)
          → core/output.py (OutputHandler: RunResult → PipelineResult)
```

- `server.py`: FastMCP 인스턴스 + 21개 tool 등록, lazy import로 tool impl 로딩
- `tools/`: 각 tool의 비즈니스 로직 (render_impl, slice_impl 등)
- `pipeline/models.py`: Pydantic 모델 (SourceDef, FilterStep, RenderDef, OutputDef 등)
- `core/compiler.py`: PipelineDefinition → executable Python/VTK script 문자열 생성
- `core/runner.py`: VTKRunner — InProcessExecutor (로컬) 또는 Docker 컨테이너에서 스크립트 실행
- `core/worker.py`: InProcessExecutor — subprocess 없이 in-process 스크립트 실행 (500ms→50ms)
- `core/registry.py`: PascalCase 키 (FilterRegistry, FormatRegistry)
- `engine/filters.py`: snake_case 키, 실제 VTK 필터 함수 (slice_plane, clip_plane 등)
- `engine/renderer.py`: 오프스크린 렌더링 (EGL/OSMesa), 싱글톤 vtkRenderWindow 재사용
- `engine/renderer_cine.py`: 시네마틱 렌더러 (lighting + SSAO + FXAA + auto-camera + PBR)
- `engine/camera_auto.py`: PCA 형상 분석 + frustum fitting 자동 카메라
- `engine/lighting.py`: 3-point lighting 프리셋 (cinematic/dramatic/studio/publication/outdoor)
- `engine/postfx.py`: SSAO + FXAA 후처리
- `engine/transfer_functions.py`: 볼륨 렌더링 transfer function 프리셋 6종
- `anim/easing.py`: 17종 easing 함수 (Manim rate_functions 기반)
- `engine/scene.py`: 배경 프리셋 + ground plane
- `engine/readers.py`: 파일 포맷별 VTK reader 팩토리
- `engine/analysis.py`: 데이터 인사이트 추출 (필드 통계, 이상점 탐지, 물리 컨텍스트, 교차 분석)
- `anim/timeline.py`: 씬 타임라인 시퀀싱 (prefix-sum + bisect O(log n) lookup)
- `anim/transitions.py`: 씬 전환 효과 (fade, dissolve, wipe — Image.blend C-level)
- `anim/compositor.py`: 프레임 합성 + 비디오 내보내기 (story/grid/slides/video 레이아웃)
- `tools/analyze.py`: analyze_data MCP tool 구현
- `tools/compose.py`: compose_assets MCP tool 구현

### Dual Registry Gotcha

두 개의 독립적인 필터 레지스트리가 존재:

- `core/registry.py` → `FILTER_REGISTRY`: PascalCase 키 (Slice, Clip). **파라미터 스키마 + VTK 클래스명** 저장. `ScriptCompiler`가 파이프라인 코드 생성 시 사용. `get_filter()`가 case-insensitive lookup 제공.
- `engine/filters.py` → `_FILTER_REGISTRY`: snake_case 키 (slice_plane, clip_plane). **실제 VTK 필터 함수** 매핑. `apply_filter()`가 `_normalize_filter_name()`으로 CamelCase → snake_case 변환 후 lookup.

새 필터 추가 시 **양쪽 모두** 등록 필요.

### VTK Headless Rendering

- `VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow` 환경변수로 EGL 활성화 (CI에서는 `vtkOSOpenGLRenderWindow` 사용)
- `vtkRenderWindow()` 사용 (NOT `vtkEGLRenderWindow()` — SIGSEGV 발생)
- 싱글톤 `_RENDER_WINDOW`는 100회 렌더 후 자동 재생성 (GPU 메모리 누수 방지)
- `_protect_stdout()`: VTK C 코드가 fd 1에 ~20MB 바이너리 쓰레기를 직접 출력 → MCP JSON-RPC 스트림 오염 방지. 실제 stdout fd를 `os.dup()`로 보존하고 fd 1을 `/dev/null`로 리다이렉트

### Error Hierarchy

`errors.py`에 정의된 커스텀 예외:
- `ViznoirError` — base
- `FileFormatError` — 미지원 파일 포맷
- `FieldNotFoundError` — 데이터셋에 없는 필드
- `EmptyOutputError` — 필터 결과가 비어있음 (isovalues가 데이터 범위 밖 등)
- `RenderError` — 렌더링 실패

### Security: ProgrammableFilter

`ProgrammableFilter`는 기본 비활성 (임의 코드 실행 위험). `VIZNOIR_ALLOW_PROGRAMMABLE=1` 환경변수로 활성화.

## Configuration (Environment Variables)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VIZNOIR_DATA_DIR` | None (무제한) | 데이터 디렉토리 제한 (Docker 보안) |
| `VIZNOIR_OUTPUT_DIR` | `/output` | 출력 디렉토리 |
| `VIZNOIR_PYTHON_BIN` | `sys.executable` | VTK 스크립트 실행 Python |
| `VIZNOIR_RENDER_BACKEND` | `gpu` | gpu/cpu/auto |
| `VIZNOIR_VTK_BACKEND` | `auto` | egl/osmesa/auto |
| `VIZNOIR_TIMEOUT` | `600` | 스크립트 실행 타임아웃 (초) |
| `VIZNOIR_ALLOW_PROGRAMMABLE` | `0` | ProgrammableFilter 활성화 (보안) |
| `VIZNOIR_DOCKER_IMAGE` | `viznoir:latest` | Docker 실행 모드 이미지 |
| `VIZNOIR_GPU_DEVICE` | `0` | GPU 디바이스 인덱스 |

## Naming Convention

| 항목 | 값 |
|------|-----|
| Python package | `viznoir` |
| PyPI name | `mcp-server-viznoir` |
| MCP server name | `viznoir` |
| Resource URI scheme | `viznoir://` |
| ENV prefix | `VIZNOIR_*` |

## Key Metrics

| 항목 | 수량 |
|------|------|
| Tools | 21 |
| Resources | 12 |
| Prompts | 4 |
| Tests | 1305+ |

## Test Structure

- `tests/test_engine/` — VTK 엔진 레이어 단위 테스트 (filters, readers, renderer, camera, colormaps)
- `tests/test_core/` — 컴파일러, 러너, 레지스트리, 컴포지터
- `tests/test_pipeline/` — 파이프라인 엔진 통합 테스트
- `tests/test_tools/` — MCP tool 레벨 테스트 (convenience, server, e2e_production)
- `tests/fixtures/` — 테스트 데이터 생성 헬퍼 (wavelet, create_data)
- pytest-asyncio `asyncio_mode = "auto"` — async 테스트 자동 감지

### CI Auto-Skip Rules (conftest.py)

CI 환경(`CI=1`)에서 VTK GPU 렌더링이 필요한 테스트는 자동 스킵:
- `*_vtk.py` 파일 전체 (패턴 매칭)
- 명시적 파일: `test_e2e_production.py`, `test_renderer_cine.py`
- 명시적 클래스: `TestVTKRendererAndRenderToPng`, `TestComposeSideBySide`, `TestCompareImpl`, `TestExportGltf`

새 VTK 렌더링 테스트 추가 시: 파일명을 `*_vtk.py`로 하거나 `conftest.py`의 스킵 목록에 추가.

### Ruff Config

- `target-version = "py310"`, `line-length = 120`
- Select: `E`, `F`, `I`, `N`, `W`, `UP` (N802 무시 — VTK의 PascalCase 메서드명)
- `tests/fixtures/*`에서 F403, F405 무시 (wildcard import 허용)

## Known Limitations

- VTK 예제 데이터셋으로만 검증됨 (수십 GB 산업 데이터 미검증)
- Headless 특성상 LLM 환각에 의한 물리적 왜곡 실시간 검증 불가
- 시뮬레이션 제어(Steering), 다중물리(Multi-physics), 불확실성 정량화(UQ) 미지원
- ParaView 자체에 MCP 인터페이스 통합 시 래퍼 성격의 한계
