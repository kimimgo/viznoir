"""E2E evidence for #58 — physics guard catches a hallucinated render config.

Grounds the guard in REAL field statistics: builds a signed (pressure-like)
field from a VTK wavelet, reads its true min/max, then validates a *bad* render
config (sequential colormap on a signed field + an empty isosurface) vs a *good*
one (diverging, zero-centered, non-empty). The guard must FAIL the bad config
and PASS the good one.

Run:  .venv/bin/python e2e/scenarios/guard_module_e2e.py
"""

from __future__ import annotations

import sys

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

from viznoir.guard import GuardContext, Status, validate


def main() -> int:
    # 1) Real dataset -> a signed "pressure-like" field (RTData minus its mean).
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    data = src.GetOutput()
    rt = vtk_to_numpy(data.GetPointData().GetArray("RTData")).astype(np.float64)
    pressure = rt - rt.mean()  # now crosses zero
    pmin, pmax = float(pressure.min()), float(pressure.max())
    print(f"real signed field: min={pmin:.2f} max={pmax:.2f} (crosses zero={pmin < 0 < pmax})")

    # 2) BAD config — what a careless agent might pick.
    bad = GuardContext(
        field_name="pressure",
        field_min=pmin,
        field_max=pmax,
        colormap="viridis",  # sequential on signed field -> hides zero crossing
        scalar_range=(pmin, pmax),
        filter_type="contour",
        isosurface_cell_count=0,  # isovalue outside range -> empty
    )
    bad_report = validate(bad)

    # 3) GOOD config — physically appropriate choices.
    sym = max(abs(pmin), abs(pmax))
    good = GuardContext(
        field_name="pressure",
        field_min=pmin,
        field_max=pmax,
        colormap="coolwarm",
        scalar_range=(-sym, sym),
        filter_type="contour",
        isosurface_cell_count=4096,
    )
    good_report = validate(good)

    print(f"BAD  verdict={bad_report.verdict.value}")
    for r in bad_report.results:
        print(f"   - [{r.status.value}] {r.rule}: {r.message}")
    print(f"GOOD verdict={good_report.verdict.value}")
    for r in good_report.results:
        print(f"   - [{r.status.value}] {r.rule}")

    checks = {
        "bad config FAILs (empty isosurface)": bad_report.verdict is Status.FAIL,
        "bad flags pressure colormap": any(
            r.rule == "pressure_diverging_colormap" and r.status is Status.WARN
            for r in bad_report.results
        ),
        "bad flags empty isosurface": any(
            r.rule == "empty_isosurface" and r.status is Status.FAIL for r in bad_report.results
        ),
        "good config PASSes": good_report.verdict is Status.PASS,
    }
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
