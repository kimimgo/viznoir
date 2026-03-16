---
name: oss-workflow
description: >-
  Open-source project success workflow for viznoir. Codifies contributor
  onboarding, release management (Release Please + PyPI), issue triage,
  and showcase curation. Triggers: release, contributor, onboarding,
  PyPI publish, issue triage, showcase, CHANGELOG, good first issue
---

# OSS Workflow

## 1. Contributor Onboarding
- New issue/PR → label `good-first-issue` if appropriate
- Review with friendly, educational tone
- After merge → thank-you comment + mention in CHANGELOG
- Track contributors: Shirish-12105 (#11), himax12 (#7)

## 2. Release Management
1. Check CHANGELOG.md for completeness
2. Release Please auto-creates version bump PR on main push
3. Merge Release Please PR → GitHub Release auto-published
4. PyPI publish via `publish.yml` (OIDC trusted publisher)
5. Update README badges if needed
- **Note**: PyPI Trusted Publisher must be configured at pypi.org

## 3. Issue Triage
- Categorize: bug / feature / question / showcase
- Assess reproducibility for bugs
- Label priority: P0 (critical) / P1 (important) / P2 (nice-to-have)
- Assign to milestone (v0.8.0, v0.9.0, backlog)

## 4. Showcase Curation
- New domain data → `inspect_data` → `cinematic_render`
- Add to README showcase gallery
- Datasets at `/mnt/dataset/viznoir-showcase/` (4.1GB, 16 domains)
- Connection: awesome-ai-cae list for viznoir exposure
