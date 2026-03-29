"""viznoir vs PyVista vs Raw VTK — end-to-end render benchmark.

Fair comparison:
  - Input:    identical wavelet 21x21x21 vtkImageData
  - Output:   PNG bytes in memory (all three produce bytes)
  - Resource: each library's default usage pattern
  - Pipeline: colormap + scalar bar + camera + render + PNG encode

Usage:
    VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow python3 benchmarks/bench_comparison.py
    VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow python3 benchmarks/bench_comparison.py -n 20
"""

from __future__ import annotations

import io
import os
import statistics
import subprocess
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

WIDTH, HEIGHT = 1280, 720


def _fmt(ms: float) -> str:
    return f"{ms:7.1f} ms"


def _stats(times: list[float]) -> dict[str, float]:
    s = sorted(times)
    n = len(s)
    return {
        "min": s[0],
        "p50": s[n // 2],
        "mean": statistics.mean(s),
        "max": s[-1],
        "stdev": statistics.stdev(s) if n > 1 else 0.0,
    }


def _make_wavelet():
    import vtk
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    return src.GetOutput()


# ── viznoir ─────────────────────────────────────────────────────────
# Uses VTKRenderer.render(data) → PNG bytes
# Singleton render window reuse is viznoir's design choice.

def bench_viznoir(data, n: int) -> list[float]:
    from viznoir.engine.renderer import RenderConfig, VTKRenderer

    cfg = RenderConfig(width=WIDTH, height=HEIGHT, array_name="RTData")
    renderer = VTKRenderer(cfg)
    renderer.render(data)  # warmup

    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        png = renderer.render(data)
        elapsed = time.perf_counter() - t0
        assert png[:4] == b"\x89PNG"
        times.append(elapsed * 1000)
    return times


# ── PyVista ─────────────────────────────────────────────────────────
# Uses Plotter → add_mesh → screenshot → PIL → PNG bytes
# New Plotter per call is PyVista's standard usage.

def bench_pyvista(data, n: int) -> list[float]:
    import pyvista as pv
    pv.OFF_SCREEN = True

    mesh = pv.wrap(data)

    # warmup
    pl = pv.Plotter(off_screen=True, window_size=(WIDTH, HEIGHT))
    pl.add_mesh(mesh, scalars="RTData", cmap="coolwarm", show_scalar_bar=True)
    img = pl.screenshot()
    pl.close()

    from PIL import Image

    times = []
    for _ in range(n):
        t0 = time.perf_counter()

        pl = pv.Plotter(off_screen=True, window_size=(WIDTH, HEIGHT))
        pl.add_mesh(mesh, scalars="RTData", cmap="coolwarm", show_scalar_bar=True)
        img_array = pl.screenshot()
        pl.close()

        # Convert numpy array → PNG bytes (same output as viznoir/raw VTK)
        buf = io.BytesIO()
        Image.fromarray(img_array).save(buf, format="PNG")
        png = buf.getvalue()

        elapsed = time.perf_counter() - t0
        assert png[:4] == b"\x89PNG"
        times.append(elapsed * 1000)
    return times


# ── Raw VTK ─────────────────────────────────────────────────────────
# Direct VTK API. New window per call (no singleton).
# Same pipeline: mapper + LUT + scalar bar + actor + render + PNG.

def bench_raw_vtk(data, n: int) -> list[float]:
    import vtk
    from vtkmodules.util.numpy_support import vtk_to_numpy

    # warmup
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(True)
    rw.SetSize(WIDTH, HEIGHT)
    ren = vtk.vtkRenderer()
    rw.AddRenderer(ren)
    m = vtk.vtkDataSetMapper()
    m.SetInputData(data)
    a = vtk.vtkActor()
    a.SetMapper(m)
    ren.AddActor(a)
    rw.Render()
    rw.Finalize()

    times = []
    for _ in range(n):
        t0 = time.perf_counter()

        # Mapper + LUT
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(data)
        mapper.SetScalarVisibility(True)
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray("RTData")
        sr = data.GetPointData().GetArray("RTData").GetRange(0)
        mapper.SetScalarRange(*sr)

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetHueRange(0.667, 0.0)
        lut.Build()
        mapper.SetLookupTable(lut)

        # Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Scalar bar
        bar = vtk.vtkScalarBarActor()
        bar.SetLookupTable(lut)
        bar.SetTitle("RTData")
        bar.SetNumberOfLabels(5)

        # Renderer + Window
        ren = vtk.vtkRenderer()
        ren.AddActor(actor)
        ren.AddViewProp(bar)
        ren.SetBackground(0.2, 0.2, 0.2)
        ren.ResetCamera()

        rw = vtk.vtkRenderWindow()
        rw.SetOffScreenRendering(True)
        rw.SetSize(WIDTH, HEIGHT)
        rw.AddRenderer(ren)
        rw.Render()

        # Capture → PNG bytes
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(rw)
        w2i.SetInputBufferTypeToRGB()
        w2i.ReadFrontBufferOff()
        w2i.Update()

        writer = vtk.vtkPNGWriter()
        writer.SetInputConnection(w2i.GetOutputPort())
        writer.WriteToMemoryOn()
        writer.Write()
        png = vtk_to_numpy(writer.GetResult()).tobytes()

        rw.Finalize()

        elapsed = time.perf_counter() - t0
        assert png[:4] == b"\x89PNG"
        times.append(elapsed * 1000)
    return times


def main() -> None:
    import argparse
    import platform

    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", "-n", type=int, default=15)
    args = parser.parse_args()
    n = args.iterations

    import vtk
    gpu = "unknown"
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            gpu = r.stdout.strip()
    except Exception:
        pass

    sep = "=" * 72

    print()
    print("viznoir End-to-End Render Benchmark")
    print(sep)
    print(f"Input:      vtkRTAnalyticSource (wavelet 21^3)")
    print(f"Output:     PNG bytes in memory")
    print(f"Pipeline:   colormap + scalar bar + camera + render + PNG encode")
    print(f"Resolution: {WIDTH} x {HEIGHT}")
    print(f"Iterations: {n} (after warmup)")
    print(f"Backend:    {os.environ.get('VTK_DEFAULT_OPENGL_WINDOW', 'default')}")
    print(f"GPU:        {gpu}")
    print(f"VTK:        {vtk.vtkVersion.GetVTKVersion()}")
    print(f"Python:     {platform.python_version()}")
    try:
        import pyvista as pv
        print(f"PyVista:    {pv.__version__}")
    except ImportError:
        print("PyVista:    not installed")
    print(sep)

    data = _make_wavelet()

    results: dict[str, dict[str, float]] = {}
    raw_times: dict[str, list[float]] = {}

    for name, fn in [
        ("viznoir", bench_viznoir),
        ("Raw VTK", bench_raw_vtk),
        ("PyVista", bench_pyvista),
    ]:
        print(f"\n[{name}] {n} iterations...", flush=True)
        try:
            t = fn(data, n)
            results[name] = _stats(t)
            raw_times[name] = t
            print(f"  median = {_fmt(results[name]['p50'])}")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Results table
    print(f"\n{sep}")
    print(f"{'Tool':<12} {'Min':>9} {'Median':>9} {'Mean':>9} {'Max':>9} {'StDev':>9}")
    print("-" * 60)

    for name, st in results.items():
        print(f"{name:<12} {_fmt(st['min']):>9} {_fmt(st['p50']):>9} "
              f"{_fmt(st['mean']):>9} {_fmt(st['max']):>9} {_fmt(st['stdev']):>9}")

    print(sep)

    # Raw data
    print("\nRaw timings (ms):")
    for name, t in raw_times.items():
        print(f"  {name}: {', '.join(f'{v:.1f}' for v in t)}")
    print()


if __name__ == "__main__":
    main()
