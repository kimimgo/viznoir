# 학생의 FEA 과제 시각화

> 구조 해석(FEA) 결과를 AI 어시스턴트로 빠르게 시각화하고 분석하는 방법

## Prerequisites

- Python 3.10+
- MCP 지원 AI 클라이언트 (Claude Code, Cursor, Windsurf 등)
- FEA 결과 파일 (VTU, Exodus, XDMF 등)
- GPU 권장, CPU fallback 가능

## 시나리오

구조역학 과제로 외팔보(cantilever beam)에 하중을 가한 유한요소 해석을 수행했습니다.
결과 파일(`beam.vtu`)에 변위(displacement), 응력(von Mises stress) 필드가 저장되어 있습니다.
viznoir으로 변형 형상, 응력 분포, 내부 단면을 시각화하고 보고서에 넣을 이미지를 생성합니다.

---

## Step 1: 설치 및 MCP 설정

```bash
pip install mcp-server-viznoir
```

`.mcp.json` 설정:

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

## Step 2: 메쉬와 결과 확인 — `inspect_data`

FEA 결과 파일의 구조를 파악합니다.

### AI에게 보내는 프롬프트

> "내 유한요소 해석 결과를 분석해줘. 파일은 `/data/beam.vtu`야."
>
> "Analyze my FEA result file at `/data/beam.vtu`."

### 호출되는 도구

```
inspect_data(file_path="/data/beam.vtu")
```

### 예상 출력

```json
{
  "file": "beam.vtu",
  "type": "VTK UnstructuredGrid",
  "bounds": [0.0, 1.0, -0.05, 0.05, -0.025, 0.025],
  "num_points": 45000,
  "num_cells": 32000,
  "cell_types": ["Hexahedron"],
  "point_arrays": [
    {"name": "displacement", "type": "vector", "range": [0.0, 0.0023]},
    {"name": "von_mises_stress", "type": "scalar", "range": [0.0, 285000000.0]},
    {"name": "stress_xx", "type": "scalar", "range": [-280000000.0, 280000000.0]},
    {"name": "strain", "type": "vector", "range": [0.0, 0.0014]}
  ],
  "cell_arrays": [
    {"name": "element_id", "type": "scalar"}
  ],
  "timesteps": []
}
```

AI가 결과를 분석합니다:
- 보의 크기: 1.0 x 0.1 x 0.05 m
- 최대 변위: 2.3 mm
- 최대 von Mises 응력: 285 MPa
- 셀 타입: 6면체(Hexahedron) — 구조 해석 표준 요소

## Step 3: 변위 렌더링 — `render`

변위(displacement) 필드를 시각화합니다.

### AI에게 보내는 프롬프트

> "변위 크기를 Cool to Warm 컬러맵으로 렌더링해줘."
>
> "Render the displacement magnitude with a Cool to Warm colormap."

### 호출되는 도구

```
render(
    file_path="/data/beam.vtu",
    field_name="displacement",
    colormap="Cool to Warm",
    camera="isometric",
    output_filename="displacement.png"
)
```

### 결과

외팔보의 변위 분포가 표시됩니다.
고정단(왼쪽) 근처는 파랑(변위 0), 자유단(오른쪽)은 빨강(최대 변위)으로 나타납니다.

### 응력 렌더링

> "von Mises 응력도 렌더링해줘."
>
> "Also render the von Mises stress."

```
render(
    file_path="/data/beam.vtu",
    field_name="von_mises_stress",
    colormap="Cool to Warm",
    camera="isometric",
    output_filename="von_mises.png"
)
```

응력 집중 영역(고정단 모서리)이 빨간색으로 강조됩니다.

## Step 4: 변형 형상 시각화 — `execute_pipeline`

`WarpByVector` 필터로 변위를 과장(scale)하여 변형 형상을 시각화합니다.

### AI에게 보내는 프롬프트

> "변위를 10배 과장해서 변형된 형상을 응력으로 색칠해줘."
>
> "Show the deformed shape with 10x displacement scaling, colored by stress."

### 호출되는 도구

```
execute_pipeline({
    "source": {"file": "/data/beam.vtu"},
    "pipeline": [
        {
            "filter": "WarpByVector",
            "params": {
                "vector": "displacement",
                "scale_factor": 10
            }
        }
    ],
    "output": {
        "type": "image",
        "render": {
            "field": "von_mises_stress",
            "colormap": "Cool to Warm",
            "camera": "isometric"
        }
    }
})
```

### 결과

보가 아래로 휘어진 형상이 실제보다 10배 과장되어 표시됩니다.
응력 분포가 색상으로 겹쳐져 변형과 응력의 관계를 한눈에 파악할 수 있습니다.

### 스케일 팩터 가이드

| 변위/전체 길이 비율 | 권장 scale_factor |
|--------------------|-------------------|
| > 10% | 1 (실제 스케일) |
| 1% ~ 10% | 5 ~ 10 |
| < 1% | 50 ~ 100 |

이 예제에서 최대 변위 2.3mm / 보 길이 1000mm = 0.23% → `scale_factor=10~50` 적절

## Step 5: 클리핑으로 내부 확인 — `clip`

보를 잘라서 내부 응력 분포를 확인합니다.

### AI에게 보내는 프롬프트

> "보의 중앙에서 잘라서 내부 응력 분포를 보여줘."
>
> "Clip the beam at the center to show internal stress distribution."

### 호출되는 도구

```
clip(
    file_path="/data/beam.vtu",
    field_name="von_mises_stress",
    origin=[0.5, 0, 0],
    normal=[1, 0, 0],
    colormap="Cool to Warm",
    camera="isometric"
)
```

### 결과

보의 x=0.5 지점에서 절단된 단면이 표시됩니다.
내부 응력의 분포를 확인할 수 있습니다 — 상하면에 최대 응력, 중립축 근처에 최소 응력.

### 다른 방향 클리핑

> "y=0 평면으로 잘라서 위쪽 절반만 보여줘."

```
clip(
    file_path="/data/beam.vtu",
    field_name="von_mises_stress",
    origin=[0.5, 0, 0],
    normal=[0, 1, 0],
    invert=false,
    camera="front"
)
```

`invert=true`로 반대쪽을 볼 수 있습니다.

## Step 6: 응력 집중 영역 추출 — `execute_pipeline`

항복 응력 이상 영역만 하이라이트합니다.

### AI에게 보내는 프롬프트

> "von Mises 응력이 250 MPa 이상인 영역만 보여줘."
>
> "Show only regions where von Mises stress exceeds 250 MPa."

### 호출되는 도구

```
execute_pipeline({
    "source": {"file": "/data/beam.vtu"},
    "pipeline": [
        {
            "filter": "Threshold",
            "params": {
                "field": "von_mises_stress",
                "lower": 250000000,
                "upper": 300000000
            }
        }
    ],
    "output": {
        "type": "image",
        "render": {
            "field": "von_mises_stress",
            "colormap": "Cool to Warm",
            "camera": "isometric"
        }
    }
})
```

### 결과

항복 응력(250 MPa) 이상 영역만 표시됩니다.
고정단 모서리의 응력 집중 영역을 정확히 식별할 수 있습니다.

## Step 7: 정량적 분석 — `extract_stats`

필드의 통계값을 추출합니다.

### AI에게 보내는 프롬프트

> "변위와 von Mises 응력의 통계를 알려줘."
>
> "Give me statistics for displacement and von Mises stress."

### 호출되는 도구

```
extract_stats(
    file_path="/data/beam.vtu",
    fields=["displacement", "von_mises_stress"]
)
```

### 예상 출력

```json
{
  "displacement": {
    "min": 0.0,
    "max": 0.0023,
    "mean": 0.0011,
    "std": 0.00068,
    "num_points": 45000
  },
  "von_mises_stress": {
    "min": 0.0,
    "max": 285000000.0,
    "mean": 95000000.0,
    "std": 72000000.0,
    "num_points": 45000
  }
}
```

AI가 해석 결과를 분석합니다:
- 최대 변위 2.3mm (보 길이의 0.23% — 소변형 가정 유효)
- 최대 von Mises 응력 285 MPa (강철 항복응력 250 MPa 초과 — 소성 변형 영역 존재)
- 평균 응력 95 MPa (대부분 탄성 범위)

## Step 8: 표면 적분 — `integrate_surface`

특정 면에서 응력을 적분하여 반력(reaction force)을 계산합니다.

### AI에게 보내는 프롬프트

> "고정단 면에서 응력을 적분해줘."
>
> "Integrate stress over the fixed end face."

### 호출되는 도구

```
integrate_surface(
    file_path="/data/beam.vtu",
    field_name="stress_xx",
    boundary="fixed_end"
)
```

### 예상 출력

```json
{
  "field": "stress_xx",
  "boundary": "fixed_end",
  "integral": 10000.0,
  "area": 0.005,
  "mean": 2000000.0
}
```

## Step 9: 라인 프로파일 — `plot_over_line`

보의 길이 방향 응력 변화를 추출합니다.

### AI에게 보내는 프롬프트

> "보의 상면을 따라 길이 방향 응력 변화를 추출해줘."
>
> "Extract stress variation along the top surface of the beam."

### 호출되는 도구

```
plot_over_line(
    file_path="/data/beam.vtu",
    field_name="von_mises_stress",
    point1=[0.0, 0.0, 0.025],
    point2=[1.0, 0.0, 0.025],
    resolution=200
)
```

### 예상 출력

```json
{
  "arc_length": [0.0, 0.005, 0.01, ...],
  "von_mises_stress": [285000000, 275000000, ...],
  "num_points": 200
}
```

이론적으로 외팔보의 굽힘 응력은 고정단에서 최대, 자유단에서 0입니다.
추출된 프로파일로 FEA 결과가 이론과 일치하는지 검증할 수 있습니다.

## Step 10: 복합 파이프라인 — `execute_pipeline`

여러 필터를 조합한 고급 시각화를 수행합니다.

### AI에게 보내는 프롬프트

> "변형 형상을 보여주되, 응력이 100 MPa 이상인 부분만 빨간색으로 강조해줘."
>
> "Show deformed shape, highlighting only regions above 100 MPa in red."

### 호출되는 도구

```
execute_pipeline({
    "source": {"file": "/data/beam.vtu"},
    "pipeline": [
        {
            "filter": "WarpByVector",
            "params": {"vector": "displacement", "scale_factor": 20}
        },
        {
            "filter": "Threshold",
            "params": {
                "field": "von_mises_stress",
                "lower": 100000000,
                "upper": 300000000
            }
        }
    ],
    "output": {
        "type": "image",
        "render": {
            "field": "von_mises_stress",
            "colormap": "Cool to Warm",
            "camera": "isometric"
        }
    }
})
```

### 데이터 내보내기

> "응력과 변위 데이터를 CSV로 내보내줘."

```
execute_pipeline({
    "source": {"file": "/data/beam.vtu"},
    "pipeline": [],
    "output": {
        "type": "csv",
        "data": {
            "fields": ["displacement", "von_mises_stress", "strain"]
        }
    }
})
```

---

## 워크플로우 요약

```
inspect_data       →  메쉬/필드 구조 파악
     ↓
render             →  변위, 응력 필드 시각화
     ↓
execute_pipeline   →  WarpByVector로 변형 형상 시각화
(WarpByVector)
     ↓
clip               →  내부 응력 분포 확인
     ↓
execute_pipeline   →  Threshold로 응력 집중 영역 추출
(Threshold)
     ↓
extract_stats      →  정량적 통계 (min/max/mean)
     ↓
integrate_surface  →  반력/면적 계산
     ↓
plot_over_line     →  길이 방향 프로파일
     ↓
execute_pipeline   →  복합 필터 + CSV 내보내기
```

## FEA 시각화 Tips

- **스케일 팩터**: 변위가 작으면 `scale_factor`를 키워서 변형을 과장
- **컬러맵**: 응력에는 `Cool to Warm` (diverging), 변위에는 `Viridis` (sequential)
- **등치면 활용**: `contour`로 특정 응력 레벨의 등가면(iso-stress surface)을 추출
- **다중 뷰**: AI에게 "정면, 측면, 등각 뷰 3장을 만들어줘"라고 요청
- **이론 검증**: `plot_over_line`으로 추출한 프로파일을 해석해(beam theory)와 비교

## 사용 가능한 FEA 필터

| 필터 | 용도 | 파이프라인에서 |
|------|------|---------------|
| WarpByVector | 변형 형상 | `{"filter": "WarpByVector", "params": {"vector": "displacement", "scale_factor": 10}}` |
| WarpByScalar | 스칼라 기반 변형 | `{"filter": "WarpByScalar", "params": {"field": "temperature", "scale_factor": 5}}` |
| Threshold | 범위 필터링 | `{"filter": "Threshold", "params": {"field": "stress", "lower": 1e8}}` |
| Contour | 등치면 추출 | `{"filter": "Contour", "params": {"field": "stress", "isovalues": [250e6]}}` |
| Calculator | 유도량 계산 | `{"filter": "Calculator", "params": {"expression": "mag(displacement)", "result_name": "disp_mag"}}` |
| Gradient | 변화율 계산 | `{"filter": "Gradient", "params": {"field": "temperature"}}` |

## 지원 파일 포맷

| 포맷 | 확장자 | 흔한 FEA 소프트웨어 |
|------|--------|-------------------|
| VTK Unstructured | `.vtu` | Abaqus (변환), CalculiX, Elmer |
| Exodus II | `.exo`, `.e` | Abaqus, MOOSE, Cubit |
| XDMF/HDF5 | `.xdmf` | FEniCS, Firedrake |
| CGNS | `.cgns` | ANSYS |
| EnSight | `.case` | ANSYS, MSC |

## Next Steps

- [CFD 엔지니어 튜토리얼](quickstart-cfd.md) — OpenFOAM 유동 시각화
- [의료 영상 CT 튜토리얼](quickstart-medical.md) — 볼륨 렌더링과 등치면
- [Pipeline DSL 레퍼런스](../api/pipeline-dsl.md) — 전체 필터/출력 옵션 가이드
- [FEA 파이프라인 예제](../api/fea-pipelines.md) — `viznoir://pipelines/fea` 전체 목록
