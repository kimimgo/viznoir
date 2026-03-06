# parapilot OSS Strategy

> Last updated: 2026-03-06 | Status: Pre-launch

---

## 1. KPI Dashboard

### Current Snapshot (2026-03-06)

| Metric | Value | Signal |
|--------|-------|--------|
| Stars | 0 | No social proof yet |
| Forks | 4 | Interest exists (fork-before-star pattern) |
| Contributors | 2 (kimimgo 82, NikanEidi 1) | Need 3+ external |
| Clones (14d) | 604 total / 137 unique | High — bot or crawler? |
| Views (14d) | 2 / 1 unique | Almost zero organic discovery |
| Referrers | github.com only | No external traffic source |
| Open Issues | 16 (9 good-first-issue) | Healthy backlog |
| Closed Issues | 5 | Low throughput |
| PRs | 1 merged, 1 closed | Contributor pipeline starting |
| PyPI downloads | ~0 | Not yet promoted |
| MCP registries | 0 | Undiscoverable |

### Targets

| Metric | 1-month | 3-month | 6-month |
|--------|---------|---------|---------|
| Stars | 30+ | 100+ | 200+ |
| Forks | 10+ | 25+ | 50+ |
| Contributors | 5+ | 10+ | 20+ |
| PyPI downloads/mo | 200+ | 1,000+ | 5,000+ |
| Views (14d) | 100+ | 500+ | 2,000+ |
| MCP registries | 3+ | 5+ | 5+ |
| JOSS paper | - | submitted | accepted |

### Gap Analysis

**Critical gap**: Views=2 vs Clones=604. 이는 봇/크롤러 클론이거나 직접 링크 접근.
진짜 사용자는 거의 없다. **발견 가능성(discoverability)이 #1 병목**.

---

## 2. Automation Inventory

### Active (7 workflows + 3 configs)

| # | Automation | File | What it does |
|---|-----------|------|-------------|
| 1 | CI | `ci.yml` | ruff + mypy strict + pytest, Python 3.10/3.11/3.12/3.13 |
| 2 | Deploy | `deploy.yml` | Astro landing page → GitHub Pages |
| 3 | Publish | `publish.yml` | Tag push → PyPI trusted publisher |
| 4 | Auto-merge | `auto-merge.yml` | Dependabot minor/patch → auto squash-merge |
| 5 | Stale | `stale.yml` | 60d stale mark → 14d auto-close |
| 6 | Welcome | `welcome.yml` | First issue/PR → greeting message |
| 7 | Release Drafter | `release-drafter.yml` | PR labels → draft release notes |
| 8 | Dependabot | `dependabot.yml` | pip + npm weekly updates |
| 9 | All Contributors | `.all-contributorsrc` | README contributor table |
| 10 | Issue templates | `.github/ISSUE_TEMPLATE/` | Bug/feature/docs templates |

### Recommended (not yet implemented)

| Priority | Automation | Impact | Effort |
|----------|-----------|--------|--------|
| **P1** | CodeQL security scan | Trust signal, catches vulns | 30min |
| **P1** | Auto-label by path | Less manual triage | 30min |
| **P2** | PR title lint | Enforce conventional commits | 15min |
| **P2** | Lock resolved issues | Reduce noise | 15min |
| **P3** | Discord/Discussions bot | Community notifications | 2hr |

### Contributor Automation Flow

```
New contributor arrives
  ↓
[Issue Template] → structured bug/feature request
  ↓
[good-first-issue label] → discoverable on GitHub Explore
  ↓
[CONTRIBUTING.md] → setup guide + architecture walkthrough
  ↓
[Welcome Bot] → greeting on first PR
  ↓
[CI] → immediate feedback (lint/type/test)
  ↓
[Maintainer review] → 24-48h target
  ↓
[All Contributors] → README recognition
  ↓
[Release Drafter] → name in release notes
```

---

## 3. Promotion Strategy

### Phase A: Discoverability (THIS WEEK)

**Problem**: Views=2. Nobody can find us.

| Action | Channel | Expected Impact | Status |
|--------|---------|----------------|--------|
| MCP Registry: Smithery.ai | Registry | High — MCP users browse here | `smithery.yaml` ready |
| MCP Registry: awesome-mcp-servers | GitHub | High — 8k+ stars list | PR to submit |
| MCP Registry: Glama.ai | Registry | Medium | Profile to create |
| MCP Registry: mcp.run | Registry | Medium | Submit |
| MCP Registry: Anthropic | Registry | High — official | Apply |
| GitHub Topics | Search | 15 topics set | Done |
| PyPI keywords | Search | Set in pyproject.toml | Done |
| GitHub description | Search | Updated | Done |

### Phase B: Community Launch (Week 2-3)

| Action | Channel | Audience | Angle |
|--------|---------|----------|-------|
| Show HN | Hacker News | Developers | "Show HN: parapilot — render your CFD simulations with AI, no GUI needed" |
| r/CFD post | Reddit | CFD engineers | "I built a headless tool that lets AI render your simulation results" |
| r/OpenFOAM post | Reddit | OpenFOAM users | "Render OpenFOAM cases from your terminal via Claude/Cursor" |
| r/Python post | Reddit | Python devs | "MCP server that gives LLMs eyes for VTK simulation data" |
| CFD-Online | Forum | Industry | Tool listing + demo |
| Product Hunt | Platform | General tech | "AI-powered CAE post-processing" |

**Posting Rules**:
- Tuesday-Thursday, 9-11am EST (HN optimal)
- Lead with the DrivAerML 8.8M cell demo image
- Always include: "18 tools, 826 tests, MIT license"
- Never say "better than ParaView" — say "complements ParaView"

### Phase C: Academic & Deep Community (Month 2-6)

| Action | Timeline | Impact |
|--------|----------|--------|
| JOSS paper submission | Month 2 | Academic citation, credibility |
| Zenodo DOI | With first release | Citable artifact |
| OpenFOAM Workshop talk | Month 3-4 | Direct CFD audience |
| SciPy poster | Month 4-5 | Python scientific community |
| GSoC project listing | Annually | Student contributors |

---

## 4. SEO & Discovery Keywords

### Primary Keywords (high intent)

| Keyword | Search Context | Where to Target |
|---------|---------------|-----------------|
| `mcp server cfd` | MCP users looking for CFD tools | README, PyPI, registries |
| `headless vtk rendering` | Engineers automating viz | Landing page, blog |
| `openfoam post processing python` | OpenFOAM users | README, Reddit |
| `paraview alternative headless` | Frustrated with ParaView GUI | Comparison table |
| `claude code simulation` | Claude users + engineers | Plugin marketplace |

### Secondary Keywords

| Keyword | Context |
|---------|---------|
| `vtk offscreen rendering docker` | DevOps/CI pipeline users |
| `cfd visualization api` | Building visualization apps |
| `scientific visualization mcp` | MCP ecosystem explorers |
| `model context protocol engineering` | MCP early adopters |
| `ai-assisted cae` | Industry innovation scouts |

### Long-tail (blog/tutorial targets)

- "how to render openfoam results without gui"
- "vtk offscreen rendering python docker"
- "automate cfd post-processing with ai"
- "claude code engineering workflow"
- "mcp server for scientific data"

### GitHub Topics (15, active)

```
cae, cfd, claude-code, headless-rendering, mcp,
model-context-protocol, paraview, post-processing,
simulation, vtk, openfoam, fea,
scientific-visualization, ai-tools, engineering
```

---

## 5. Branding

### Identity

| Element | Value |
|---------|-------|
| Name | **parapilot** |
| Tagline | "Headless CAE post-processing for AI assistants" |
| One-liner | "Ask your AI to render your simulation" |
| Accent | `#00d4ff` |
| Dark BG | `#0a0a0a` |
| Font body | Inter |
| Font code | JetBrains Mono |
| Tone | Technical, confident, concise. Zero hype. |

### Positioning Matrix

```
                    GUI Required
                    ↑
     ParaView       |       Kitware VTK-MCP
     (full IDE)     |       (docs only)
                    |
  ←──────────────── + ──────────────────→
   Few tools        |              Many tools
                    |
     LLNL           |       parapilot
     paraview_mcp   |       (headless, 18 tools,
     (GUI-attached) |        826 tests, plugin)
                    |
                    ↓
                    Headless
```

**We own the bottom-right quadrant**: headless + many tools + tested.

### What We Are

> The only headless scientific visualization server that speaks MCP.
> Zero GUI, zero boilerplate — just ask your AI to render your simulation.

### What We Are NOT

- Not a ParaView replacement (we complement it)
- Not a complete CAE platform
- Not a simulation solver/runner
- Not "AI that understands physics" (we render, not simulate)

### Messaging by Audience

| Audience | Hook | Proof Point |
|----------|------|-------------|
| **CFD Engineers** | "Render your OpenFOAM/CGNS with a single prompt" | DrivAerML 8.8M cell demo |
| **AI Developers** | "Give your LLM eyes for simulation data" | 18 tools, Claude plugin, stdio/SSE |
| **Researchers** | "Reproducible viz pipelines in version control" | JSON DSL, deterministic output |
| **OSS Contributors** | "Well-tested, well-documented, real impact" | 826 tests, 83% coverage, 9 good-first-issues |
| **Engineering Managers** | "Automate post-processing in CI/CD" | Docker GPU, batch_render, headless |

### Visual Assets Needed

| Asset | Spec | Status | Issue |
|-------|------|--------|-------|
| Logo (SVG) | Wireframe mesh + pilot motif, `#00d4ff` → `#0066ff` gradient | Not started | #23 |
| Social Preview | 1280x640, dark bg, DrivAerML + badges | Not started | #23 |
| OG Image | 1200x630, for landing page `<meta>` | Not started | - |
| Favicon | 16/32/192px PNG from logo | Not started | - |

---

## 6. Contributor Growth Strategy

### Current Pipeline

```
Discovery: Views=2 ← BOTTLENECK
  ↓
Interest: Forks=4, Clones=604
  ↓
First Contact: Issues opened=21, Comments on issues
  ↓
First PR: 1 merged (NikanEidi), 1 assigned (Darshankg18)
  ↓
Repeat: 0 repeat contributors
```

### Tactics

#### A. Good First Issue Pipeline (always 5-8 open)

| Category | Current Count | Target |
|----------|--------------|--------|
| Documentation | 3 (#7, #21, #23) | 2-3 |
| Type hints | 2 (#13, #14) | 1-2 |
| Testing | 3 (#16, #17, #22) | 1-2 |
| Colormaps/presets | 2 (#6, #15) | 1-2 |
| Features | 1 (#9) | 1 |
| **Total** | **11** | **5-8** |

**Rule**: When one is closed, open a new one within 48h.

#### B. Issue Quality Standards

Every issue must have:
- `## Summary` — what and why
- `## What to do` — step-by-step instructions
- `## Files to modify` — exact file paths
- `## Difficulty` — Beginner/Intermediate/Advanced
- Labels: `good first issue` + category + `help wanted`

#### C. Recognition Ladder

| Level | Trigger | Recognition |
|-------|---------|-------------|
| First PR merged | 1 PR | Welcome bot + All Contributors table |
| Active contributor | 3+ PRs | CONTRIBUTORS.md mention |
| Core contributor | 10+ PRs or major feature | Release notes credit |
| Co-author | Significant contribution | JOSS paper co-authorship |

#### D. Response Time Targets

| Event | Target | Current |
|-------|--------|---------|
| New issue | Acknowledge within 24h | OK |
| New PR | First review within 48h | OK |
| Review requested changes | Respond within 24h | OK |
| Stale issues | Auto-mark at 60d, close at 74d | Automated |

#### E. Seasonal Campaigns

| Month | Campaign | Goal |
|-------|----------|------|
| October | Hacktoberfest labels | 5+ PRs |
| March-April | GSoC applications | 1-2 students |
| Anytime | "Help Wanted" board | Ongoing |

---

## 7. Competitive Moat

Things competitors cannot easily replicate:

| Moat | Why It's Defensible |
|------|-------------------|
| **826 tests** | Months of work; LLNL/paraview_mcp has 0 |
| **Pipeline DSL** | Declarative JSON filter chains + code gen |
| **Physics-aware defaults** | Field name → physical quantity auto-detection |
| **Split-pane animation** | Synchronized multi-view + time-series graph GIF |
| **Dual execution** | Local VTK + Docker GPU seamless switching |
| **Claude Code plugin** | One-line install: `claude install kimimgo/parapilot` |
| **Cinematic renderer** | PCA auto-camera + 3-point lighting + SSAO + PBR |

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| ParaView adds native MCP | Medium | High | Focus on headless + CI/CD differentiator |
| VTK breaking change | Low | Medium | Pin VTK version, test matrix |
| Zero traction after launch | Medium | High | Iterate on messaging, try different channels |
| Sole maintainer burnout | High | Critical | Build contributor base, automate everything |
| Security vulnerability | Low | High | CodeQL, Dependabot, minimal attack surface |

---

## 9. Execution Checklist

### This Week

- [ ] Register on Smithery.ai
- [ ] PR to awesome-mcp-servers
- [ ] Register on Glama.ai
- [ ] Register on mcp.run
- [ ] Apply to Anthropic registry
- [ ] Set up PyPI Trusted Publisher
- [ ] Add CodeQL workflow
- [ ] Create social preview image

### Next Week

- [ ] Post on Hacker News (Show HN)
- [ ] Post on r/CFD
- [ ] Post on r/OpenFOAM
- [ ] Post on r/Python
- [ ] First PyPI release (v0.1.0 tag)

### Month 1

- [ ] 5+ MCP registry listings
- [ ] 30+ GitHub stars
- [ ] 5+ contributors
- [ ] CFD-Online listing
- [ ] Product Hunt launch

### Month 2-3

- [ ] JOSS paper draft
- [ ] Zenodo DOI
- [ ] 100+ stars
- [ ] 10+ contributors
- [ ] Conference abstract submitted
