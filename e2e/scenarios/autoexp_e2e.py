"""E2E evidence for #61 — autoexp picks the best colormap via real GPU renders.

Renders a VTK wavelet through viznoir's real renderer with each physics-
appropriate colormap candidate (engine.presets), measures each with the quality
metric (engine.quality), and lets the autoexp ratchet keep the best. Proves the
modify->render->measure->keep/revert loop works end-to-end on actual renders.

Run:  .venv/bin/python e2e/scenarios/autoexp_e2e.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import vtk

from viznoir.core.autoexp import autoexp
from viznoir.engine.presets import candidates_for
from viznoir.engine.quality import load_png
from viznoir.engine.renderer import RenderConfig, render_to_png

_TMP = Path(tempfile.mkdtemp())


def main() -> int:
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    data = src.GetOutput()
    rng = data.GetPointData().GetArray("RTData").GetRange()
    fmin, fmax = float(rng[0]), float(rng[1])

    def render_fn(params: dict):
        cfg = RenderConfig(colormap=params["colormap"], array_name="RTData")
        png = _TMP / f"{params['colormap'].replace(' ', '_')}.png"
        png.write_bytes(render_to_png(data, cfg))
        return load_png(str(png))

    # RTData is one-sided positive -> sequential colormap candidates.
    candidates = [c.as_params() for c in candidates_for(fmin, fmax)]
    print(f"field RTData range [{fmin:.1f}, {fmax:.1f}] -> candidates: {[c['colormap'] for c in candidates]}")

    result = autoexp({"colormap": "grayscale"}, candidates, render_fn)

    print(f"baseline (grayscale) score: {result.baseline_score:.4f}")
    for t in result.trials:
        print(f"  {'KEEP' if t.kept else 'skip'} {t.label:20s} score={t.score:.4f}")
    print(f"best: {result.best_params['colormap']} score={result.best_score:.4f} improved={result.improved}")

    checks = {
        "ran baseline + all candidates": len(result.trials) == 1 + len(candidates),
        "best_score >= baseline": result.best_score >= result.baseline_score,
        "best is a real colormap": isinstance(result.best_params.get("colormap"), str),
        "every trial measured a score": all(0.0 <= t.score <= 1.0 for t in result.trials),
    }
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
