# viznoir — 실사용자 시나리오 & 기능 정의

> 리서치 기반: Reddit r/CFD, r/OpenFOAM, CFD Engine, ScienceDirect, 업계 자료 종합

---

## 실사용자 Pain Points (리서치 발견)

### 1. "ParaView GUI가 멈춘다" — 대용량 데이터 병목
> "The GUI becomes unresponsive while waiting for some data processing or rendering"
> — r/CFD

- 수십~수백 GB 시뮬레이션 결과를 ParaView에 로드하면 GUI freeze
- 특히 transient (시계열) 데이터는 수천 개 timestep → 메모리 폭발
- HPC 클러스터에서 돌린 결과를 로컬로 옮기는 것 자체가 병목

**viznoir 대응**: 헤드리스 → GUI 없음, 메모리 효율적, 원격 서버에서 직접 렌더

### 2. "post-processing 스크립트 짜기 귀찮다" — 자동화 진입장벽
> "State files are a very low barrier to automation, and scripting is also good"
> — r/CFD

- ParaView Python API는 강력하지만 학습곡선 높음
- pvbatch/pvpython 스크립트 작성 → 디버깅 → 반복 수정 사이클이 김
- OpenFOAM functionObjects → 설정 복잡, 런타임 전용

**viznoir 대응**: 자연어로 요청 → AI가 tool 호출 → 결과 즉시 반환. 스크립트 불필요.

### 3. "그래프는 ParaView 말고 Python으로" — 도구 분산
> "I highly recommend learning something like Python (matplotlib) for graphs"
> "I use ParaView for contours and Python for figures"
> — r/CFD

- 3D 렌더 → ParaView, 2D 그래프 → matplotlib, 보고서 → Word/LaTeX
- 3개 도구를 오가며 작업 → context switching 비용 높음
- 일관된 스타일 유지 어려움

**viznoir 대응**: render + plot_over_line + extract_stats → 단일 인터페이스에서 3D/2D/수치 모두

### 4. "보고서 이미지 대량 생성" — 반복 작업
> "For certain problem types we use standardized post-processing and reporting"
> — r/CFD

- 매 시뮬레이션마다 동일 포맷의 이미지 세트 생성 (단면 3장, 유선 1장, 통계표 1개...)
- 설계 비교 (Case A vs B vs C) → 동일 뷰포인트에서 N개 케이스 렌더
- "표준화된 보고서" 니즈 → 템플릿 기반 자동화

**viznoir 대응**: execute_pipeline DSL로 표준 파이프라인 정의 → 케이스만 바꿔서 반복 실행

### 5. "transient 데이터 실시간 확인" — 수렴/모니터링
> "triggering an instance of paraview whenever a time folder is written"
> "trying to do some transient post processing without storing massive amounts of data"
> — r/CFD

- 시뮬레이션 진행 중에 결과를 확인하고 싶음 (수렴 체크, 물리적 타당성)
- 전체 데이터를 저장하지 않고 on-the-fly 시각화
- 수렴 그래프, residual plot, force 모니터링

**viznoir 대응**: ⚠️ 현재 미지원. functionObjects 데이터를 읽는 tool 필요.

### 6. "ParaView 출력이 못생겼다" — 프레젠테이션 품질
> "produces output that is very ugly by default"
> "if I want to generate a figure for a report or presentation I would only use Paraview if I was extremely short on time"
> — r/CFD

- 학술 논문/프레젠테이션용 고품질 이미지 필요
- 기본 컬러맵, 축 레이블, 범례 → 수동 조정 필요
- 일관된 스타일 (폰트, 색상, 해상도) 유지

**viznoir 대응**: colormap 프리셋 + 해상도 설정. 그러나 축/범례/주석은 현재 미약.

---

## 유저 페르소나별 시나리오

### Persona A: CFD 엔지니어 (산업계)
**환경**: OpenFOAM/STAR-CCM+, HPC 클러스터, 수십 GB 결과
**일상**: 시뮬레이션 제출 → 대기 → 결과 확인 → 보고서 → 회의

| 시나리오 | 현재 워크플로우 | viznoir 워크플로우 |
|---------|-------------|-------------------|
| 수렴 확인 | SSH → ParaView headless → pvbatch 스크립트 | "residual plot 보여줘" → plot_over_line |
| 단면 비교 | ParaView GUI에서 수동 3개 단면 생성 | "x=0, 0.5, 1.0 에서 pressure 단면 3장" |
| 설계 비교 | Case A,B,C 각각 ParaView 열어서 동일 뷰 캡처 | "3개 케이스를 같은 뷰에서 비교 렌더" |
| 보고서 | ParaView→PNG→Word 수동 삽입 | "표준 보고서 이미지 세트 생성" |

### Persona B: 학술 연구원
**환경**: OpenFOAM/FEniCS, 학교 서버, 논문 작성
**일상**: 메쉬 검증 → 시뮬레이션 → 후처리 → 논문 figure → 리뷰 대응

| 시나리오 | 현재 워크플로우 | viznoir 워크플로우 |
|---------|-------------|-------------------|
| 논문 figure | ParaView + matplotlib + Inkscape | render + plot_over_line + 스타일 프리셋 |
| 격자 수렴 | 3개 메쉬 수동 비교 | "coarse/medium/fine 메쉬 L2 에러 비교" |
| 리뷰 대응 | "Reviewer 2가 다른 각도 요청" → ParaView 재작업 | "Y축 회전 45도에서 다시 렌더" |

### Persona C: 학생/입문자
**환경**: 강의 과제, 처음 CFD/FEA 접함
**일상**: 튜토리얼 따라하기 → 결과 확인 → 보고서 제출

| 시나리오 | 현재 워크플로우 | viznoir 워크플로우 |
|---------|-------------|-------------------|
| 첫 결과 확인 | ParaView 설치 → 인터페이스 어려움 → 포기 | "결과 파일 분석해줘" → inspect_data |
| 과제 보고서 | 스크린샷 → Word | "보고서용 이미지 세트 생성" |

### Persona D: DevOps/MLOps 엔지니어
**환경**: CI/CD 파이프라인, 시뮬레이션 자동화
**일상**: 시뮬레이션 결과 자동 검증 → 대시보드 → 알림

| 시나리오 | 현재 워크플로우 | viznoir 워크플로우 |
|---------|-------------|-------------------|
| CI 검증 | pvbatch 스크립트 → 이미지 diff | MCP tool → 이미지 + 통계 자동 검증 |
| 대시보드 | 커스텀 VTK 스크립트 | execute_pipeline → JSON 결과 → Grafana |

---

## 기능 Gap 분석 — 현재 vs 필요

### ✅ 현재 보유 (13 tools)

| 기능 | Tool | 유저 니즈 매칭 |
|------|------|-------------|
| 파일 분석 | inspect_data | Persona C 첫 확인 |
| 3D 렌더 | render | 모든 페르소나 |
| 단면 | slice | Persona A 단면 비교 |
| 등치면 | contour | Persona B 논문 figure |
| 클리핑 | clip | Persona A 내부 구조 |
| 유선 | streamlines | Persona A/B 유동 시각화 |
| 라인 프로파일 | plot_over_line | Persona B 검증 그래프 |
| 통계 추출 | extract_stats | 모든 페르소나 |
| 표면 적분 | integrate_surface | Persona A 힘/모멘트 |
| 애니메이션 | animate | Persona B 프레젠테이션 |
| 멀티 패널 | split_animate | Persona A 비교 |
| 파이프라인 DSL | execute_pipeline | Persona D 자동화 |
| DualSPHysics 전용 | pv_isosurface | 특수 |

### ❌ 누락된 핵심 기능 (유저 리서치 기반)

#### P0 — 킬러 피처 (차별화)

| # | 기능 | 설명 | 유저 니즈 |
|---|------|------|---------|
| F1 | **compare** | 2-4개 케이스를 동일 뷰에서 나란히 비교 렌더 | 설계 비교, 격자 수렴, A/B 테스트 |
| F2 | **batch_render** | JSON 매니페스트로 N개 이미지를 한번에 생성 | 표준 보고서 이미지 세트 |
| F3 | **probe_timeseries** | 특정 좌표의 시계열 데이터 추출 + 그래프 | 수렴 확인, 센서 데이터 |
| F4 | **diff** | 두 데이터셋의 필드 차이 (error map) | 격자 수렴, 솔버 비교 |

#### P1 — 생산성 향상

| # | 기능 | 설명 | 유저 니즈 |
|---|------|------|---------|
| F5 | **annotate** | 이미지에 화살표, 텍스트, 치수선 추가 | 논문 figure, 보고서 |
| F6 | **read_functionobjects** | OpenFOAM functionObjects (.dat) 파싱 + 그래프 | 수렴 모니터링 |
| F7 | **boundary_conditions** | OpenFOAM BC 시각화 (inlet/outlet/wall 색분리) | 설정 검증 |
| F8 | **mesh_quality** | 메쉬 품질 지표 (skewness, aspect ratio) 시각화 | 메쉬 검증 |
| F9 | **section_report** | 표준 보고서 섹션 생성 (마크다운 + 이미지) | 자동 보고서 |

#### P2 — 학술/고급

| # | 기능 | 설명 | 유저 니즈 |
|---|------|------|---------|
| F10 | **latex_figure** | LaTeX-ready figure 생성 (pgfplots 데이터 포함) | 논문 figure |
| F11 | **style_preset** | 저널별 스타일 (Nature, AIAA, JFM...) | 학술 논문 |
| F12 | **validation_plot** | 실험 데이터 vs 시뮬레이션 비교 그래프 | 검증(V&V) |
| F13 | **residual_plot** | OpenFOAM/STAR-CCM+ 잔차 이력 그래프 | 수렴 판단 |
| F14 | **force_monitor** | 항력/양력 시계열 그래프 | 공력 분석 |

---

## 우선순위 매트릭스

```
              높은 차별화
                  │
         F1      │     F4
       compare   │    diff
                  │
  높은 ──────────┼────────── 낮은
  니즈 빈도      │          니즈 빈도
                  │
         F2      │     F10
      batch      │   latex_fig
         F3      │     F11
      probe_ts   │   style_preset
                  │
              낮은 차별화
```

### 구현 순서 제안

**Sprint 1 (v0.2.0)**: F1 compare + F2 batch_render
- 가장 높은 니즈 × 높은 차별화
- 경쟁자(LLNL) 대비 확실한 우위
- "AI가 설계 A vs B를 한눈에 비교" → 킬러 데모

**Sprint 2 (v0.3.0)**: F3 probe_timeseries + F6 read_functionobjects
- OpenFOAM 유저 직접 타겟
- 수렴 확인 = 매일 하는 작업 → 높은 사용 빈도

**Sprint 3 (v0.4.0)**: F4 diff + F5 annotate
- 학술 유저 타겟
- 격자 수렴 연구, 솔버 검증

**Sprint 4 (v0.5.0)**: F9 section_report + F13 residual_plot
- 자동 보고서 = "이것만으로도 viznoir 쓸 이유"
- 산업계 도입의 마지막 퍼즐

---

## 킬러 유저 시나리오 (마케팅용)

### 시나리오 1: "30초 설계 비교"
```
User: "Case_A와 Case_B의 pressure를 같은 뷰에서 비교해줘"
AI: [compare tool] → 2-panel 이미지, 동일 colorbar, 차이 통계
```
→ 현재 ParaView: 15분 (각 파일 로드 → 뷰 맞추기 → 스크린샷)

### 시나리오 2: "원격 수렴 확인"
```
User: "HPC에서 돌리고 있는 시뮬레이션 수렴 됐어?"
AI: [read_functionobjects] → residual plot + "1e-4 이하, 수렴됨"
```
→ 현재: SSH → tail log → ParaView에서 수동 그래프

### 시나리오 3: "논문 figure 일괄 생성"
```
User: "이 시뮬레이션으로 Figure 3-7을 만들어줘. AIAA 스타일로."
AI: [batch_render] → 5개 figure, 일관된 스타일, LaTeX 캡션 포함
```
→ 현재: ParaView + matplotlib + Inkscape = 2시간

### 시나리오 4: "과제 자동 보고서"
```
User: "이 결과로 보고서 만들어줘"
AI: [section_report] → 마크다운 + 이미지 세트 + 통계표
```
→ 현재: 학생이 1시간 고생

---

## 검증 필요 사항

1. **대용량 데이터 성능**: 현재 VTK 예제(수 MB) → 실제(수 GB~수십 GB)에서 성능?
2. **멀티블록/파티션 데이터**: OpenFOAM parallel 결과(processor0~N)를 올바르게 합치는지?
3. **시계열 데이터 메모리**: 1000+ timestep 로드 시 메모리 사용량?
4. **colorbar 일관성**: 동일 범위 보장이 compare에서 되는지?
5. **해상도 vs 파일 크기**: 300dpi 논문용 이미지의 크기 관리?
