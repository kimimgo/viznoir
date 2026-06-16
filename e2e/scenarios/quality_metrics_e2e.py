"""E2E evidence for #60 — quality metrics on a REAL viznoir render (not synthetic).

Renders a VTK wavelet (vtkRTAnalyticSource) through viznoir's render_to_png on
the GPU, then runs engine.quality.measure_quality on the resulting PNG and
checks the metrics are physically sensible (a real render is far richer than a
blank frame). Writes the PNG next to this report as captured evidence.

Run:  .venv/bin/python e2e/scenarios/quality_metrics_e2e.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import vtk

from viznoir.engine.quality import load_png, measure_quality

OUT = Path(__file__).resolve().parents[1] / "reports"
OUT.mkdir(parents=True, exist_ok=True)
PNG = OUT / "quality-metrics-render.png"


def main() -> int:
    # 1) Real dataset: VTK's analytic wavelet (ParaView "Wavelet" equivalent).
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    data = src.GetOutput()

    # 2) Render through viznoir's actual pipeline -> PNG bytes -> file.
    from viznoir.engine.renderer import render_to_png

    png_bytes = render_to_png(data)
    PNG.write_bytes(png_bytes)

    # 3) Measure quality of the real render.
    img = load_png(str(PNG))
    rendered = measure_quality(img)

    # 4) Baseline: a blank frame must score ~0 (the metric discriminates).
    blank = measure_quality(np.full_like(img, 255), background_color=(255, 255, 255))

    print(f"render PNG:        {PNG}  ({len(png_bytes)} bytes, shape={img.shape})")
    print(f"rendered metrics:  {rendered.to_dict()}")
    print(f"blank metrics:     {blank.to_dict()}")

    # 5) Assertions — a real render is informative; a blank frame is not.
    checks = {
        "score in [0,1]": 0.0 <= rendered.score <= 1.0,
        "coverage > 0.05 (object visible)": rendered.field_coverage > 0.05,
        "contrast > 0 (not flat)": rendered.contrast > 0.0,
        "edge_entropy > 0 (has detail)": rendered.edge_entropy > 0.0,
        "rendered.score > blank.score": rendered.score > blank.score,
        "blank.score ~ 0": blank.score < 0.02,
    }
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
