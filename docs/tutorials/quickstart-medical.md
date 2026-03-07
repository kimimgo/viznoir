# 의료 영상 연구원의 CT 데이터 시각화

> CT 스캔 데이터(VTI)를 AI 어시스턴트로 3D 시각화하고 단면 분석하는 방법

## Prerequisites

- Python 3.10+
- MCP 지원 AI 클라이언트 (Claude Code, Cursor, Windsurf 등)
- CT 데이터 (VTI 포맷, Hounsfield Unit 스칼라)
- GPU 권장 (볼륨 렌더링 성능)

## 시나리오

두부(head) CT 스캔 데이터가 VTI(VTK ImageData) 포맷으로 있습니다.
이 데이터를 3D 볼륨 렌더링, 등치면 추출, 단면 분석, 라인 프로파일로 시각화하고,
360도 회전 애니메이션을 만들어 논문이나 발표에 활용합니다.

---

## Step 1: 설치 및 MCP 설정

```bash
pip install mcp-server-viznoir
```

`.mcp.json` 설정 (Claude Code / Cursor 공통):

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

## Step 2: 데이터 확인 — `inspect_data`

CT 데이터의 구조와 HU(Hounsfield Unit) 범위를 파악합니다.

### AI에게 보내는 프롬프트

> "CT 스캔 데이터를 분석해줘. 파일은 `/data/head.vti`야."
>
> "Analyze my CT scan data at `/data/head.vti`."

### 호출되는 도구

```
inspect_data(file_path="/data/head.vti")
```

### 예상 출력

```json
{
  "file": "head.vti",
  "type": "VTK ImageData",
  "bounds": [0.0, 255.0, 0.0, 255.0, 0.0, 127.0],
  "dimensions": [256, 256, 128],
  "spacing": [1.0, 1.0, 2.0],
  "point_arrays": [
    {"name": "MetaImage", "type": "scalar", "range": [-1024.0, 3071.0]}
  ],
  "cell_arrays": [],
  "timesteps": []
}
```

HU 범위(-1024 ~ 3071)를 확인할 수 있습니다. 주요 조직별 HU 값:
- 공기: -1000
- 지방: -100 ~ -50
- 물/연조직: 0 ~ 80
- 뼈(해면골): 100 ~ 300
- 뼈(치밀골): 300 ~ 3000

## Step 3: 볼륨 렌더링 — `render`

CT 데이터를 3D 볼륨으로 시각화합니다.

### AI에게 보내는 프롬프트

> "CT 데이터를 3D 볼륨 렌더링으로 보여줘."
>
> "Show me a 3D volume rendering of the CT data."

### 호출되는 도구

```
render(
    file_path="/data/head.vti",
    field_name="MetaImage",
    colormap="Grayscale",
    camera="isometric",
    width=1920,
    height=1080,
    output_filename="head_volume.png"
)
```

### 볼륨 렌더링 모드

viznoir의 `execute_pipeline`을 사용하면 representation을 volume으로 지정할 수 있습니다:

```
execute_pipeline({
    "source": {"file": "/data/head.vti"},
    "pipeline": [],
    "output": {
        "type": "image",
        "render": {
            "field": "MetaImage",
            "colormap": "Grayscale",
            "representation": "volume"
        }
    }
})
```

### 결과

두부의 3D 볼륨이 반투명하게 렌더링됩니다. 뼈 구조가 밝게, 연조직은 반투명하게 표시됩니다.

## Step 4: 뼈 구조 추출 — `contour`

특정 HU 값에서 등치면(iso-surface)을 추출하여 뼈 구조를 3D로 시각화합니다.

### AI에게 보내는 프롬프트

> "HU 500에서 뼈 구조를 추출해줘."
>
> "Extract bone structure at HU 500 as an iso-surface."

### 호출되는 도구

```
contour(
    file_path="/data/head.vti",
    field_name="MetaImage",
    isovalues=[500],
    colormap="Cool to Warm",
    camera="isometric",
    width=1920,
    height=1080
)
```

### 결과

HU 500 등치면이 두개골 형태로 추출됩니다.
여러 등치면을 동시에 추출하여 피부와 뼈를 함께 볼 수도 있습니다:

> "HU 200에서 뼈, HU -200에서 피부 윤곽을 동시에 보여줘."
>
> "Show bone at HU 200 and skin contour at HU -200 together."

```
contour(..., isovalues=[200, -200])
```

### 다중 등치면으로 조직 분리

```
contour(
    file_path="/data/head.vti",
    field_name="MetaImage",
    isovalues=[100, 300, 700],
    colormap="Cool to Warm"
)
```

세 등치면이 서로 다른 색상으로 해면골(100), 치밀골(300), 치아/임플란트(700)를 구분합니다.

## Step 5: 단면 보기 — `slice`

Coronal(관상면), Sagittal(시상면), Axial(축면) 단면을 생성합니다.

### AI에게 보내는 프롬프트

> "y축 중앙에서 관상면(coronal) 슬라이스를 보여줘."
>
> "Show a coronal slice at the center along the y-axis."

### 호출되는 도구

```
slice(
    file_path="/data/head.vti",
    field_name="MetaImage",
    origin=[127.5, 127.5, 63.5],
    normal=[0, 1, 0],
    colormap="Grayscale",
    camera="front"
)
```

### 세 가지 표준 단면

| 단면 | normal | camera | 설명 |
|------|--------|--------|------|
| Axial (축면) | `[0, 0, 1]` | `top` | 위에서 아래로 |
| Coronal (관상면) | `[0, 1, 0]` | `front` | 앞에서 뒤로 |
| Sagittal (시상면) | `[1, 0, 0]` | `right` | 좌에서 우로 |

AI에게 자연어로 요청할 수 있습니다:

> "세 가지 표준 단면(axial, coronal, sagittal)을 각각 만들어줘."
>
> "Create all three standard orthogonal slices."

## Step 6: 밀도 프로파일 — `plot_over_line`

두개골 중심선을 따라 HU 값 변화를 추출합니다.

### AI에게 보내는 프롬프트

> "두개골 중심선을 따라 위에서 아래로 HU 값 변화를 보여줘."
>
> "Show me the HU profile along the center vertical line from top to bottom."

### 호출되는 도구

```
plot_over_line(
    file_path="/data/head.vti",
    field_name="MetaImage",
    point1=[127.5, 127.5, 127.0],
    point2=[127.5, 127.5, 0.0],
    resolution=200
)
```

### 예상 출력

```json
{
  "arc_length": [0.0, 0.64, 1.28, ...],
  "MetaImage": [-1000, -1000, ..., 800, 300, 50, 50, ..., 300, 800, -1000],
  "num_points": 200
}
```

프로파일에서 HU 값이 급격히 상승하는 두 지점이 두개골 상부와 하부입니다.
AI가 이 패턴을 분석하여 두개골 두께를 추정할 수 있습니다.

### 활용 예시

> "x 방향으로 눈 높이에서 좌우로 스캔해서 안와(orbit) 구조를 찾아줘."

```
plot_over_line(
    file_path="/data/head.vti",
    field_name="MetaImage",
    point1=[0.0, 127.5, 80.0],
    point2=[255.0, 127.5, 80.0],
    resolution=300
)
```

## Step 7: 회전 애니메이션 — `animate`

등치면을 360도 회전하며 촬영하는 orbit 애니메이션을 만듭니다.

### AI에게 보내는 프롬프트

> "뼈 구조를 360도 회전하는 GIF 애니메이션으로 만들어줘."
>
> "Create a 360-degree orbit GIF of the bone structure."

### 호출되는 도구

```
animate(
    file_path="/data/head.vti",
    field_name="MetaImage",
    mode="orbit",
    colormap="Cool to Warm",
    fps=24,
    orbit_duration=6.0,
    output_format="gif",
    width=960,
    height=960
)
```

### 결과

두개골이 360도 회전하는 6초짜리 GIF 애니메이션이 생성됩니다.
`orbit_duration`으로 회전 속도를 조절합니다 (6초 = 느린 회전, 3초 = 빠른 회전).

### 고화질 비디오

발표용으로 고화질 MP4가 필요하다면:

> "1080p MP4로 만들어줘."

```
animate(..., output_format="mp4", width=1920, height=1080, video_quality=18)
```

## Step 8: 고급 파이프라인 — `execute_pipeline`

여러 필터를 조합한 복잡한 시각화를 한 번에 실행합니다.

### AI에게 보내는 프롬프트

> "HU 300 이상만 필터링해서 뼈만 보여주고, 위에서 내려다보는 시점으로 렌더링해줘."
>
> "Filter only bone (HU > 300) and render from top view."

### 호출되는 도구

```
execute_pipeline({
    "source": {"file": "/data/head.vti"},
    "pipeline": [
        {
            "filter": "Threshold",
            "params": {
                "field": "MetaImage",
                "lower": 300,
                "upper": 3071
            }
        }
    ],
    "output": {
        "type": "image",
        "render": {
            "field": "MetaImage",
            "colormap": "Cool to Warm",
            "camera": "top"
        }
    }
})
```

### 고급 파이프라인: 뇌 조직만 추출

```json
{
    "source": {"file": "/data/head.vti"},
    "pipeline": [
        {
            "filter": "Threshold",
            "params": {"field": "MetaImage", "lower": 20, "upper": 80}
        },
        {
            "filter": "Contour",
            "params": {"field": "MetaImage", "isovalues": [50]}
        }
    ],
    "output": {
        "type": "image",
        "render": {
            "field": "MetaImage",
            "colormap": "Viridis",
            "camera": "isometric"
        }
    }
}
```

---

## 워크플로우 요약

```
inspect_data     →  데이터 확인 (해상도, HU 범위, 차원)
     ↓
render (volume)  →  3D 볼륨 렌더링 (전체 구조 파악)
     ↓
contour          →  등치면 추출 (뼈, 피부, 조직 분리)
     ↓
slice            →  표준 단면 (axial, coronal, sagittal)
     ↓
plot_over_line   →  라인 프로파일 (HU 변화 분석)
     ↓
animate (orbit)  →  360도 회전 애니메이션
     ↓
execute_pipeline →  고급 필터 조합
```

## 의료 영상 관련 Tips

- **HU 기준값**: 공기 -1000, 물 0, 연조직 20-80, 뼈 300+, 금속 3000+
- **컬러맵**: 전통적 CT 이미지는 `Grayscale`, 구조 구분은 `Cool to Warm`
- **등치면 선택**: 먼저 `extract_stats`로 HU 분포를 확인한 뒤 적절한 isovalue 결정
- **해상도**: 볼륨 렌더링은 GPU 메모리에 의존 — 큰 데이터는 `width`/`height` 조절
- **슬라이스 위치**: `inspect_data`의 bounds로 정확한 origin 계산

## VTI 이외의 의료 영상 포맷

viznoir은 VTI 외에도 다양한 포맷을 지원합니다:

| 포맷 | 확장자 | 비고 |
|------|--------|------|
| VTK ImageData | `.vti` | 정규 격자, 가장 일반적 |
| VTK Unstructured | `.vtu` | 비정규 메쉬 |
| XDMF/HDF5 | `.xdmf` | 대용량 데이터셋 |
| Exodus | `.exo` | 유한요소 |

DICOM을 직접 읽지는 않으므로, 사전에 VTI로 변환해야 합니다:

```python
# Python으로 DICOM → VTI 변환 (SimpleITK 사용)
import SimpleITK as sitk
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames("/path/to/dicom/")
reader.SetFileNames(dicom_names)
image = reader.Execute()
sitk.WriteImage(image, "/data/head.vti")
```

## Next Steps

- [CFD 엔지니어 튜토리얼](quickstart-cfd.md) — OpenFOAM 유동 시각화
- [FEA 구조해석 튜토리얼](quickstart-fea.md) — 변위, 응력, 클리핑
- [Pipeline DSL 레퍼런스](../api/pipeline-dsl.md) — 고급 파이프라인 구성
- [컬러맵 가이드](../api/colormaps.md) — 물리량별 권장 컬러맵
