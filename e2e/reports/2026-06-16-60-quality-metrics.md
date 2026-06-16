# E2E Evidence — #60 engine/quality.py (render quality metrics)

- **Date**: 2026-06-16
- **Scenario**: `e2e/scenarios/quality_metrics_e2e.py`
- **Environment**: oliveeelab host, RTX 4090, VTK offscreen render
- **Artifact**: `e2e/reports/quality-metrics-render.png` (228 KB, 1920×1080)

## What was driven (real pipeline, not synthetic)

1. Built a VTK wavelet dataset (`vtkRTAnalyticSource`, ParaView "Wavelet" equivalent).
2. Rendered it through viznoir's **actual** `engine.renderer.render_to_png` → PNG bytes.
3. Loaded the PNG with `engine.quality.load_png` and ran `measure_quality`.
4. Compared against a blank (all-white) frame to prove the metric discriminates.

## Results

| frame | contrast | edge_entropy | field_coverage | score |
|-------|---------:|-------------:|---------------:|------:|
| **real render** | 0.2125 | 0.0963 | 0.2535 | **0.2272** |
| blank (255,255,255) | 0.0000 | 0.0000 | 0.0000 | **0.0000** |

The rendered wavelet (RTData scalar field with colorbar over a dark background)
yields ~25% object coverage and non-zero contrast/edge detail; a blank frame
scores 0. This is exactly the signal `core/autoexp.py` (#61) needs to keep vs.
revert a render change.

## Checks (6/6 PASS)

```
[PASS] score in [0,1]
[PASS] coverage > 0.05 (object visible)
[PASS] contrast > 0 (not flat)
[PASS] edge_entropy > 0 (has detail)
[PASS] rendered.score > blank.score
[PASS] blank.score ~ 0
```

## Unit coverage

`tests/test_engine/test_quality.py` — 20 tests, `quality.py` at 94% line
coverage. Total suite: 1709 tests (≥1650 guard). ruff + mypy clean.
