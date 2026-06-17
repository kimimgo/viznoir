# E2E Evidence — #62 Quality gates (90% coverage + benchmark regression)

- **Date**: 2026-06-16
- **Environment**: oliveeelab self-hosted runner, RTX 4090, EGL

## Coverage gate 80% → 90%

With the self-hosted GPU runner (#97) running the rendering tests that
GitHub-hosted CI must skip, measured coverage is now well above the new gate:

```
1751 passed, 13 skipped
TOTAL  5597 stmts, 275 missed → 95%
```

`ci.yml` coverage check raised to `--fail-under=90` (runs on Python 3.12, the
version with `VIZNOIR_RUN_GPU_TESTS=1`). 95% ≥ 90% → the gate passes with margin.

## Benchmark regression gate

`tests/test_engine/test_perf_budget_vtk.py` — 4 render-latency budget tests that
run on the self-hosted GPU runner (EGL) as part of the 3.12 test job. A render
that suddenly takes seconds fails CI. Budgets are >10× typical to ignore the
shared host's timing noise.

| benchmark | typical | budget | headroom |
|-----------|--------:|-------:|---------:|
| wavelet render (1080p) | ~150 ms | 3000 ms | ~20× |
| 480p render | ~30 ms | 1500 ms | ~50× |
| 4K render | ~310 ms | 8000 ms | ~25× |
| colormap switch | ~55 ms | 3000 ms | ~50× |

Verified:
```
CI=1 VIZNOIR_RUN_GPU_TESTS=1 ...EGL...  -> 4 passed in 1.15s
CI=1 (hosted, no GPU)                   -> 4 skipped
```

The perf tests are `*_vtk.py`, so they auto-skip on GitHub-hosted CI and run only
where a GPU exists — same gating as the other rendering tests.

## Result

v0.11.0 "Trust & Guard" quality gates are enforced in CI: ≥90% coverage and
bounded render latency, both on the self-hosted GPU runner. ruff + mypy clean.
