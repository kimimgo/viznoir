"""In-process vs Subprocess execution benchmark.

Compares the two execution paths in viznoir:
- InProcessExecutor: compile() + exec() in current process
- Subprocess: asyncio.create_subprocess_exec(python, script.py)

Both execute the identical VTK script (wavelet → render → PNG).
Measures N iterations each, reports min/mean/median/p95/max.

Usage:
    python3 benchmarks/bench_execution.py
    python3 benchmarks/bench_execution.py --iterations 20
"""

from __future__ import annotations

import asyncio
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# The VTK script both execution paths will run (identical code).
_RENDER_SCRIPT = """\
import os
os.environ.setdefault("VTK_DEFAULT_OPENGL_WINDOW", "vtkEGLRenderWindow")
import vtk
from pathlib import Path

src = vtk.vtkRTAnalyticSource()
src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
src.Update()

mapper = vtk.vtkDataSetMapper()
mapper.SetInputData(src.GetOutput())
mapper.SetScalarRange(src.GetOutput().GetScalarRange())

actor = vtk.vtkActor()
actor.SetMapper(mapper)

renderer = vtk.vtkRenderer()
renderer.AddActor(actor)
renderer.SetBackground(0.1, 0.1, 0.1)
renderer.ResetCamera()

rw = vtk.vtkRenderWindow()
rw.SetOffScreenRendering(True)
rw.SetSize(1280, 720)
rw.AddRenderer(renderer)
rw.Render()

w2i = vtk.vtkWindowToImageFilter()
w2i.SetInput(rw)
w2i.Update()

writer = vtk.vtkPNGWriter()
out_dir = os.environ.get("VIZNOIR_OUTPUT_DIR", "/tmp/viznoir_bench")
Path(out_dir).mkdir(parents=True, exist_ok=True)
writer.SetFileName(os.path.join(out_dir, "bench.png"))
writer.SetInputConnection(w2i.GetOutputPort())
writer.Write()

rw.Finalize()
"""


def _fmt(seconds: float) -> str:
    return f"{seconds * 1000:8.1f} ms"


def bench_inprocess(n: int) -> list[float]:
    """Run the render script N times via InProcessExecutor."""
    from viznoir.core.worker import InProcessExecutor

    executor = InProcessExecutor()
    times: list[float] = []

    for i in range(n):
        with tempfile.TemporaryDirectory(prefix="viznoir_bench_ip_") as tmpdir:
            out = Path(tmpdir) / "output"
            out.mkdir()
            t0 = time.perf_counter()
            result = executor.run(_RENDER_SCRIPT, output_dir=out)
            elapsed = time.perf_counter() - t0
            assert result.exit_code == 0, f"in-process run {i} failed: {result.stderr[:200]}"
            times.append(elapsed)

    return times


async def _subprocess_one(script_path: Path, output_dir: Path) -> float:
    """Run one subprocess execution and return elapsed time."""
    env = {
        **os.environ,
        "VIZNOIR_OUTPUT_DIR": str(output_dir),
    }
    env.pop("DISPLAY", None)

    t0 = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate()
    elapsed = time.perf_counter() - t0

    assert proc.returncode == 0, f"subprocess failed: {stderr.decode()[:200]}"
    return elapsed


def bench_subprocess(n: int) -> list[float]:
    """Run the render script N times via subprocess."""
    times: list[float] = []

    with tempfile.TemporaryDirectory(prefix="viznoir_bench_sp_") as tmpdir:
        script_path = Path(tmpdir) / "pipeline.py"
        script_path.write_text(_RENDER_SCRIPT, encoding="utf-8")

        for i in range(n):
            out = Path(tmpdir) / f"output_{i}"
            out.mkdir()
            elapsed = asyncio.run(_subprocess_one(script_path, out))
            times.append(elapsed)

    return times


def _stats(times: list[float]) -> dict[str, float]:
    s = sorted(times)
    n = len(s)
    return {
        "min": s[0],
        "p50": s[n // 2],
        "mean": statistics.mean(s),
        "p95": s[int(n * 0.95)] if n >= 20 else s[-1],
        "max": s[-1],
        "stdev": statistics.stdev(s) if n > 1 else 0.0,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", "-n", type=int, default=10)
    args = parser.parse_args()
    n = args.iterations

    sep = "=" * 68
    print()
    print("viznoir Execution Mode Benchmark")
    print(f"Script: wavelet 21x21x21 → render 1280x720 → PNG")
    print(f"Iterations: {n} each")
    print(f"Python: {sys.executable}")
    print(sep)

    # Warmup in-process (first run has import overhead)
    print("\n[Warmup] in-process x1 ...", end=" ", flush=True)
    warmup_ip = bench_inprocess(1)
    print(f"{_fmt(warmup_ip[0])}")

    print(f"[Warmup] subprocess x1 ...", end=" ", flush=True)
    warmup_sp = bench_subprocess(1)
    print(f"{_fmt(warmup_sp[0])}")

    # Actual benchmark
    print(f"\n[Bench] in-process x{n} ...", flush=True)
    ip_times = bench_inprocess(n)

    print(f"[Bench] subprocess x{n} ...", flush=True)
    sp_times = bench_subprocess(n)

    ip = _stats(ip_times)
    sp = _stats(sp_times)

    print()
    print(sep)
    header = f"{'Metric':<12} {'In-Process':>12} {'Subprocess':>12} {'Ratio':>8}"
    print(header)
    print("-" * 68)

    for key in ["min", "p50", "mean", "p95", "max", "stdev"]:
        ratio = sp[key] / ip[key] if ip[key] > 0 else float("inf")
        label = "x" if key != "stdev" else ""
        print(f"{key:<12} {_fmt(ip[key]):>12} {_fmt(sp[key]):>12} {ratio:>7.1f}{label}")

    print(sep)
    print(f"\nSubprocess/In-Process median ratio: {sp['p50'] / ip['p50']:.1f}x")
    print()

    # Raw data
    print("Raw timings (ms):")
    print(f"  in-process: {', '.join(f'{t*1000:.1f}' for t in ip_times)}")
    print(f"  subprocess: {', '.join(f'{t*1000:.1f}' for t in sp_times)}")
    print()


if __name__ == "__main__":
    main()
