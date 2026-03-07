# viznoir Cinematic Rendering — 영화 수준 과학 영상 기능 설계

> "자연어를 찰떡같이 알아듣고 고품질 영화수준의 과학영상을 생성하는 것"

---

## 비전

```
User: "이 CFD 결과를 영화처럼 아름답게 렌더해줘.
       pressure를 쿨웜으로, 뒤쪽 3/4 앵글에서,
       살짝 심도 흐림 넣고, 바닥면에 그림자 깔아줘"

viznoir: → 시네마틱 조명 + SSAO + PBR 재질 + DOF
           → 자동 프레이밍 (rule of thirds)
           → 그라디언트 배경 + 바닥 그림자
           → 4K PNG (3840×2160)
```

---

## 현재 vs 목표

| 요소 | 현재 (v0.1.0) | 목표 (Cinematic) |
|------|--------------|-----------------|
| **조명** | VTK 기본 headlight 1개 | 3-point lighting + 환경광 |
| **그림자** | 없음 | Shadow map + soft shadow |
| **AO** | 없음 | SSAO (Screen-Space Ambient Occlusion) |
| **재질** | Phong shading | PBR (Physically Based Rendering) |
| **안티앨리어싱** | 없음 | FXAA + MSAA |
| **배경** | 단색 (0.2, 0.2, 0.2) | 그라디언트 + 환경맵 + HDRI |
| **카메라** | 7개 고정 프리셋 | 자동 프레이밍 + 자연어 앵글 |
| **DOF** | 없음 | 피사계 심도 (초점 거리 자동) |
| **해상도** | 1920×1080 | 최대 4K (3840×2160) |
| **바닥면** | 없음 | 그림자 캐치 평면 |
| **볼륨** | 기본 ramp opacity | 시네마틱 볼륨 (산란/반사) |
| **카메라 경로** | orbit만 | Bezier spline + 가속/감속 |
| **모션 블러** | 없음 | 셔터 시뮬레이션 |

---

## 아키텍처 설계

### 새로운 구조

```
engine/
  renderer.py        ← 기존 (호환 유지)
  renderer_cine.py   ← NEW: 시네마틱 렌더러
  camera.py          ← 기존 (확장)
  camera_auto.py     ← NEW: 자동 프레이밍/앵글
  lighting.py        ← NEW: 3-point + 환경광
  materials.py       ← NEW: PBR 재질 프리셋
  postfx.py          ← NEW: SSAO, FXAA, DOF
  scene.py           ← NEW: 배경, 바닥, 환경맵
  camera_path.py     ← NEW: 애니메이션 경로
```

### 자연어 → 렌더 파라미터 매핑

```python
# 자연어 키워드 → 렌더 설정 매핑
NATURAL_LANGUAGE_MAP = {
    # 앵글
    "3/4 앵글": {"azimuth": 45, "elevation": 30},
    "극적인 앵글": {"azimuth": 30, "elevation": 15},  # low angle
    "탑뷰": {"azimuth": 0, "elevation": 90},
    "아이소메트릭": {"azimuth": 45, "elevation": 35.264},
    "영화적 앵글": {"azimuth": 35, "elevation": 20},
    "클로즈업": {"zoom": 2.5, "dof": True},
    "와이드샷": {"zoom": 0.7},
    "dutch angle": {"roll": 15},

    # 분위기
    "영화처럼": {"preset": "cinematic"},
    "드라마틱": {"preset": "dramatic"},
    "클린": {"preset": "clean"},
    "다크": {"preset": "dark_studio"},
    "밝은": {"preset": "bright_studio"},
    "논문용": {"preset": "publication"},
    "프레젠테이션": {"preset": "presentation"},

    # 품질
    "고품질": {"quality": "ultra", "resolution": "4k"},
    "4K": {"resolution": "4k"},
    "초고해상도": {"resolution": "4k", "ssaa": 2},
    "빠르게": {"quality": "draft"},
}
```

---

## 핵심 기능 상세 설계

### 1. 시네마틱 조명 시스템

```python
@dataclass
class LightingPreset:
    """영화 촬영 기법 기반 조명 프리셋."""
    name: str
    lights: list[LightDef]

@dataclass
class LightDef:
    type: str          # "directional", "positional", "ambient"
    position: tuple    # 광원 위치/방향
    color: tuple       # RGB (0-1)
    intensity: float   # 밝기
    cone_angle: float  # spot light용
    shadow: bool       # 그림자 여부

LIGHTING_PRESETS = {
    # 3-point lighting (영화 표준)
    "cinematic": LightingPreset("cinematic", [
        LightDef("directional", (1, 1, 2), (1.0, 0.98, 0.95), 1.0, 0, True),    # Key light (약간 따뜻)
        LightDef("directional", (-1, 0, 1), (0.7, 0.8, 1.0), 0.4, 0, False),    # Fill light (차가움)
        LightDef("directional", (0, -1, 0.5), (1.0, 1.0, 1.0), 0.3, 0, False),  # Rim/Back light
    ]),

    # 드라마틱 단일광 (높은 명암비)
    "dramatic": LightingPreset("dramatic", [
        LightDef("directional", (1, 0.5, 2), (1.0, 0.95, 0.9), 1.2, 0, True),
        LightDef("ambient", (0,0,0), (0.15, 0.15, 0.2), 0.1, 0, False),
    ]),

    # 스튜디오 (균일, 부드러움)
    "studio": LightingPreset("studio", [
        LightDef("directional", (0, 0, 1), (1.0, 1.0, 1.0), 0.8, 0, False),
        LightDef("directional", (1, 1, 0.5), (1.0, 1.0, 1.0), 0.5, 0, False),
        LightDef("directional", (-1, -1, 0.5), (1.0, 1.0, 1.0), 0.3, 0, False),
        LightDef("ambient", (0,0,0), (0.3, 0.3, 0.3), 0.2, 0, False),
    ]),

    # 논문용 (밝고 깨끗, 그림자 없음)
    "publication": LightingPreset("publication", [
        LightDef("directional", (0, 0, 1), (1.0, 1.0, 1.0), 0.7, 0, False),
        LightDef("ambient", (0,0,0), (0.5, 0.5, 0.5), 0.3, 0, False),
    ]),
}
```

**VTK 구현**:
```python
import vtk

def apply_lighting(renderer, preset_name):
    preset = LIGHTING_PRESETS[preset_name]
    renderer.RemoveAllLights()
    renderer.AutomaticLightCreationOff()

    for ldef in preset.lights:
        light = vtk.vtkLight()
        if ldef.type == "directional":
            light.SetLightTypeToSceneLight()
            light.SetPosition(*ldef.position)
        elif ldef.type == "ambient":
            light.SetLightTypeToHeadlight()
        light.SetColor(*ldef.color)
        light.SetIntensity(ldef.intensity)
        if ldef.shadow:
            light.ShadowOn()  # Shadow map 필요
        renderer.AddLight(light)
```

### 2. SSAO + FXAA 후처리

```python
def enable_postfx(renderer, scene_size):
    """SSAO + FXAA 활성화."""
    import vtk

    # SSAO
    basic_passes = vtk.vtkRenderStepsPass()
    ssao = vtk.vtkSSAOPass()
    ssao.SetRadius(0.1 * scene_size)
    ssao.SetBias(0.001 * scene_size)
    ssao.SetKernelSize(128)
    ssao.BlurOn()
    ssao.SetDelegatePass(basic_passes)
    renderer.SetPass(ssao)

    # FXAA
    renderer.SetUseFXAA(True)
    fxaa_opts = renderer.GetFXAAOptions()
    fxaa_opts.SetSubpixelBlendLimit(0.75)
    fxaa_opts.SetRelativeContrastThreshold(0.125)
```

### 3. PBR 재질 시스템

```python
MATERIAL_PRESETS = {
    # 금속 — CFD 구조물, 기계 부품
    "brushed_metal": {"metallic": 0.9, "roughness": 0.4, "color": (0.8, 0.8, 0.85)},
    "polished_steel": {"metallic": 1.0, "roughness": 0.1, "color": (0.9, 0.9, 0.92)},

    # 비금속 — 유체, 의료
    "glass": {"metallic": 0.0, "roughness": 0.0, "color": (0.9, 0.95, 1.0), "opacity": 0.3},
    "ceramic": {"metallic": 0.0, "roughness": 0.3, "color": (0.95, 0.95, 0.9)},
    "skin": {"metallic": 0.0, "roughness": 0.6, "color": (0.9, 0.7, 0.6)},

    # 과학 시각화 전용
    "fluid_surface": {"metallic": 0.1, "roughness": 0.2, "color": (0.3, 0.6, 0.9)},
    "matte_vis": {"metallic": 0.0, "roughness": 0.8, "color": None},  # colormap 따름
    "glossy_vis": {"metallic": 0.1, "roughness": 0.3, "color": None},
}

def apply_pbr_material(actor, preset_name):
    """PBR 재질 적용."""
    mat = MATERIAL_PRESETS[preset_name]
    prop = actor.GetProperty()
    prop.SetInterpolationToPBR()
    prop.SetMetallic(mat["metallic"])
    prop.SetRoughness(mat["roughness"])
    if mat.get("color"):
        prop.SetColor(*mat["color"])
    if mat.get("opacity"):
        prop.SetOpacity(mat["opacity"])
```

### 4. 자동 프레이밍 (Smart Camera)

```python
@dataclass
class SmartFraming:
    """영화 촬영 구도 규칙 기반 자동 프레이밍."""

    rule: str = "thirds"  # "thirds", "center", "golden"
    headroom: float = 0.15  # 상단 여백 비율
    lookroom: float = 0.1   # 시선 방향 여백

def auto_frame(renderer, data_bounds, style="cinematic"):
    """데이터 바운딩박스를 분석해 최적 카메라 위치를 자동 결정."""

    # 1. 종횡비 분석
    dx = data_bounds[1] - data_bounds[0]
    dy = data_bounds[3] - data_bounds[2]
    dz = data_bounds[5] - data_bounds[4]
    aspect = max(dx, dy) / max(dz, 0.001)

    # 2. 형상에 따른 최적 앵글
    if aspect > 3.0:
        # 납작한 형상 (자동차, 날개) → 3/4 앵글
        azimuth, elevation = 35, 25
    elif aspect < 0.3:
        # 세로 형상 (빌딩, 타워) → 올려다보기
        azimuth, elevation = 30, -10
    elif dz / max(dx, dy, 0.001) > 2.0:
        # 높은 형상 → 눈높이
        azimuth, elevation = 40, 5
    else:
        # 일반 → 이소메트릭 변형
        azimuth, elevation = 45, 30

    # 3. 스타일 보정
    if style == "dramatic":
        elevation = max(elevation - 15, -20)  # 낮은 앵글
    elif style == "publication":
        elevation = 30  # 일정한 앵글

    # 4. Rule of thirds 적용
    # 피사체를 화면 1/3 지점에 배치

    # 5. 줌 — 피사체가 화면의 70-80% 차지하도록

    return azimuth, elevation
```

### 5. 배경 시스템

```python
BACKGROUND_PRESETS = {
    # 그라디언트
    "dark_gradient": {
        "type": "gradient",
        "top": (0.05, 0.05, 0.12),     # 거의 검정
        "bottom": (0.15, 0.15, 0.2),    # 약간 밝은 남색
    },
    "light_gradient": {
        "type": "gradient",
        "top": (0.95, 0.95, 0.98),
        "bottom": (0.8, 0.82, 0.88),
    },
    "sunset": {
        "type": "gradient",
        "top": (0.1, 0.1, 0.2),
        "bottom": (0.4, 0.15, 0.1),
    },

    # 단색
    "pure_white": {"type": "solid", "color": (1.0, 1.0, 1.0)},
    "pure_black": {"type": "solid", "color": (0.0, 0.0, 0.0)},

    # 환경맵 (HDRI)
    "studio_hdri": {"type": "hdri", "file": "studio.hdr"},
    "outdoor_hdri": {"type": "hdri", "file": "outdoor.hdr"},
}

def apply_background(renderer, preset_name):
    preset = BACKGROUND_PRESETS[preset_name]
    if preset["type"] == "gradient":
        renderer.GradientBackgroundOn()
        renderer.SetBackground(*preset["bottom"])
        renderer.SetBackground2(*preset["top"])
    elif preset["type"] == "solid":
        renderer.GradientBackgroundOff()
        renderer.SetBackground(*preset["color"])
```

### 6. 바닥면 + 그림자 캐치

```python
def add_ground_plane(renderer, data_bounds, shadow=True):
    """데이터 아래에 그림자를 받는 바닥면 추가."""
    import vtk

    # 바닥 위치 = 데이터 최저점
    z_min = data_bounds[4]

    # 바운딩박스보다 3배 큰 평면
    dx = (data_bounds[1] - data_bounds[0]) * 3
    dy = (data_bounds[3] - data_bounds[2]) * 3
    cx = (data_bounds[0] + data_bounds[1]) / 2
    cy = (data_bounds[2] + data_bounds[3]) / 2

    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(cx - dx/2, cy - dy/2, z_min)
    plane.SetPoint1(cx + dx/2, cy - dy/2, z_min)
    plane.SetPoint2(cx - dx/2, cy + dy/2, z_min)
    plane.SetResolution(1, 1)
    plane.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(plane.GetOutput())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(0.3, 0.3, 0.3)
    prop.SetOpacity(0.5)
    if shadow:
        prop.SetInterpolationToPBR()
        prop.SetRoughness(0.9)
        prop.SetMetallic(0.0)

    renderer.AddActor(actor)
```

### 7. 시네마틱 카메라 경로 (애니메이션)

```python
@dataclass
class CameraKeyframe:
    """카메라 키프레임."""
    frame: int
    position: tuple[float, float, float]
    focal_point: tuple[float, float, float]
    view_up: tuple[float, float, float] = (0, 0, 1)
    fov: float = 30.0

CAMERA_PATHS = {
    # 영화적 orbit (가속/감속)
    "cinematic_orbit": "ease-in-out orbit with slight elevation change",

    # 줌 인 → 디테일 → 줌 아웃
    "reveal": "wide shot → zoom to detail → pull back",

    # 회전하며 올라가기
    "ascending_spiral": "spiral upward from eye level to bird's eye",

    # 패닝 (좌→우)
    "pan": "smooth lateral pan across the subject",

    # 플라이스루 (내부 통과)
    "flythrough": "camera flies through the geometry",

    # 속도 변화 (Bezier 보간)
    "dramatic_reveal": "fast zoom → slow orbit → hold",
}
```

---

## 품질 프리셋 (자연어 트리거)

| 프리셋 | 조명 | 후처리 | 재질 | 배경 | 해상도 | 렌더 시간 |
|--------|------|--------|------|------|--------|---------|
| `draft` | headlight | 없음 | Phong | 단색 | 720p | ~0.3s |
| `standard` | 3-point | FXAA | Phong | 그라디언트 | 1080p | ~0.5s |
| `cinematic` | 3-point | SSAO+FXAA | PBR | 그라디언트+바닥 | 1080p | ~1.5s |
| `ultra` | 3-point+환경 | SSAO+FXAA+DOF | PBR | HDRI+바닥 | 4K | ~3s |
| `publication` | 균일 | FXAA | Phong | 흰색 | 300dpi | ~0.8s |

---

## 자연어 인터페이스 설계

### 새 MCP Tool: `cinematic_render`

```python
@mcp.tool()
async def cinematic_render(
    file_path: str,
    field: str | None = None,
    style: str = "cinematic",        # cinematic, dramatic, studio, publication
    angle: str = "auto",             # auto, 3/4, dramatic, close-up, wide
    quality: str = "cinematic",      # draft, standard, cinematic, ultra
    background: str = "auto",        # auto, dark, light, gradient, transparent
    material: str = "auto",          # auto, metal, glass, matte, glossy
    ground_shadow: bool = True,
    depth_of_field: bool = False,
    colormap: str = "cool to warm",
    width: int = 1920,
    height: int = 1080,
    description: str = "",           # 자연어 추가 지시 (AI가 파싱)
) -> PipelineResult:
    """Cinematic-quality scientific visualization rendering.

    Renders simulation data with film-quality lighting, materials, and composition.
    Supports natural language descriptions for fine control.

    Examples:
      "영화처럼 렌더해줘" → style=cinematic
      "논문 figure로" → style=publication
      "드라마틱한 낮은 앵글" → style=dramatic, angle=dramatic
      "클로즈업으로 디테일 보여줘" → angle=close-up
      "메탈릭 느낌으로" → material=metal
    """
```

### 새 MCP Tool: `cinematic_animate`

```python
@mcp.tool()
async def cinematic_animate(
    file_path: str,
    field: str | None = None,
    camera_path: str = "cinematic_orbit",  # orbit, reveal, spiral, pan, flythrough
    duration: float = 5.0,                  # 초
    fps: int = 30,
    style: str = "cinematic",
    easing: str = "ease-in-out",           # linear, ease-in, ease-out, ease-in-out
    output_format: str = "mp4",            # mp4, gif
    quality: str = "cinematic",
    music_sync: bool = False,              # 비트 동기화 (향후)
) -> PipelineResult:
    """Create cinematic camera animation of scientific data.

    Film-quality camera movements with professional easing and composition.
    """
```

---

## 구현 로드맵

### Phase 1 (v0.2.0) — Foundation
- [ ] `renderer_cine.py` — 시네마틱 렌더러 클래스
- [ ] `lighting.py` — 5개 조명 프리셋 (cinematic, dramatic, studio, publication, outdoor)
- [ ] `postfx.py` — SSAO + FXAA 활성화
- [ ] `scene.py` — 그라디언트 배경 5개 + 바닥면 + 그림자
- [ ] `cinematic_render` MCP tool

### Phase 2 (v0.3.0) — Materials & Camera
- [ ] `materials.py` — PBR 재질 프리셋 8개
- [ ] `camera_auto.py` — 자동 프레이밍 (형상 분석 → 최적 앵글)
- [ ] 자연어 → 파라미터 매핑 엔진
- [ ] 4K 해상도 지원

### Phase 3 (v0.4.0) — Animation
- [ ] `camera_path.py` — Bezier 스플라인 카메라 경로
- [ ] `cinematic_animate` MCP tool
- [ ] 5개 카메라 경로 프리셋 (orbit, reveal, spiral, pan, flythrough)
- [ ] ease-in/out 보간

### Phase 4 (v0.5.0) — Advanced
- [ ] DOF (Depth of Field)
- [ ] HDRI 환경맵 (번들 3개)
- [ ] 모션 블러
- [ ] OSPRay 레이트레이싱 지원 (설치 시)

---

## 킬러 데모 시나리오

### Demo 1: "CFD 결과를 영화처럼"
```
User: "이 차량 공기역학 시뮬레이션을 시네마틱하게 렌더해줘.
       pressure 필드, 드라마틱한 앵글, 바닥에 그림자"

→ 3-point lighting + SSAO + PBR glossy
→ 낮은 3/4 앵글 (자동차 광고 느낌)
→ 그라디언트 배경 + 바닥 그림자
→ 렌더 시간 ~1.5초
```

### Demo 2: "CT 스캔 시네마틱 볼륨"
```
User: "두개골 CT를 영화 수준으로 볼륨 렌더링해줘"

→ 시네마틱 볼륨 렌더링 (산란 모델)
→ dramatic 조명 (단일 강한 키라이트)
→ 검정 배경에서 뼈가 드라마틱하게 부각
→ 자동 클로즈업 프레이밍
```

### Demo 3: "시네마틱 오비트 영상"
```
User: "이 메쉬를 시네마틱하게 회전하는 5초 영상으로 만들어줘"

→ ease-in-out 가속/감속
→ 살짝 elevation 변화 (단순 평면 회전 아님)
→ SSAO + PBR + 3-point lighting
→ 30fps MP4
```

---

## 경쟁 우위 분석

| | ParaView GUI | LLNL/paraview_mcp | Blender | **viznoir cinematic** |
|---|---|---|---|---|
| 시네마틱 렌더 | OSPRay (수동설정) | 없음 | 최고 품질 | VTK native (자동) |
| 자연어 제어 | 없음 | 없음 | 없음 | **유일** |
| 과학 데이터 직접 | ✅ | ✅ | 변환 필요 | ✅ |
| 헤드리스 | pvbatch (복잡) | ❌ GUI | CLI 가능 | **MCP 1줄** |
| 설정 난이도 | 높음 | 높음 | 매우 높음 | **자연어** |

**핵심 차별점**: "과학 데이터를 직접 읽으면서 영화 수준 렌더를 자연어로 제어" — 이 조합은 세계 어디에도 없음.

---

## VTK 기술 제약 & 대안

| 기능 | VTK 지원 | 비고 |
|------|---------|------|
| SSAO | ✅ vtkSSAOPass (VTK 9.0+) | GPU 필수 |
| FXAA | ✅ renderer.SetUseFXAA(True) | |
| PBR | ✅ SetInterpolationToPBR() (VTK 9.0+) | |
| Shadow Map | ✅ vtkShadowMapPass | 퀄리티 제한적 |
| Gradient BG | ✅ GradientBackgroundOn() | |
| DOF | ⚠️ 커스텀 구현 필요 | multi-pass blur |
| OSPRay RT | ✅ vtkOSPRayPass | 별도 빌드 필요 |
| HDRI | ✅ vtkSkybox + vtkTexture | 파일 번들 필요 |
| Motion Blur | ⚠️ 커스텀 구현 | 프레임 블렌딩 |
| Bloom/Glow | ❌ 미지원 | post-process 필요 |
