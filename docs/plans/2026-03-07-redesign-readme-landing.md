# README + Landing Page Redesign — "Ruff Style" Benchmark-Driven

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** README와 랜딩페이지를 벤치마크 주도("증거 먼저") 구조로 완전 리디자인하여, 개발자가 3초 만에 가치를 파악하고 30초 만에 설치할 수 있게 한다.

**Architecture:** `release/0.3.0` long-lived branch에서 작업. 두 개의 Agent Team이 feat/* worktree로 분리 병행 — Team A(README + 에셋)와 Team B(Landing Page). Lead(cc)는 main에서 의사결정, release/0.3.0으로 머지, 품질 게이트를 담당.

**Tech Stack:** Astro 5 + Tailwind 3 (www/), Markdown (README), WebP/PNG (showcase assets)

---

## Version Roadmap

| Version | 코드네임 | 핵심 목표 | 상태 |
|---------|---------|----------|------|
| **v0.1.0** | Initial | 13 tools, 310 tests | ✅ released, tagged |
| **v0.2.0** | Quality | 18 tools, 1134 tests, CI green, MCP Tasks | 🏷️ **태깅 예정** (현재 main) |
| **v0.3.0** | Public Face | README/랜딩 리디자인, PyPI publish | 🎯 **이번 작업** |
| **v1.0.0** | Production | 실사용 검증, stable API, 커뮤니티 피드백 | 미래 |

### Semantic Versioning 원칙
- **PATCH** (0.x.1): 버그 픽스, 문서 수정 → main 직접 커밋
- **MINOR** (0.x.0): 기능 추가, 리디자인 → `release/0.x.0` 브랜치
- **MAJOR** (x.0.0): Breaking change → `release/x.0.0` 브랜치

---

## Branch Strategy: Release Branch Model

```
main ─────●──── v0.2.0 ────●──── v0.3.0 ────●──── v1.0.0
           │     (태깅)      │     (머지)      │
           │                 │                 │
           └── release/0.3.0 ┘                 └── release/1.0.0
                ├── feat/redesign-readme    ← Team A worktree
                ├── feat/redesign-landing   ← Team B worktree
                └── feat/pypi-publish       ← (향후 단독 작업)
```

### Branch Lifecycle

| 브랜치 | 수명 | 분기 원점 | 머지 대상 | 관리자 |
|--------|------|----------|----------|--------|
| `main` | **영구** | — | — | Lead(cc) only |
| `release/0.3.0` | **v0.3.0 출시까지** | main (v0.2.0 태그 후) | main | Lead(cc) |
| `feat/redesign-readme` | Task 완료까지 | release/0.3.0 | release/0.3.0 | Team A |
| `feat/redesign-landing` | Task 완료까지 | release/0.3.0 | release/0.3.0 | Team B |

### Rules
1. **main**: Lead(cc)만 머지. 5 Quality Gates 전부 통과 필수. 모든 릴리즈 태그는 main에서.
2. **release/0.x.0**: 해당 버전의 통합 브랜치. feat/* 결과물 축적. CI green 유지.
3. **feat/***: 단일 팀 소유. 파일 소유권 엄격 분리. 완료 후 release/에 머지.

### Merge Flow
```
feat/redesign-readme ──→ release/0.3.0 ──→ main (v0.3.0 태그 + GitHub Release)
feat/redesign-landing ──→ release/0.3.0 ──┘
```

### 향후 버전 적용 예시
```
release/1.0.0 (v1.0 작업 시 생성)
  ├── feat/real-data-validation
  ├── feat/streaming-support
  └── feat/community-feedback
```

---

## Agent Team Design

### Lead: cc (Opus, main branch)
- 의사결정, 디자인 방향 설정
- v0.2.0 태깅, release/0.3.0 생성
- Team A/B 결과물 리뷰 + release/0.3.0 머지
- Quality Gate 실행 (lint, build, link check)
- 최종 main 머지 + v0.3.0 태깅
- CHANGELOG, CLAUDE.md, pyproject.toml 버전 업데이트

### Team A: README + Assets (2명)
**Branch:** `feat/redesign-readme`
**Worktree:** `/tmp/parapilot-readme`

| Role | Model | 담당 파일 |
|------|-------|----------|
| **writer** | opus | `README.md`, `README.ko.md` |
| **asset-creator** | opus | `docs/assets/demo.*`, showcase 큐레이션 |

**File Ownership (배타적):**
- `README.md`, `README.ko.md`
- `docs/assets/` (신규 디렉토리)

### Team B: Landing Page (2명)
**Branch:** `feat/redesign-landing`
**Worktree:** `/tmp/parapilot-landing`

| Role | Model | 담당 파일 |
|------|-------|----------|
| **designer** | opus | 컴포넌트 구조, Tailwind 스타일, 레이아웃 |
| **developer** | opus | Astro 컴포넌트 구현, 빌드 검증, 반응형 |

**File Ownership (배타적):**
- `www/src/components/*.astro`
- `www/src/pages/index.astro`
- `www/src/styles/global.css`
- `www/tailwind.config.mjs`

### 충돌 방지 규칙
- Team A는 `www/` 하위 수정 **금지**
- Team B는 `README.md`, `README.ko.md`, `docs/` 수정 **금지**
- `www/public/showcase/` 이미지는 **읽기 전용** (양 팀 참조만, 수정은 Lead)

---

## Design Spec: README.md (Team A)

### Target: ~120줄 (현재 223줄 → 절반)

### Structure (순서 중요)

```markdown
# parapilot

> Headless CAE/CFD post-processing for AI terminals. No ParaView. No GUI.

[배지: CI | Coverage | PyPI | Python | License] (5개만)

[터미널 데모 GIF — MCP tool call → PNG 결과물, 5초 루프]

## Quick Start

[3가지 설치 방법: Claude plugin / pip / Docker]

## What You Get

[핵심 feature 3개: Headless Rendering / 18 MCP Tools / 50+ Formats]

## See It In Action

[큐레이션 6장: 2×3 그리드]
[Full gallery → 랜딩페이지 링크]

## vs Alternatives

[비교표: parapilot / ParaView(pvpython) / PyVista / VTK-direct]
[사실 기반, 존중적 톤]

## Contributing

[3줄: clone → install → test]

## License

MIT
```

### 핵심 카피

**Tagline (h1 아래):**
> Headless CAE/CFD post-processing for AI terminals. No ParaView. No GUI.

**비교표 포지셔닝:**
> 18 MCP tools that turn natural language into publication-ready renders.

**설치 우선순위:**
1. `claude install kimimgo/parapilot` (Claude Code 사용자)
2. `pip install mcp-server-parapilot` (범용)
3. `docker compose up` (격리 환경)

**비교표 (사실 기반):**

| Feature | parapilot | ParaView (pvpython) | PyVista | VTK Python |
|---------|-----------|---------------------|---------|------------|
| MCP Integration | ✅ Native 18 tools | ❌ | ❌ | ❌ |
| Headless | ✅ EGL/OSMesa | ✅ pvpython | ✅ | ⚠️ Manual |
| Docker | ✅ GPU + CPU | ⚠️ Complex | ❌ | ❌ |
| Natural Language | ✅ AI-first | ❌ | ❌ | ❌ |
| File Formats | 50+ (meshio) | 70+ | 30+ | ~20 |
| Installation | pip install | System package | pip install | pip install |
| Tests | 1134 (99% cov) | N/A | ✅ | N/A |

---

## Design Spec: Landing Page (Team B)

### Target: 5개 섹션 (현재 8개 → 5개)

### Section Flow

```
1. Hero          — 터미널 데모 + tagline + CTA
2. Proof         — 수치 4개 + feature matrix
3. Showcase      — 큐레이션 6장
4. QuickStart    — 3-step 설치
5. Footer        — 6 links
```

### Section 1: Hero (redesign)

```
┌──────────────────────────────────────────┐
│  [왼쪽 50%]                 [오른쪽 50%]  │
│                                          │
│  parapilot                  ┌──────────┐ │
│                             │ Terminal  │ │
│  Post-process               │ Demo     │ │
│  simulations from           │ (코드+   │ │
│  your terminal.             │  결과물)  │ │
│                             └──────────┘ │
│  No ParaView. No GUI.                    │
│                                          │
│  [pip install ...] [GitHub →]            │
│  Claude Code · Cursor · Gemini CLI       │
└──────────────────────────────────────────┘
```

- 2-column hero (text left, demo right)
- 배지 제거 (Hero에서), Proof로 이동
- CTA 2개: install command + GitHub
- 모바일: 1-column stack (demo 아래)

### Section 2: Proof (Stats + Comparison 통합)

```
┌──────────────────────────────────────────┐
│  18 Tools │ 1134 Tests │ 50+ Formats │ 99% Cov │
│                                          │
│  ──────────────────────────────────────── │
│                                          │
│  Feature Matrix (checkmarks)             │
│  parapilot vs ParaView vs PyVista        │
└──────────────────────────────────────────┘
```

- Stats.astro + Comparison.astro → Proof.astro로 통합
- 바 차트 제거 → 명확한 checkmark matrix

### Section 3: Showcase (축소)

큐레이션 6장:
1. DrivAerML 자동차 CFD (외부 공기역학)
2. CT Skull contour (의료)
3. Carotid streamlines (혈류)
4. Office HVAC flow (건축 환기)
5. Structural FEA stress (구조)
6. Stanford Dragon (일반 3D)

- 2×3 그리드
- "All renders from single MCP calls"
- [Full Gallery →] 링크

### Section 4: QuickStart (간소화)

- PluginShowcase 흡수 (4개 클라이언트 동일 JSON → 1번만 표시)
- 3-step: install → configure → prompt

### Section 5: Footer (확장)

6링크: GitHub | PyPI | Docs | Issues | License | Discord(placeholder)

### 삭제 대상
- `Architecture.astro` → Docs 사이트로 이동
- `PluginShowcase.astro` → QuickStart에 통합
- `Features.astro` → Proof에 압축
- `Stats.astro` → Proof에 통합
- `Comparison.astro` → Proof에 통합

---

## Asset Creation Spec

### 1. Terminal Demo

**옵션 A (GIF):** asciinema/vhs 녹화
- 800×500px, 10fps, <3MB, 5초 루프
- WebP + GIF 동시 제공

**옵션 B (정적 코드블록 + 결과 PNG):** GIF 제작이 어려우면
- 코드블록 스크린샷 + 렌더링 결과물 PNG 나란히 배치

**내용:**
```
> "Render the pressure field from cavity.foam with jet colormap"

✓ Rendered in 0.8s → cavity_pressure.png
[렌더링 결과 이미지]
```

### 2. Showcase 큐레이션

기존 88개 WebP 중 6개 선택 (README + Landing 공용):
- `drivaerml_cp.webp` — 자동차 CFD
- `ct_head_contour.webp` — 의료 CT
- `streamlines.webp` — 혈류 streamlines
- `office_flow.webp` — HVAC
- `blow_deform.webp` 또는 `arch_structural.webp` — 구조
- `dragon.webp` — 일반 3D

나머지는 www/public/showcase/에 유지 (향후 full gallery 페이지용).

---

## Implementation Tasks

### Phase 0: Version Tagging + Branch Setup (Lead)

#### Task 0.1: Tag v0.2.0 on main

**Step 1:** CHANGELOG에서 [Unreleased] → [0.2.0] 변환
```bash
# CHANGELOG.md 편집: [Unreleased] → [0.2.0] - 2026-03-07
# 하단 링크도 업데이트
```

**Step 2:** pyproject.toml 버전 업데이트
```bash
# version = "0.1.0" → version = "0.2.0"
```

**Step 3:** 태그 생성 + push
```bash
git add -A
git commit -m "release: v0.2.0 — 18 tools, 1134 tests, MCP Tasks, CI green"
git tag -a v0.2.0 -m "v0.2.0: Quality milestone — 18 tools, 1134 tests, 99% coverage"
git push origin main --tags
```

#### Task 0.2: Create release/0.3.0 branch

```bash
git checkout -b release/0.3.0
git push origin release/0.3.0
```

#### Task 0.3: Bump version to 0.3.0-dev on release branch

```bash
# pyproject.toml: version = "0.3.0.dev0"
git commit -am "chore: bump version to 0.3.0.dev0"
git push origin release/0.3.0
```

#### Task 0.4: Create worktrees for teams

```bash
# Team A worktree
git checkout release/0.3.0
git checkout -b feat/redesign-readme
git push origin feat/redesign-readme
git worktree add /tmp/parapilot-readme feat/redesign-readme

# Team B worktree
git checkout release/0.3.0
git checkout -b feat/redesign-landing
git push origin feat/redesign-landing
git worktree add /tmp/parapilot-landing feat/redesign-landing
```

#### Task 0.5: Create Agent Teams

```
TeamCreate: readme-team
  - writer (opus): README.md, README.ko.md
  - asset-creator (opus): docs/assets/, showcase 큐레이션

TeamCreate: landing-team
  - designer (opus): www/src/components/, styles
  - developer (opus): Astro 구현, 빌드 검증
```

---

### Phase 1: Team A — README + Assets (병렬)

#### Task 1.1: Write new README.md
**Worktree:** `/tmp/parapilot-readme`
**Files:** `README.md`
- Design Spec 기반 ~120줄 README 작성
- 배지 5개 (CI, Coverage, PyPI, Python, License)
- 터미널 데모 placeholder
- 큐레이션 6장 쇼케이스
- 사실 기반 비교표
- Commit: `docs: redesign README — benchmark-driven, 120 lines`

#### Task 1.2: Write new README.ko.md
**Files:** `README.ko.md`
- README.md 한국어 번역, 동일 구조
- Commit: `docs: redesign Korean README to match v2`

#### Task 1.3: Create terminal demo asset
**Files:** `docs/assets/demo.gif` (또는 정적 대안)
- 옵션 A/B 중 선택하여 제작
- Commit: `docs: add terminal demo asset for README hero`

#### Task 1.4: Push to feat/redesign-readme
```bash
git push origin feat/redesign-readme
```

---

### Phase 2: Team B — Landing Page (Phase 1과 병렬)

#### Task 2.1: Redesign Hero.astro
**Worktree:** `/tmp/parapilot-landing`
**Files:** `www/src/components/Hero.astro`
- 2-column layout (text left, demo right)
- 배지 제거, CTA 2개
- Commit: `www: redesign Hero — 2-column, demo-right, clean CTA`

#### Task 2.2: Create Proof.astro (Stats + Comparison 통합)
**Files:**
- Create: `www/src/components/Proof.astro`
- Delete: `www/src/components/Stats.astro`, `www/src/components/Comparison.astro`
- Commit: `www: create Proof section — unified stats + comparison`

#### Task 2.3: Slim down Showcase.astro
**Files:** `www/src/components/Showcase.astro`
- 80장 → 6장 큐레이션, 1개 그리드
- Commit: `www: slim Showcase to 6 curated renders`

#### Task 2.4: Merge PluginShowcase into QuickStart
**Files:**
- Modify: `www/src/components/QuickStart.astro`
- Delete: `www/src/components/PluginShowcase.astro`
- Commit: `www: merge PluginShowcase into QuickStart`

#### Task 2.5: Update Footer + page layout
**Files:**
- `www/src/components/Footer.astro` (6링크)
- Delete: `www/src/components/Architecture.astro`, `www/src/components/Features.astro`
- `www/src/pages/index.astro` (5-section: Hero/Proof/Showcase/QuickStart/Footer)
- Commit: `www: 5-section layout, remove Architecture/Features`

#### Task 2.6: Build verification
```bash
cd /tmp/parapilot-landing/www && npm install && npm run build
```
- Commit: `www: fix build issues from redesign` (필요시)

#### Task 2.7: Push to feat/redesign-landing
```bash
git push origin feat/redesign-landing
```

---

### Phase 3: Integration (Lead, release/0.3.0)

#### Task 3.1: Merge feat/redesign-readme → release/0.3.0
```bash
git checkout release/0.3.0
git merge feat/redesign-readme --no-ff -m "merge: Team A README redesign into release/0.3.0"
```

#### Task 3.2: Merge feat/redesign-landing → release/0.3.0
```bash
git merge feat/redesign-landing --no-ff -m "merge: Team B Landing Page redesign into release/0.3.0"
```

#### Task 3.3: Cross-check consistency
- [ ] README의 이미지 경로 ↔ www/public/showcase/ 일치
- [ ] README의 수치 (18 tools, 1134 tests, 99% coverage) ↔ 랜딩페이지 일치
- [ ] 비교표 내용 양쪽 동일
- [ ] 설치 명령 양쪽 동일

#### Task 3.4: Quality Gate
```bash
ruff check src/ tests/                          # G1: lint
mypy src/parapilot/ --ignore-missing-imports     # G2: type check
pytest -q                                        # G3: tests
cd www && npm run build                          # G4: www build
```

#### Task 3.5: Version finalize
```bash
# pyproject.toml: version = "0.3.0.dev0" → version = "0.3.0"
# CHANGELOG: [Unreleased] 아래에 0.3.0 섹션 추가
git commit -am "release: v0.3.0 — Public Face (README + Landing redesign)"
```

---

### Phase 4: Release (Lead, main)

#### Task 4.1: Merge release/0.3.0 → main
```bash
git checkout main
git merge release/0.3.0 --no-ff -m "release: merge v0.3.0 — Public Face redesign"
git tag -a v0.3.0 -m "v0.3.0: Public Face — README/Landing redesign, benchmark-driven"
git push origin main --tags
```

#### Task 4.2: GitHub Release 생성
```bash
gh release create v0.3.0 --title "v0.3.0: Public Face" --notes-from-tag
```

---

### Phase 5: Cleanup (Lead)

#### Task 5.1: Remove worktrees and feature branches
```bash
git worktree remove /tmp/parapilot-readme 2>/dev/null
git worktree remove /tmp/parapilot-landing 2>/dev/null
git branch -d feat/redesign-readme feat/redesign-landing
git push origin --delete feat/redesign-readme feat/redesign-landing
```

#### Task 5.2: Decide release/0.3.0 branch fate
- 옵션 A: 삭제 (v0.3.0 태그가 있으므로 브랜치 불필요)
- 옵션 B: 유지 (hotfix 0.3.1이 필요할 경우)
- **추천: 삭제** (hotfix는 main에서 직접)

```bash
git branch -d release/0.3.0
git push origin --delete release/0.3.0
```

#### Task 5.3: Update project metadata
- `CLAUDE.md`: README 줄수, 섹션 수 업데이트
- `memory/MEMORY.md`: 버전 정보 업데이트
- `TeamDelete` 양 팀

---

## Quality Checklist

### README
- [ ] ~120줄
- [ ] 배지 5개
- [ ] 터미널 데모 (GIF 또는 코드블록+PNG)
- [ ] 쇼케이스 6장
- [ ] 비교표 사실 기반, 존중적 톤
- [ ] 설치 3가지 (Claude plugin, pip, Docker)
- [ ] Contributing 3줄

### Landing Page
- [ ] 5개 섹션 (Hero, Proof, Showcase, QuickStart, Footer)
- [ ] `npm run build` 성공
- [ ] 모바일 반응형 (360px~)
- [ ] 깨진 이미지 0개
- [ ] Architecture/Features/PluginShowcase/Stats/Comparison 삭제됨

### Release
- [ ] v0.2.0 태그 존재
- [ ] v0.3.0 태그 존재
- [ ] CHANGELOG 양 버전 기록
- [ ] pyproject.toml version = "0.3.0"
- [ ] GitHub Release 생성됨

### Consistency
- [ ] 수치 일치 (tools, tests, coverage, formats) — README ↔ Landing ↔ CLAUDE.md
- [ ] 이미지 경로 일치
- [ ] 비교표 내용 일치
- [ ] 설치 명령 일치
