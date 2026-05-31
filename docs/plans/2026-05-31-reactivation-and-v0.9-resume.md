# viznoir 재활성화 + v0.9.0 재개 (2026-05-31)

> 7주간 정지(2026-04-09~)했던 프로젝트를 현실에 맞춰 정리하고 로드맵을 재개하기 위한 plan.
> 기존 로드맵 [`2026-03-12-roadmap.md`](./2026-03-12-roadmap.md)의 현황 갱신본.

## 현황 (계획 vs 현실)

| 마일스톤 | 상태 |
|---------|------|
| v0.7.0 Release & Promote | ✅ 완료 |
| v0.8.0 Industrial Validation | ✅ 완료 (Fluent/CGNS/SPH 파서 + cryoEM MRC reader, 필터 warp_by_vector/threshold/glyph 포함) |
| **v0.9.0 Quality & Guard** | ❌ **미착수** ← 재개 지점 |
| v1.0.0 Production Ready | ❌ 미착수 |

**정지 기간 동안 어긋난 것:**
- 패키지 리네임(`mcp-server-viznoir → viznoir`, v0.8.1)이 커밋되지 않은 채, 그 상태로 **PyPI에 viznoir 0.8.1 수동 publish**(2026-04-15). git 태그/커밋 없음.
- git HEAD/태그는 0.8.0, PyPI는 0.8.1 → 버전 불일치. release-please는 0.9.0을 제안한 채 방치.
- dependabot PR 11개 적체(#47–#57).

## 결정

- **버전 정합 = Option B**: 0.8.1 태그 생략, 다음 정식 릴리스를 **0.9.0**으로 전진. 수동 0.8.1은 일회성 인정. 이후 release-please + CI(trusted publisher)로 일원화.
- **릴리스 정책 수정**: 수동 `twine` 금지, CI 경유만.

## 재활성화 체크리스트

- [x] 리네임 + 문서 동기화 커밋 (브랜치 `chore/rename-to-viznoir`)
- [ ] dependabot PR 11개 일괄 검토 리포트
- [ ] GitHub 마일스톤 2개 + Epic/하위 이슈 등록
- [ ] (별도 인가) 브랜치 push + PR + release-please 0.9.0 머지 → PyPI 0.9.0
- [ ] v0.9.0 구현 착수

## v0.9.0 — Quality & Guard (다음 마일스톤)

물리 가드 + autoexp 파일럿. "환각 방지" 기초.

| 작업 | 산출물 |
|------|--------|
| Physics Guard | `guard/rules.py`(도메인 규칙) + `guard/validator.py`(pass/warn/fail) |
| validate_render tool | 렌더 후 검증 MCP tool (tools 23→24) |
| 품질 메트릭 | `engine/quality.py` (contrast, edge entropy, field coverage) |
| Autoexp 파일럿 | `core/autoexp.py` (modify→render→measure→keep/revert; 기존 `presets/registry.py` 활용) |
| Quality gates | 커버리지 80%→90%, 벤치마크 회귀 CI |

## v1.0.0 — Production Ready

| 작업 | 산출물 |
|------|--------|
| Stable API | SemVer 보증 + deprecation 정책 문서 |
| 릴리스 파이프라인 정상화 | CI trusted publisher 일원화, Docker Hub 이미지 |
| 플러그인 시스템 | user-defined filters/parsers/presets |
| Remote render | WebSocket 스트리밍 |
| 문서 | 전체 tool 레퍼런스(23+) + 도메인 갤러리 + 마이그레이션 가이드 |
| 검증 | 3개 도메인(CFD/FEA/Medical) E2E |
