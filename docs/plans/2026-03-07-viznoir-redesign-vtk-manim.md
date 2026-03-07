# viznoir Redesign — VTK Power Tool + Science Storyteller + Cinema Quality

**Date**: 2026-03-07
**Status**: Approved (PoC validated)
**Priority**: A (VTK Power) → C (Science Storyteller) → B (Cinema Quality)

## Philosophy

> VTK 데이터를 native 레벨로 사용해서, 학술대회 발표와 논문에 쓸 스토리텔링 자료를 만든다.
> 그 시각화 품질이 아주 아름답다.

## Current State Analysis

| Axis | Score | Gap |
|------|-------|-----|
| VTK Coverage | ~70-75% | Parallel projection, volume rendering, programmable filter 미지원 |
| Native Performance | Bottleneck | subprocess spinup = 50-70% of pipeline time (500ms-2s/request) |
| VFX Quality | Basic Cinematic | PBR/SSAO/FXAA 있으나 shadow mapping, HDRI, DOF, bloom 없음 |
| Science Storytelling | None | LaTeX overlay, animation timeline, easing 미지원 |

## PoC Validation (2026-03-07)

`poc_vtk_manim.py` — VTK cinematic render + Manim LaTeX + easing curves → Pillow composite.

- VTK wavelet isosurface: CinematicConfig (PBR, SSAO, FXAA, ground plane, dark gradient)
- Manim MathTex: Navier-Stokes equation (native LaTeX via dvisvgm)
- Manim rate_functions: 5 easing curves (smooth, ease_in_out_sine, there_and_back, rush_into, rush_from)
- Pillow composite: VTK base + equation panel + easing chart + title + watermark

Result: `/tmp/viznoir-manim-poc/viznoir_manim_poc.png` — 성공적으로 합성 확인.

## Manim Integration Strategy

**Approach**: Selective Absorption (Option B)
- manim community fork를 reference로 유지
- ~1,200 LOC 선별 이식 → `viznoir.anim` package
- MCP server 패러다임과 Manim Scene 시스템은 비호환 → 직접 통합 불가, 핵심 알고리즘만 추출

**Excluded**: TTS, Manim Scene/Animation 전체 시스템, OpenGL renderer

---

## Phase 1: v0.4.0 — Core Power

### 1.1 Worker Pool (성능 최적화)

subprocess spinup 제거 → in-process worker pool.

```
Before: server.py → subprocess.Popen(script.py) → 500ms-2s overhead
After:  server.py → WorkerPool.submit(pipeline) → ~50ms overhead
```

- `ProcessPoolExecutor` 기반 (VTK GIL 제약 회피)
- 워커 100회 렌더 후 자동 재시작 (VTK 메모리 누수 방지, 기존 싱글톤 패턴 유지)
- Fallback: subprocess 모드 유지 (Docker 환경)

### 1.2 Parallel Projection

공학 도면/논문 figure용 정사영 카메라.

```python
# engine/camera.py 확장
def setup_parallel_projection(renderer, dataset, direction="iso"):
    camera = renderer.GetActiveCamera()
    camera.ParallelProjectionOn()
    camera.SetParallelScale(computed_scale)
```

- `RenderConfig.projection`: `"perspective"` | `"parallel"` (default: perspective)
- 6방향 프리셋: +X, -X, +Y, -Y, +Z, -Z, iso

### 1.3 Volume Rendering

CT/MRI 볼륨 데이터 직접 렌더링.

```python
# engine/volume.py (신규)
def volume_render(image_data, transfer_function="ct_bone", ...):
    mapper = vtk.vtkGPUVolumeRayCastMapper()
    ...
```

- `vtkGPUVolumeRayCastMapper` (GPU) + `vtkFixedPointVolumeRayCastMapper` (CPU fallback)
- Transfer function presets: ct_bone, ct_tissue, mri_brain, thermal, generic
- MCP tool: `volume_render` 추가

### 1.4 Manim Easing Absorption

`viznoir.anim.easing` — Manim rate_functions 17종 이식 (~200 LOC).

```python
# anim/easing.py
def smooth(t): ...
def ease_in_out_sine(t): ...
def there_and_back(t): ...
# ... 17 functions total
```

- 기존 `AnimationDef.easing` 필드와 연결
- Pure Python, 외부 의존성 없음

---

## Phase 2: v0.5.0 — Science Storyteller

### 2.1 LaTeX Overlay

`viznoir.anim.latex` — Manim Tex 시스템 핵심 추출 (~400 LOC).

```python
# anim/latex.py
def render_latex(tex_string, font_size=48, color="#FFFFFF") -> PIL.Image:
    """LaTeX → SVG → PNG (transparent background)"""
```

- dvisvgm 파이프라인 (Manim 방식)
- matplotlib mathtext fallback (LaTeX 미설치 환경)
- `composite` optional dependency에 포함

### 2.2 Animation Timeline

`viznoir.anim.timeline` — keyframe 기반 애니메이션 (~300 LOC).

```python
# anim/timeline.py
class Timeline:
    def add_keyframe(self, t: float, camera=None, opacity=None, ...): ...
    def interpolate(self, t: float) -> FrameState: ...
```

- Camera path interpolation (position, focal point, view up)
- Property animation (opacity, color, scalar range)
- Easing function 적용

### 2.3 Transitions

`viznoir.anim.transitions` — 장면 전환 효과 (~300 LOC).

```python
# anim/transitions.py
def fade_in(frame, t, easing=smooth): ...
def fade_out(frame, t, easing=smooth): ...
def cross_dissolve(frame_a, frame_b, t): ...
def wipe(frame_a, frame_b, t, direction="left"): ...
```

### 2.4 story_render MCP Tool

VTK + LaTeX + Timeline → 학회 발표용 영상.

```python
@mcp.tool()
async def story_render(
    file_path: str,
    story: list[StoryStep],  # [{vtk_render, latex, transition, duration}]
    output_format: str = "mp4",
    fps: int = 30,
) -> PipelineResult:
```

---

## Phase 3: v0.6.0 — Cinema Quality

| Feature | VTK Class | 효과 |
|---------|-----------|------|
| Shadow Mapping | `vtkShadowMapPass` | 실제 그림자 |
| HDRI Environment | `vtkOpenGLTexture` + cubemap | 환경맵 조명/반사 |
| Normal Mapping | `vtkTexture` + normal map | 표면 디테일 |
| Depth of Field | `vtkDepthOfFieldPass` | 피사계 심도 |
| Motion Blur | Multi-frame accumulation | 움직임 흐림 |
| Bloom | `vtkGaussianBlurPass` + composite | 발광 효과 |

---

## File Structure (New)

```
src/viznoir/
├── anim/                    # Phase 1-2 신규
│   ├── __init__.py
│   ├── easing.py            # Phase 1: rate_functions (200 LOC)
│   ├── latex.py             # Phase 2: LaTeX → PNG (400 LOC)
│   ├── timeline.py          # Phase 2: keyframe animation (300 LOC)
│   └── transitions.py       # Phase 2: scene transitions (300 LOC)
├── engine/
│   ├── volume.py            # Phase 1: volume rendering (신규)
│   ├── camera.py            # Phase 1: +parallel projection
│   ├── renderer_cine.py     # Phase 3: +shadow/HDRI/DOF
│   └── ...
├── core/
│   ├── worker.py            # Phase 1: worker pool (신규)
│   └── ...
└── tools/
    ├── volume_impl.py       # Phase 1: volume_render tool
    ├── story_impl.py        # Phase 2: story_render tool
    └── ...
```

## Dependencies

| Package | Phase | Optional Group |
|---------|-------|----------------|
| (none new) | Phase 1 | — |
| pillow, matplotlib | Phase 2 | `composite` (기존) |
| ffmpeg (system) | Phase 2 | story_render mp4 출력용 |

## Success Criteria

| Phase | Metric |
|-------|--------|
| v0.4.0 | render latency < 200ms (wavelet), parallel projection 6방향, volume CT render |
| v0.5.0 | 30초 학회 발표 영상 생성 (VTK + LaTeX + transitions) |
| v0.6.0 | shadow + HDRI cinematic render, Blender 대비 80% 품질 |

## Out of Scope

- TTS / 음성 합성
- Manim Scene/Animation 전체 시스템 이식
- Real-time interactive rendering
- ParaView 호환 레이어
- 시뮬레이션 제어 (Steering)
