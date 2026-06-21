# E2E Evidence — #64 Stable API + SemVer & deprecation policy

- **Date**: 2026-06-16
- **Scenario**: `e2e/scenarios/api_stability_e2e.py`

## What was delivered

- `docs/api-stability.md` — defines the public API surface (24 MCP tools,
  resources, prompts, `pipeline.models`, CLI, `VIZNOIR_*` env), the SemVer
  guarantee (PATCH/MINOR/MAJOR), the deprecate→warn→remove cycle, and a
  maintainer breaking-change checklist.
- `viznoir/_deprecation.py` — `deprecated()` decorator + `warn_deprecated()` that
  **enforce** the policy in code (consistent `DeprecationWarning` naming the
  version, removal target, and replacement).

## End-to-end demonstration

```
result='rendered'
warning='legacy_render is deprecated since viznoir 1.0.0 and will be removed in 2.0.0. Use render instead.'
```

Checks (7/7 PASS):

```
[PASS] deprecated callable still returns      (no behaviour change)
[PASS] emits DeprecationWarning
[PASS] warning names since + removal           (1.0.0 / 2.0.0)
[PASS] warning names replacement               (render)
[PASS] carries __deprecated__ metadata
[PASS] -W error makes it fail-fast             (clients can hard-fail on deprecated API)
[PASS] api-stability.md exists                 (Semantic Versioning policy documented)
```

The public tool surface itself is already pinned by
`tests/test_tools/test_server_registration.py` + `test_mcp_compliance.py` (name
inventory + count), so the 1.0 freeze is test-enforced, not just documented.

## Unit coverage

`tests/test_deprecation.py` — 7 tests, `_deprecation.py` at **100%**. Suite: 1771
tests. ruff + mypy (89 files) clean.
