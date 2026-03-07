# viznoir v0.5.0 — Science Storyteller Design

**Date**: 2026-03-07
**Status**: Approved
**Phase**: 2 of 3 (v0.4.0 Core Power → **v0.5.0 Science Storyteller** → v0.6.0 Cinema Quality)

## Philosophy

> VTK 데이터에서 인사이트를 추출하고, 스토리텔링 소재를 생성하여,
> 학회 발표와 논문에 쓸 자료를 만든다. 이것이 viznoir의 철학과 경쟁력이다.

핵심은 렌더링 품질이 아니라 **"어디를 봐야 하는지 아는 것"**.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                LLM Agent (Claude)                  │
│  스토리 기획 · 인사이트 해석 · 내러티브 구성        │
└──────┬──────────────────────────────┬─────────────┘
       │ MCP tool calls               │ prompts/resources
       ▼                              ▼
┌──────────────────────────────────────────────────┐
│              viznoir MCP Server                    │
│                                                    │
│  analyze_data (NEW)    19 existing tools            │
│  compose_assets (NEW)  render/slice/contour/...     │
│                                                    │
│  story_planning prompt (NEW)                       │
│  storytelling resource (NEW)                       │
│                                                    │
│  viznoir.anim: easing ✅ latex ✅                   │
│    + timeline (NEW) + transitions (NEW)            │
│    + compositor (NEW)                              │
└──────────────────────────────────────────────────┘
```

**원칙**: viznoir = 분석 + 도구 + 합성. 스토리 기획 판단은 LLM에게 위임.

## New MCP Tool: `analyze_data`

VTK 데이터 → Level 2 물리 인사이트 리포트.

**Input**:
- `file_path: str` — VTK/OpenFOAM/CGNS 파일
- `focus: str | None` — 특정 필드 집중 분석
- `domain: str | None` — "cfd" | "fea" | "thermal" 힌트

**Output (Level 2)**:
```json
{
  "summary": {
    "num_points": 352841,
    "bounds": [[0, 10], [0, 2], [0, 1]],
    "fields": ["Pressure", "Velocity"],
    "domain_guess": "cfd"
  },
  "field_analyses": [
    {
      "name": "Pressure",
      "stats": {"min": -1200, "max": 3400, "mean": 820, "std": 450},
      "physics_context": "Large pressure gradient suggests strong flow acceleration",
      "anomalies": [
        {"type": "local_extremum", "location": [3.2, 0.5, 0.5], "value": 3400, "significance": "high"}
      ],
      "recommended_views": [
        {"type": "slice", "params": {"origin": [3.2, 0, 0], "normal": [1, 0, 0]}, "reason": "Pressure peak cross-section"}
      ]
    }
  ],
  "cross_field_insights": [
    {"type": "correlation", "fields": ["Pressure", "Velocity"], "note": "Inverse correlation — Bernoulli-consistent"}
  ],
  "suggested_equations": [
    {"context": "pressure-velocity coupling", "latex": "p + \\frac{1}{2}\\rho v^2 = \\text{const}", "name": "Bernoulli"}
  ]
}
```

**Implementation**: `engine/analysis.py` (~400 LOC)
- `_compute_field_stats()` — VTK native statistics
- `_detect_anomalies()` — gradient magnitude + local extrema
- `_infer_physics_context()` — physics_defaults lookup
- `_recommend_views()` — anomaly location → tool parameters
- `_cross_field_analysis()` — spatial correlation

## New MCP Tool: `compose_assets`

에이전트가 생성한 asset들을 조합.

**Input**:
- `assets: list[AssetDef]` — render/latex/plot/text
- `layout: str` — "story" | "grid" | "slides" | "video"
- `title`, `width`, `height`

**Layout modes**:

| Layout | Output | Use case |
|--------|--------|----------|
| story | 1 image (1920x1080) | Dashboard, SNS |
| grid | N×M grid image | Paper figure |
| slides | PNG sequence | Marp/PPT input |
| video | MP4 (30fps) | Conference talk |

**Video mode** supports scenes with duration + transitions:
```json
{
  "scenes": [
    {"assets": [0], "duration": 3.0, "transition": "fade_in"},
    {"assets": [0, 1], "duration": 4.0, "transition": "dissolve"}
  ]
}
```

## New Prompt: `story_planning`

Guides the LLM to structure a narrative from analyze_data results:
1. HOOK — most surprising finding
2. CONTEXT — what the simulation is
3. EVIDENCE — recommended_views executed in order
4. EQUATION — suggested_equations at the right moment
5. CONCLUSION — engineering judgment

## New Resource: `viznoir://storytelling`

Scene templates (overview, zoom_anomaly, cross_section, equation_overlay),
narrative patterns per domain (cfd, fea, thermal), annotation styles.

## Animation Package (`viznoir.anim`)

| Module | Status | LOC | Role |
|--------|--------|-----|------|
| easing.py | ✅ done | 125 | 20 rate functions |
| latex.py | ✅ done | 278 | LaTeX → SVG → PNG + cache |
| timeline.py | NEW | ~250 | Scene sequencing + duration |
| transitions.py | NEW | ~200 | fade/dissolve/wipe/per-term |
| compositor.py | NEW | ~300 | Frame compositing + ffmpeg |

## Performance Optimization

| Bottleneck | Current | Target | Method |
|------------|---------|--------|--------|
| LaTeX render | 105ms | <30ms | SVG cache (skip recompile) |
| cinematic_render | 195ms | <150ms | VTK pipeline reuse |
| compose (video) | 5ms/frame | maintain | Pillow compositing |
| analyze_data | new | <2s | VTK native C++ stats |

## File Structure

```
src/viznoir/
├── anim/
│   ├── latex.py           (modify: add cache)
│   ├── timeline.py        NEW
│   ├── transitions.py     NEW
│   └── compositor.py      NEW
├── engine/
│   └── analysis.py        NEW
└── tools/
    ├── analyze.py          NEW
    └── compose.py          NEW

server.py                  (modify: +2 tools, +1 prompt, +1 resource)
```

**Total new code**: ~1,400 LOC implementation + ~800 LOC tests

## Success Criteria

1. `analyze_data` on wavelet dataset returns physics context + anomaly locations + recommended views
2. LLM agent uses analyze_data → plans story → calls existing tools → calls compose_assets
3. `compose_assets layout=video` produces 30-second MP4 from cached assets in <15s
4. Full pipeline (analyze → plan → render → compose) completes in <2 minutes
5. LaTeX cache: repeat render <30ms

## Out of Scope

- Manim dependency (optional future addition)
- Real-time preview
- TTS / voice narration
- Write-on stroke animation (Phase 3 consideration)
- Simulation steering
