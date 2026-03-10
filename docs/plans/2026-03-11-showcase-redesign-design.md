# Showcase Redesign Design

**Date**: 2026-03-11
**Goal**: README를 도메인 전문가(CFD/FEA 엔지니어) 대상으로 재구성하여 credibility 확보

## Target Audience

DualSPHysics 패턴 — 학술/산업 도메인 전문가가 "이거 진짜 쓸 수 있겠다" 판단하는 구조

## Design Decisions

### Before/After Hero
- **Before**: ParaView GUI 5단계 워크플로우 (Open → Apply → Filter → Camera → Export)
- **After**: viznoir 1줄 자연어 프롬프트 → 동일 결과
- 형식: 텍스트 기반 비교 (이미지 불필요 — 코드 자체가 proof)

### README 구조 (위→아래)

1. **Logo + Tagline + Badges** — 현행 유지
2. **Before/After Hero** — ParaView GUI workflow vs viznoir prompt (NEW)
3. **Science Storytelling** — inspect_physics → cinematic × 4 → compose (기존 강화)
4. **Domain Gallery** — 카테고리별 6개 큐레이션 (기존 구조 개선)
5. **Quick Start** — Claude plugin / pip / Docker / MCP config
6. **What You Get** — 4가지 핵심 차별점
7. **vs Alternatives** — 비교표
8. **Contributing + License**

### Gallery 큐레이션 (6개)

| 카테고리 | 이미지 | 캡션 |
|----------|--------|------|
| External Aero | drivaerml_cp | DrivAer-ML Cp (1.4M cells) |
| Medical | ct_head_contour | CT Head Isosurface |
| Internal Flow | streamlines | Carotid Blood Flow |
| HVAC | office_flow | Office Ventilation |
| Structural FEA | arch_structural | Arch Bridge Stress |
| Mesh Processing | dragon | Stanford Dragon (870K faces) |

### 제외 사항

- GIF 생성은 이번 범위 밖 (정적 이미지로 충분)
- 별도 showcase 페이지는 랜딩 사이트에 이미 존재
- Tech Specs 섹션은 vs Alternatives 표로 대체

## Approved

- PM Interview 3라운드 완료 (Mom Test, Target Persona, Before/After 형식)
- DualSPHysics형 도메인 전문가 타겟 확정
- ParaView GUI 비교 형식 확정
