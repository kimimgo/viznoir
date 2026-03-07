# CFD 엔지니어의 첫 viznoir 사용

> OpenFOAM 시뮬레이션 결과를 AI 어시스턴트로 빠르게 시각화하고 분석하는 방법

## Prerequisites

- Python 3.10+
- MCP 지원 AI 클라이언트 (Claude Code, Cursor, Windsurf 등)
- OpenFOAM 시뮬레이션 결과 (`.foam` 파일)
- GPU 권장 (EGL 헤드리스 렌더링), CPU fallback 가능

## 시나리오

실린더 주위 유동(cylinder flow) 시뮬레이션을 OpenFOAM으로 완료했습니다.
결과 디렉토리에 `case.foam`, `0/`, `constant/`, `system/` 폴더가 있는 상태입니다.
viznoir을 사용해 압력장, 유선, 슬라이스 뷰를 빠르게 생성하고 통계를 추출합니다.

---

## Step 1: 설치

```bash
pip install mcp-server-viznoir
```

VTK가 자동으로 설치됩니다. GPU 렌더링을 위해 EGL 드라이버가 필요합니다.
CPU만 있는 환경에서는 OSMesa fallback이 자동 적용됩니다.

```bash
# 설치 확인
mcp-server-viznoir --help
```

## Step 2: MCP 클라이언트 설정

사용하는 AI 클라이언트의 MCP 설정 파일에 viznoir을 등록합니다.

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir",
      "env": {
        "VIZNOIR_OUTPUT_DIR": "./output"
      }
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir",
      "env": {
        "VIZNOIR_OUTPUT_DIR": "./output"
      }
    }
  }
}
```

설정 후 AI 클라이언트를 재시작하면 viznoir 도구가 활성화됩니다.

## Step 3: 데이터 검사 — `inspect_data`

시뮬레이션 파일을 열어 어떤 데이터가 있는지 확인합니다.

### AI에게 보내는 프롬프트

> "내 OpenFOAM 시뮬레이션 결과를 분석해줘. 파일은 `/home/user/simulations/cylinder/case.foam`이야."
>
> "Analyze my OpenFOAM simulation result. The file is at `/home/user/simulations/cylinder/case.foam`."

### 호출되는 도구

```
inspect_data(file_path="/home/user/simulations/cylinder/case.foam")
```

### 예상 출력

```json
{
  "file": "case.foam",
  "type": "OpenFOAM",
  "bounds": [-2.0, 8.0, -2.0, 2.0, -0.5, 0.5],
  "point_arrays": [
    {"name": "U", "type": "vector", "range": [0.0, 1.45]},
    {"name": "p", "type": "scalar", "range": [-0.82, 0.53]}
  ],
  "cell_arrays": [
    {"name": "turbulenceProperties:k", "type": "scalar"}
  ],
  "timesteps": [0.0, 0.5, 1.0, 1.5, 2.0],
  "blocks": ["internalMesh", "boundary/inlet", "boundary/outlet", "boundary/wall"]
}
```

AI가 이 결과를 바탕으로 사용 가능한 필드(`U`, `p`), 타임스텝, 경계면 목록을 설명해줍니다.
이 정보를 기반으로 이후 시각화를 진행합니다.

## Step 4: 첫 렌더링 — `render`

압력(pressure) 필드를 시각화합니다.

### AI에게 보내는 프롬프트

> "마지막 타임스텝의 압력 필드를 렌더링해줘."
>
> "Render the pressure field at the latest timestep."

### 호출되는 도구

```
render(
    file_path="/home/user/simulations/cylinder/case.foam",
    field_name="p",
    colormap="Cool to Warm",
    camera="isometric",
    timestep="latest",
    output_filename="pressure.png"
)
```

### 결과

1920x1080 PNG 이미지가 생성됩니다. 실린더 주위의 압력 분포가 Cool to Warm 컬러맵으로 표시됩니다.
고압 영역(빨강)은 실린더 전면, 저압 영역(파랑)은 후류에 나타납니다.

### 카메라 변경

다른 시점에서 보고 싶다면:

> "위에서 내려다보는 시점으로 다시 렌더링해줘."
>
> "Re-render from a top-down view."

```
render(..., camera="top")
```

사용 가능한 카메라 프리셋: `isometric`, `top`, `front`, `right`, `left`, `back`

## Step 5: 슬라이스 뷰 — `slice`

z=0 평면으로 절단하여 내부 유동장을 확인합니다.

### AI에게 보내는 프롬프트

> "z=0 평면으로 잘라서 속도 크기를 보여줘."
>
> "Show me a z=0 slice of velocity magnitude."

### 호출되는 도구

```
slice(
    file_path="/home/user/simulations/cylinder/case.foam",
    field_name="U",
    origin=[0, 0, 0],
    normal=[0, 0, 1],
    colormap="Viridis",
    camera="top",
    timestep="latest"
)
```

### 결과

z=0 평면의 속도 분포가 표시됩니다. 실린더 뒤의 후류(wake)와 와류(vortex shedding) 패턴을 확인할 수 있습니다.

`origin`과 `normal`을 생략하면 데이터셋 중심에서 자동으로 절단합니다.
다른 방향의 슬라이스도 요청할 수 있습니다:

> "x=3 위치에서 y-z 평면으로 잘라줘."
>
> "Create a y-z plane slice at x=3."

```
slice(..., origin=[3, 0, 0], normal=[1, 0, 0])
```

## Step 6: 유선 시각화 — `streamlines`

속도 벡터 필드로 유선(streamlines)을 그립니다.

### AI에게 보내는 프롬프트

> "속도 벡터로 유선을 그려줘. 입구 쪽에서 시작해서 실린더를 지나가는 모습을 보여줘."
>
> "Draw streamlines from the inlet showing flow around the cylinder."

### 호출되는 도구

```
streamlines(
    file_path="/home/user/simulations/cylinder/case.foam",
    vector_field="U",
    seed_point1=[-1.5, -1.5, 0],
    seed_point2=[-1.5, 1.5, 0],
    seed_resolution=30,
    max_length=10.0,
    colormap="Viridis",
    timestep="latest"
)
```

### 결과

입구 영역에서 시작된 30개의 유선이 실린더를 감싸며 흘러가는 모습이 렌더링됩니다.
유선 색상은 속도 크기에 따라 변합니다.

`seed_point1`/`seed_point2`를 생략하면 데이터셋 경계(bounds)에서 자동으로 seed line을 생성합니다.

## Step 7: 통계 추출 — `extract_stats`

압력과 속도의 통계값(최소, 최대, 평균, 표준편차)을 추출합니다.

### AI에게 보내는 프롬프트

> "압력과 속도의 범위, 평균값을 알려줘."
>
> "Give me the range and mean values of pressure and velocity."

### 호출되는 도구

```
extract_stats(
    file_path="/home/user/simulations/cylinder/case.foam",
    fields=["p", "U"],
    timestep="latest"
)
```

### 예상 출력

```json
{
  "p": {
    "min": -0.82,
    "max": 0.53,
    "mean": 0.012,
    "std": 0.15,
    "num_points": 125000
  },
  "U": {
    "min": 0.0,
    "max": 1.45,
    "mean": 0.98,
    "std": 0.23,
    "num_points": 125000,
    "components": {
      "Ux": {"min": -0.45, "max": 1.45, "mean": 0.95},
      "Uy": {"min": -0.82, "max": 0.82, "mean": 0.0},
      "Uz": {"min": -0.01, "max": 0.01, "mean": 0.0}
    }
  }
}
```

AI가 이 통계를 해석하여 "유동은 주로 x 방향이며, 최대 속도 비율(U_max/U_inlet)은 약 1.45"와 같은 분석을 제공합니다.

## Step 8: 라인 프로파일 — `plot_over_line`

실린더 후류의 속도 프로파일을 추출합니다.

### AI에게 보내는 프롬프트

> "실린더 뒤쪽 x=3 위치에서 y 방향 속도 프로파일을 뽑아줘."
>
> "Extract a velocity profile along y-direction at x=3 behind the cylinder."

### 호출되는 도구

```
plot_over_line(
    file_path="/home/user/simulations/cylinder/case.foam",
    field_name="U",
    point1=[3.0, -2.0, 0.0],
    point2=[3.0, 2.0, 0.0],
    resolution=200,
    timestep="latest"
)
```

### 예상 출력

```json
{
  "arc_length": [0.0, 0.02, 0.04, ...],
  "U": [[0.92, 0.01, 0.0], [0.88, 0.05, 0.0], ...],
  "num_points": 200,
  "line": {
    "point1": [3.0, -2.0, 0.0],
    "point2": [3.0, 2.0, 0.0]
  }
}
```

이 데이터를 기반으로 후류의 속도 결손(velocity deficit)을 분석할 수 있습니다.

## Step 9: 벽면 적분 — `integrate_surface`

실린더 벽면의 압력을 적분하여 항력(drag force)을 계산합니다.

### AI에게 보내는 프롬프트

> "실린더 벽면(wall)에서 압력을 적분해줘."
>
> "Integrate pressure over the cylinder wall boundary."

### 호출되는 도구

```
integrate_surface(
    file_path="/home/user/simulations/cylinder/case.foam",
    field_name="p",
    boundary="wall",
    timestep="latest"
)
```

### 예상 출력

```json
{
  "field": "p",
  "boundary": "wall",
  "integral": 0.342,
  "area": 3.14159,
  "mean": 0.109
}
```

## Step 10: 애니메이션 — `animate`

시간에 따른 유동 변화를 애니메이션으로 생성합니다.

### AI에게 보내는 프롬프트

> "전체 타임스텝에 걸쳐 압력 변화를 GIF 애니메이션으로 만들어줘."
>
> "Create a GIF animation of pressure evolution over all timesteps."

### 호출되는 도구

```
animate(
    file_path="/home/user/simulations/cylinder/case.foam",
    field_name="p",
    mode="timesteps",
    colormap="Cool to Warm",
    camera="top",
    fps=24,
    speed_factor=5.0,
    output_format="gif"
)
```

### 결과

와류 방출(vortex shedding)의 시간 변화를 보여주는 GIF 애니메이션이 생성됩니다.
`speed_factor=5.0`은 물리 시간 1초를 영상 0.2초로 압축합니다(5배속).

---

## 워크플로우 요약

```
inspect_data  →  데이터 파악 (필드, 타임스텝, 경계면)
     ↓
render        →  전체 뷰 렌더링 (압력, 온도 등)
     ↓
slice         →  내부 단면 확인
     ↓
streamlines   →  유동 패턴 시각화
     ↓
extract_stats →  정량적 분석 (min/max/mean)
     ↓
plot_over_line→  라인 프로파일 추출
     ↓
integrate_surface → 표면 적분 (힘, 플럭스)
     ↓
animate       →  시간 변화 애니메이션
```

## Tips

- **자동 파라미터**: `origin`, `normal`, `seed_point` 등을 생략하면 데이터 중심에서 자동 설정됩니다
- **컬러맵**: 압력/온도는 `Cool to Warm`, 속도는 `Viridis`, 터뷸런스는 `Plasma` 권장
- **타임스텝**: `"latest"`로 마지막 스텝, `null`로 첫 스텝, 숫자로 특정 스텝 선택
- **블록 선택**: OpenFOAM의 boundary patch를 `blocks` 파라미터로 선택 가능
- **리소스 참조**: AI에게 "사용 가능한 컬러맵 목록 보여줘"라고 하면 `viznoir://colormaps` 리소스를 조회합니다

## Troubleshooting

| 문제 | 해결 방법 |
|------|-----------|
| "File not found" | 절대 경로 사용, `.foam` 파일 존재 확인 |
| 빈 이미지 | `inspect_data`로 필드명 재확인, `timestep="latest"` 시도 |
| 렌더링 느림 | `width`/`height` 줄이기 (960x540), GPU 드라이버 확인 |
| 검은 화면 | EGL 미지원 시 `VIZNOIR_RENDER_BACKEND=cpu` 설정 |

## Next Steps

- [의료 영상 CT 시각화 튜토리얼](quickstart-medical.md) — 볼륨 렌더링과 등치면
- [FEA 구조해석 시각화 튜토리얼](quickstart-fea.md) — 변위, 응력, 클리핑
- [Pipeline DSL 레퍼런스](../api/pipeline-dsl.md) — `execute_pipeline`으로 복잡한 워크플로우 구성
- [MCP 리소스 목록](../api/resources.md) — `viznoir://` 리소스 URI 전체 목록
