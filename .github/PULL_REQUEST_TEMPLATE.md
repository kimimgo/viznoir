## Description

<!-- What does this PR do? Why is this change needed? -->

## Related Issues

<!-- Fixes #123 — use "Fixes" to auto-close the issue on merge -->

## Test Plan

<!-- How was this tested? Include commands you ran and relevant output. -->

## Quality Gate Checklist

All gates are enforced by CI. Check these locally before pushing:

- [ ] `ruff check src/ tests/` — zero lint errors
- [ ] `ruff format --check src/ tests/` — zero format violations
- [ ] `mypy src/viznoir/ --ignore-missing-imports` — zero type errors
- [ ] `pytest --cov=viznoir -q` — all tests pass, coverage >= 80%
- [ ] New code has corresponding tests (no untested logic)
- [ ] No secrets or credentials in the diff
- [ ] CHANGELOG.md updated (if user-facing change)

## Breaking Changes

<!-- Does this PR break existing behavior? If yes, describe the impact. -->

N/A

## PR Size

<!-- PRs under 200 lines get reviewed fastest. If this is large, explain why it can't be split. -->
