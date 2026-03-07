#!/usr/bin/env python3
"""viznoir MCP E2E Validation — Tests all 13 tools with real VTK data.

Usage:
    python docs/validation/test_e2e.py

Requires: pip install -e ".[dev]" (viznoir + pyvista + vtk)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

# Insert src for local dev
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

os.environ["VTK_DEFAULT_OPENGL_WINDOW"] = "vtkEGLRenderWindow"
os.environ.setdefault("VIZNOIR_RENDER_BACKEND", "gpu")

TEST_DIR = Path("/tmp/viznoir_test")
OUTPUT_DIR = TEST_DIR / "output"


@dataclass
class TestResult:
    tool: str
    dataset: str
    status: str  # PASS, FAIL, SKIP
    elapsed: float = 0.0
    output_size: int = 0
    notes: str = ""
    output_file: str = ""


results: list[TestResult] = []


def _check_image_quality(data: bytes | None, tool_name: str) -> str:
    """Check image for common quality issues."""
    if data is None:
        return "NO IMAGE DATA"
    size = len(data)
    if size < 1000:
        return f"SUSPICIOUSLY SMALL ({size}B)"
    if size < 8192:
        return f"POSSIBLY EMPTY/BLANK ({size}B)"
    return ""


# ---------------------------------------------------------------------------
# Test Data Generation
# ---------------------------------------------------------------------------

def generate_test_data():
    """Generate VTK test datasets using pyvista."""
    import numpy as np
    import pyvista as pv

    TEST_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Wavelet (structured grid with RTData scalar)
    wavelet = pv.Wavelet()
    wavelet.save(str(TEST_DIR / "wavelet.vtk"))
    print(f"  wavelet.vtk: {wavelet.n_points} pts, fields={list(wavelet.point_data.keys())}")

    # 2. Sphere with scalar field (unstructured)
    sphere = pv.Sphere(theta_resolution=50, phi_resolution=50)
    sphere["elevation"] = sphere.points[:, 2]
    sphere.save(str(TEST_DIR / "sphere.vtk"))
    print(f"  sphere.vtk: {sphere.n_points} pts, fields={list(sphere.point_data.keys())}")

    # 3. Flow field with vectors (for streamlines)
    xrng = np.linspace(-5, 5, 30)
    yrng = np.linspace(-5, 5, 30)
    zrng = np.linspace(-2, 2, 15)
    x, y, z = np.meshgrid(xrng, yrng, zrng, indexing="ij")
    grid = pv.StructuredGrid(x, y, z)
    # Swirling flow
    vx = -y.ravel()
    vy = x.ravel()
    vz = np.sin(z.ravel())
    vectors = np.column_stack([vx, vy, vz])
    grid["velocity"] = vectors
    grid["speed"] = np.linalg.norm(vectors, axis=1)
    grid.save(str(TEST_DIR / "flow.vtk"))
    print(f"  flow.vtk: {grid.n_points} pts, fields={list(grid.point_data.keys())}")

    # 4. Uniform grid (for slice/clip testing)
    uniform = pv.ImageData(dimensions=(50, 50, 50), spacing=(0.1, 0.1, 0.1), origin=(0, 0, 0))
    uniform["scalar"] = np.random.default_rng(42).random(uniform.n_points)
    uniform.save(str(TEST_DIR / "uniform.vti"))
    print(f"  uniform.vti: {uniform.n_points} pts")

    return {
        "wavelet": str(TEST_DIR / "wavelet.vtk"),
        "sphere": str(TEST_DIR / "sphere.vtk"),
        "flow": str(TEST_DIR / "flow.vtk"),
        "uniform": str(TEST_DIR / "uniform.vti"),
    }


# ---------------------------------------------------------------------------
# Individual Tool Tests
# ---------------------------------------------------------------------------

async def _run_test(tool: str, dataset: str, coro, output_file: str = ""):
    """Execute a single tool test and record the result."""
    t0 = time.time()
    try:
        result = await coro
        elapsed = time.time() - t0

        # Determine output size and quality
        img_bytes = None
        output_size = 0
        notes = ""

        if hasattr(result, "image_bytes") and result.image_bytes:
            img_bytes = result.image_bytes
            output_size = len(img_bytes)
            notes = _check_image_quality(img_bytes, tool)
            if output_file and img_bytes:
                out_path = OUTPUT_DIR / output_file
                out_path.write_bytes(img_bytes)
        elif hasattr(result, "ok"):
            output_size = len(result.image_bytes) if result.image_bytes else 0
            img_bytes = result.image_bytes
            notes = _check_image_quality(img_bytes, tool)
            if output_file and img_bytes:
                out_path = OUTPUT_DIR / output_file
                out_path.write_bytes(img_bytes)
        elif isinstance(result, dict):
            output_size = len(json.dumps(result))
            if "error" in result:
                notes = f"ERROR: {result['error']}"
        else:
            output_size = len(str(result))

        status = "FAIL" if notes.startswith(("NO IMAGE", "ERROR", "SUSPICIOUSLY")) else "PASS"
        results.append(TestResult(
            tool=tool, dataset=dataset, status=status,
            elapsed=elapsed, output_size=output_size,
            notes=notes, output_file=output_file,
        ))
        return result
    except Exception as e:
        elapsed = time.time() - t0
        tb = traceback.format_exc()
        results.append(TestResult(
            tool=tool, dataset=dataset, status="FAIL",
            elapsed=elapsed, notes=f"EXCEPTION: {e}\n{tb}",
        ))
        return None


async def run_all_tests(data: dict[str, str]):
    """Run all 13 tool tests."""
    from viznoir.config import PVConfig
    from viznoir.core.runner import VTKRunner

    config = PVConfig()
    runner = VTKRunner(config=config)

    wavelet = data["wavelet"]
    sphere = data["sphere"]
    flow = data["flow"]
    uniform = data["uniform"]

    # --- 1. inspect_data ---
    print("\n[1/13] inspect_data...")
    from viznoir.tools.inspect import inspect_data_impl
    meta = await _run_test(
        "inspect_data", "wavelet",
        inspect_data_impl(wavelet, runner),
    )
    if meta and isinstance(meta, dict):
        print(f"  bounds: {meta.get('bounds', 'N/A')}")
        arrays = meta.get("point_arrays") or meta.get("arrays", [])
        print(f"  arrays: {len(arrays)} found")

    # --- 2. render ---
    print("\n[2/13] render...")
    from viznoir.tools.render import render_impl
    await _run_test(
        "render", "wavelet",
        render_impl(wavelet, "RTData", runner, width=800, height=600),
        output_file="render_wavelet.png",
    )

    # render with colormap
    await _run_test(
        "render (colormap)", "sphere",
        render_impl(sphere, "elevation", runner, colormap="Viridis", width=800, height=600),
        output_file="render_sphere_viridis.png",
    )

    # --- 3. slice ---
    print("\n[3/13] slice...")
    from viznoir.tools.filters import slice_impl
    # Auto-origin (no origin specified — should use dataset center)
    await _run_test(
        "slice (auto-origin)", "wavelet",
        slice_impl(wavelet, "RTData", runner, normal=[0, 0, 1], width=800, height=600),
        output_file="slice_wavelet_auto.png",
    )
    # Explicit origin
    await _run_test(
        "slice (explicit)", "uniform",
        slice_impl(uniform, "scalar", runner, origin=[2.5, 2.5, 2.5], normal=[1, 0, 0], width=800, height=600),
        output_file="slice_uniform_explicit.png",
    )

    # --- 4. contour ---
    print("\n[4/13] contour...")
    from viznoir.tools.filters import contour_impl

    # First inspect to get the data range for correct isovalues
    meta_w = await inspect_data_impl(wavelet, runner)
    rtdata_range = None
    for arr in (meta_w.get("point_arrays") or meta_w.get("arrays", [])):
        name = arr.get("name", "") if isinstance(arr, dict) else ""
        if name == "RTData":
            rtdata_range = arr.get("range", [])
            break
    print(f"  RTData range: {rtdata_range}")

    if rtdata_range and len(rtdata_range) == 2:
        mid = (rtdata_range[0] + rtdata_range[1]) / 2
        isovalues = [mid]
    else:
        isovalues = [100.0]  # fallback

    await _run_test(
        "contour (valid iso)", "wavelet",
        contour_impl(wavelet, "RTData", isovalues, runner, width=800, height=600),
        output_file="contour_wavelet_valid.png",
    )

    # Contour with out-of-range isovalue (regression test for empty output bug)
    # Expected: EmptyOutputError with helpful range info — this is CORRECT behavior
    try:
        oor_result = await contour_impl(wavelet, "RTData", [99999.0], runner, width=800, height=600)
        # If we get here without error, that's unexpected
        results.append(TestResult(
            tool="contour (out-of-range)", dataset="wavelet", status="FAIL",
            notes="Expected EmptyOutputError but got success",
        ))
    except Exception as e:
        if "EmptyOutputError" in str(e) or "empty output" in str(e).lower():
            results.append(TestResult(
                tool="contour (out-of-range)", dataset="wavelet", status="PASS",
                notes=f"Correctly rejected: {str(e)[:100]}",
            ))
        else:
            results.append(TestResult(
                tool="contour (out-of-range)", dataset="wavelet", status="FAIL",
                notes=f"Unexpected error: {e}",
            ))

    # --- 5. clip ---
    print("\n[5/13] clip...")
    from viznoir.tools.filters import clip_impl
    await _run_test(
        "clip (auto-origin)", "wavelet",
        clip_impl(wavelet, "RTData", runner, normal=[1, 0, 0], width=800, height=600),
        output_file="clip_wavelet_auto.png",
    )
    await _run_test(
        "clip (invert)", "wavelet",
        clip_impl(wavelet, "RTData", runner, normal=[1, 0, 0], invert=True, width=800, height=600),
        output_file="clip_wavelet_invert.png",
    )

    # --- 6. streamlines ---
    print("\n[6/13] streamlines...")
    from viznoir.tools.filters import streamlines_impl
    # Auto seed points (no seed specified — should use dataset bounds)
    await _run_test(
        "streamlines (auto-seed)", "flow",
        streamlines_impl(flow, "velocity", runner, max_length=20.0, width=800, height=600),
        output_file="streamlines_flow_auto.png",
    )
    # Explicit seed
    await _run_test(
        "streamlines (explicit)", "flow",
        streamlines_impl(
            flow, "velocity", runner,
            seed_point1=[-4, -4, 0], seed_point2=[4, 4, 0],
            seed_resolution=15, max_length=20.0, width=800, height=600,
        ),
        output_file="streamlines_flow_explicit.png",
    )

    # --- 7. plot_over_line ---
    print("\n[7/13] plot_over_line...")
    from viznoir.tools.extract import plot_over_line_impl
    pol_result = await _run_test(
        "plot_over_line", "wavelet",
        plot_over_line_impl(
            wavelet, "RTData", [-10, 0, 0], [10, 0, 0], runner, resolution=50,
        ),
    )
    if pol_result and isinstance(pol_result, dict):
        n_points = len(pol_result.get("coordinates", pol_result.get("points", [])))
        print(f"  sampled {n_points} points")

    # --- 8. extract_stats ---
    print("\n[8/13] extract_stats...")
    from viznoir.tools.extract import extract_stats_impl
    stats = await _run_test(
        "extract_stats", "wavelet",
        extract_stats_impl(wavelet, ["RTData"], runner),
    )
    if stats and isinstance(stats, dict):
        print(f"  stats keys: {list(stats.keys())}")

    # --- 9. integrate_surface ---
    print("\n[9/13] integrate_surface...")
    from viznoir.tools.extract import integrate_surface_impl
    integ = await _run_test(
        "integrate_surface", "sphere",
        integrate_surface_impl(sphere, "elevation", runner),
    )
    if integ and isinstance(integ, dict):
        print(f"  integration result keys: {list(integ.keys())}")

    # --- 10. animate (orbit mode — works with single timestep) ---
    print("\n[10/13] animate (orbit)...")
    from viznoir.tools.animate import animate_impl
    anim = await _run_test(
        "animate (orbit/gif)", "wavelet",
        animate_impl(
            wavelet, "RTData", runner,
            mode="orbit", orbit_duration=2.0, fps=8,
            width=400, height=300, output_format="gif",
        ),
        output_file="animate_orbit.gif",
    )
    if anim and hasattr(anim, "json_data") and anim.json_data:
        print(f"  animation result: {list(anim.json_data.keys()) if isinstance(anim.json_data, dict) else type(anim.json_data)}")

    # --- 11. execute_pipeline (DSL) ---
    print("\n[11/13] execute_pipeline...")
    from viznoir.tools.pipeline import execute_pipeline_impl
    pipeline_json = {
        "source": {"file": wavelet},
        "pipeline": [
            {"filter": "Slice", "params": {"normal": [0, 0, 1]}},
        ],
        "output": {
            "type": "image",
            "render": {
                "field": "RTData",
                "colormap": "Viridis",
                "resolution": [800, 600],
            },
        },
    }
    await _run_test(
        "execute_pipeline", "wavelet",
        execute_pipeline_impl(pipeline_json, runner),
        output_file="pipeline_slice.png",
    )

    # Pipeline with Threshold filter
    pipeline_threshold = {
        "source": {"file": wavelet},
        "pipeline": [
            {"filter": "Threshold", "params": {"field": "RTData", "lower": 100, "upper": 300}},
        ],
        "output": {
            "type": "image",
            "render": {
                "field": "RTData",
                "colormap": "Cool to Warm",
                "resolution": [800, 600],
            },
        },
    }
    await _run_test(
        "execute_pipeline (threshold)", "wavelet",
        execute_pipeline_impl(pipeline_threshold, runner),
        output_file="pipeline_threshold.png",
    )

    # --- 12. pv_isosurface (requires Docker — skip if not available) ---
    print("\n[12/13] pv_isosurface...")
    results.append(TestResult(
        tool="pv_isosurface", dataset="N/A", status="SKIP",
        notes="Requires DualSPHysics Docker image + bi4 data — skipped in E2E validation",
    ))

    # --- 13. split_animate (requires composite deps) ---
    print("\n[13/13] split_animate...")
    try:
        import PIL  # noqa: F401
        import matplotlib  # noqa: F401
        has_composite = True
    except ImportError:
        has_composite = False

    if has_composite:
        from viznoir.tools.split_animate import split_animate_impl
        panes = [
            {
                "type": "render", "row": 0, "col": 0,
                "render_pane": {"render": {"field": "RTData"}, "title": "RTData"},
            },
            {
                "type": "render", "row": 0, "col": 1,
                "render_pane": {"render": {"field": "RTData", "colormap": "Viridis"}, "title": "Viridis"},
            },
        ]
        # gif=False returns json_data (frame sequence), not image_bytes
        sa_result = await _run_test(
            "split_animate (frames)", "wavelet",
            split_animate_impl(
                wavelet, panes, runner,
                layout={"rows": 1, "cols": 2, "gap": 4},
                fps=8, resolution=[800, 400], gif=False,
            ),
        )
        # Fix status: json_data with frame_count > 0 is success
        if sa_result and hasattr(sa_result, "json_data") and sa_result.json_data:
            jd = sa_result.json_data
            if isinstance(jd, dict) and jd.get("frame_count", 0) > 0:
                # Override last result status
                results[-1].status = "PASS"
                results[-1].notes = f"frames={jd['frame_count']}, composed={jd.get('composed_frame_count', 0)}"
                results[-1].output_size = jd.get("frame_count", 0)
    else:
        results.append(TestResult(
            tool="split_animate", dataset="N/A", status="SKIP",
            notes="Requires Pillow + matplotlib (pip install -e '.[composite]')",
        ))


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_report(data: dict[str, str]) -> str:
    """Generate markdown report from test results."""
    import vtk

    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    total = len(results)
    success_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0

    render_times = [r.elapsed for r in results if r.status == "PASS" and "render" in r.tool.lower() or "slice" in r.tool.lower() or "contour" in r.tool.lower() or "clip" in r.tool.lower() or "stream" in r.tool.lower()]
    avg_render = sum(render_times) / len(render_times) if render_times else 0

    report = f"""# viznoir E2E Validation Report

**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**Validator**: automated (docs/validation/test_e2e.py)

## Test Environment

| Component | Version |
|-----------|---------|
| Python | {sys.version.split()[0]} |
| VTK | {vtk.vtkVersion.GetVTKVersion()} |
| PyVista | {__import__('pyvista').__version__} |
| OS | {os.uname().sysname} {os.uname().release} |
| GPU | RTX 4090 24GB (EGL headless) |
| Render Backend | {os.environ.get('VIZNOIR_RENDER_BACKEND', 'gpu')} |

## Test Datasets

| Dataset | Path | Description |
|---------|------|-------------|
| wavelet | wavelet.vtk | Structured grid, RTData scalar field |
| sphere | sphere.vtk | Polygonal mesh, elevation scalar |
| flow | flow.vtk | Structured grid, velocity vectors + speed scalar |
| uniform | uniform.vti | Uniform image data, random scalar |

## Results Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Skipped | {skipped} |
| **Success Rate** | **{success_rate:.1f}%** |
| Avg Render Time | {avg_render:.2f}s |

## Detailed Results

| # | Tool | Dataset | Time(s) | Output Size | Status | Notes |
|---|------|---------|---------|-------------|--------|-------|
"""
    for i, r in enumerate(results, 1):
        size_str = f"{r.output_size:,}B" if r.output_size else "-"
        time_str = f"{r.elapsed:.2f}" if r.elapsed > 0 else "-"
        notes = r.notes[:80] if r.notes else ""
        report += f"| {i} | {r.tool} | {r.dataset} | {time_str} | {size_str} | **{r.status}** | {notes} |\n"

    # Issues section
    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        report += "\n## Issues Found\n\n"
        for r in failures:
            report += f"### {r.tool} ({r.dataset})\n\n"
            report += f"```\n{r.notes}\n```\n\n"
    else:
        report += "\n## Issues Found\n\nNo issues found.\n"

    # Output files
    output_files = [r for r in results if r.output_file]
    if output_files:
        report += "\n## Output Files\n\n"
        report += f"All output files saved to `{OUTPUT_DIR}/`:\n\n"
        for r in output_files:
            status_mark = "x" if r.status == "PASS" else " "
            report += f"- [{status_mark}] `{r.output_file}` ({r.output_size:,}B)\n"

    report += f"""
## Performance Summary

| Category | Count | Avg Time(s) |
|----------|-------|-------------|
| Rendering (render/slice/contour/clip/streamlines) | {len(render_times)} | {avg_render:.2f} |
| Data extraction (stats/plot_over_line/integrate) | {sum(1 for r in results if r.tool in ('extract_stats', 'plot_over_line', 'integrate_surface'))} | {sum(r.elapsed for r in results if r.tool in ('extract_stats', 'plot_over_line', 'integrate_surface')) / max(1, sum(1 for r in results if r.tool in ('extract_stats', 'plot_over_line', 'integrate_surface'))):.2f} |
| Animation | {sum(1 for r in results if 'animate' in r.tool)} | {sum(r.elapsed for r in results if 'animate' in r.tool) / max(1, sum(1 for r in results if 'animate' in r.tool)):.2f} |

## Reproduction

```bash
cd /home/imgyu/workspace/02_active/dev/kimtech
pip install -e ".[dev]"
python docs/validation/test_e2e.py
```
"""
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("viznoir MCP E2E Validation")
    print("=" * 60)

    print("\n>> Generating test data...")
    data = generate_test_data()

    print("\n>> Running 13 tool tests...")
    t_start = time.time()
    asyncio.run(run_all_tests(data))
    total_time = time.time() - t_start

    print(f"\n>> All tests completed in {total_time:.1f}s")

    # Summary
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    print(f"\n>> Results: {passed} PASS, {failed} FAIL, {skipped} SKIP")

    # Generate report
    report = generate_report(data)
    report_path = Path(__file__).parent / "e2e-report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n>> Report saved to {report_path}")

    # Also dump JSON for programmatic use
    json_path = Path(__file__).parent / "e2e-results.json"
    json_data = [
        {
            "tool": r.tool, "dataset": r.dataset, "status": r.status,
            "elapsed": round(r.elapsed, 3), "output_size": r.output_size,
            "notes": r.notes, "output_file": r.output_file,
        }
        for r in results
    ]
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
    print(f">> JSON results saved to {json_path}")

    # Return exit code
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
