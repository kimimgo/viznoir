# E2E Evidence — #58 guard/ module (physics-aware render validation)

- **Date**: 2026-06-16
- **Scenario**: `e2e/scenarios/guard_module_e2e.py`
- **Environment**: oliveeelab host (pure logic + VTK field extraction, no GPU)

## What was driven (grounded in real field stats)

1. Built a signed pressure-like field from a VTK wavelet (`RTData - mean`) and
   read its **true** range: `min=-115.80, max=123.67` (crosses zero).
2. Validated a **bad** render config (sequential `viridis` on the signed field +
   empty isosurface) and a **good** one (`coolwarm`, zero-centered range,
   non-empty isosurface).

## Results

```
BAD  verdict=FAIL
   - [warn] pressure_diverging_colormap: signed pressure but colormap 'viridis' is not diverging
   - [fail] empty_isosurface: isosurface produced no geometry — isovalue outside data range
GOOD verdict=PASS
   - [pass] pressure_diverging_colormap
   - [pass] empty_isosurface
```

## Checks (4/4 PASS)

```
[PASS] bad config FAILs (empty isosurface)
[PASS] bad flags pressure colormap (sequential on signed field)
[PASS] bad flags empty isosurface (with suggested data range)
[PASS] good config PASSes
```

The guard turns hallucinated visualization choices into actionable pass/warn/fail
verdicts — the foundation `validate_render` (#59) will expose as an MCP tool.

## Unit coverage

`tests/test_guard/test_guard.py` — 24 tests; `guard/` at **96%** line coverage
(rules 95%, validator 100%). Suite: 1733 tests (≥1650 guard). ruff + mypy clean.
