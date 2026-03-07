"""Viznoir rendering performance benchmark suite.

Measures render/filter latency and detects regressions using the engine layer
directly — no MCP server round-trip.  VTK Wavelet (vtkRTAnalyticSource) is
used as the sole data source so no external files are required.

Usage
-----
Run as a standalone script (time module, no extra deps):

    python benchmarks/bench_render.py

Run with pytest-benchmark (optional, install with ``pip install pytest-benchmark``):

    pytest benchmarks/bench_render.py -v --benchmark-sort=mean

Environment
-----------
Set ``VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow`` to enable GPU EGL
headless rendering (required on headless servers).  Without it VTK falls back
to OSMesa (software) if available.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable

# ---------------------------------------------------------------------------
# Ensure the project src layout is importable when run directly.
# ---------------------------------------------------------------------------

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


# ---------------------------------------------------------------------------
# Wavelet dataset factory
# ---------------------------------------------------------------------------


def _make_wavelet(extent: int = 10) -> object:
    """Create a VTK Wavelet (RTAnalytic) dataset.

    Args:
        extent: Half-extent in each axis.  ``extent=10`` yields a
            21x21x21 voxel grid with an ``RTData`` point array.

    Returns:
        ``vtkImageData`` with the wavelet scalar field.
    """
    import vtk  # type: ignore[import-untyped]

    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-extent, extent, -extent, extent, -extent, extent)
    src.Update()
    return src.GetOutput()


# ---------------------------------------------------------------------------
# Resolution helper
# ---------------------------------------------------------------------------

_RESOLUTIONS: dict[str, tuple[int, int]] = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4K": (3840, 2160),
}

# ---------------------------------------------------------------------------
# Benchmark: basic wavelet render
# ---------------------------------------------------------------------------


def bench_wavelet_render(benchmark: Callable | None = None) -> float:
    """Benchmark: render the Wavelet dataset at 720p.

    Measures end-to-end latency from ``vtkRTAnalyticSource`` through
    ``VTKRenderer.render()`` to PNG bytes.

    Args:
        benchmark: Optional pytest-benchmark fixture.  When ``None`` the
            function times itself with ``time.perf_counter``.

    Returns:
        Elapsed time in seconds (standalone mode).  When called via
        pytest-benchmark the fixture controls timing and the return value
        is ignored.
    """
    from viznoir.engine.renderer import RenderConfig, VTKRenderer

    data = _make_wavelet()
    renderer = VTKRenderer(RenderConfig(width=1280, height=720, array_name="RTData"))

    def _run() -> bytes:
        return renderer.render(data)

    if benchmark is not None:
        benchmark(_run)
        return 0.0

    t0 = time.perf_counter()
    png = _run()
    elapsed = time.perf_counter() - t0

    assert png[:4] == b"\x89PNG", "render did not produce a valid PNG"
    return elapsed


# ---------------------------------------------------------------------------
# Benchmark: slice filter
# ---------------------------------------------------------------------------


def bench_wavelet_slice(benchmark: Callable | None = None) -> float:
    """Benchmark: slice the Wavelet dataset with a Z-normal plane.

    Measures ``slice_plane()`` filter latency (VTK cutter pipeline).
    The resulting polydata is rendered at 640x480 so the render overhead
    is consistent across runs.

    Args:
        benchmark: Optional pytest-benchmark fixture.

    Returns:
        Elapsed time in seconds (standalone mode).
    """
    from viznoir.engine.filters import slice_plane
    from viznoir.engine.renderer import RenderConfig, VTKRenderer

    data = _make_wavelet()
    renderer = VTKRenderer(RenderConfig(width=640, height=480))

    def _run() -> bytes:
        sliced = slice_plane(data, normal=(0.0, 0.0, 1.0))
        return renderer.render(sliced)

    if benchmark is not None:
        benchmark(_run)
        return 0.0

    t0 = time.perf_counter()
    png = _run()
    elapsed = time.perf_counter() - t0

    assert png[:4] == b"\x89PNG", "slice render did not produce a valid PNG"
    return elapsed


# ---------------------------------------------------------------------------
# Benchmark: contour filter
# ---------------------------------------------------------------------------


def bench_wavelet_contour(benchmark: Callable | None = None) -> float:
    """Benchmark: extract isosurface from the Wavelet dataset.

    Two isovalue contours (120 and 200) are extracted from the ``RTData``
    scalar field.  The resulting polydata is rendered at 640x480.

    Args:
        benchmark: Optional pytest-benchmark fixture.

    Returns:
        Elapsed time in seconds (standalone mode).
    """
    from viznoir.engine.filters import contour
    from viznoir.engine.renderer import RenderConfig, VTKRenderer

    data = _make_wavelet()
    renderer = VTKRenderer(RenderConfig(width=640, height=480, array_name="RTData"))

    def _run() -> bytes:
        iso = contour(data, array_name="RTData", values=[120.0, 200.0])
        return renderer.render(iso)

    if benchmark is not None:
        benchmark(_run)
        return 0.0

    t0 = time.perf_counter()
    png = _run()
    elapsed = time.perf_counter() - t0

    assert png[:4] == b"\x89PNG", "contour render did not produce a valid PNG"
    return elapsed


# ---------------------------------------------------------------------------
# Benchmark: resolution scaling
# ---------------------------------------------------------------------------


def bench_resolution_scaling(benchmark: Callable | None = None) -> dict[str, float]:
    """Benchmark: render times across 480p, 720p, 1080p, and 4K.

    Each resolution is timed independently.  In pytest-benchmark mode the
    benchmark fixture is called once per resolution (parametrized outside
    via ``pytest.mark.parametrize`` or run individually).

    Args:
        benchmark: Optional pytest-benchmark fixture.  When provided the
            first resolution (480p) is used for the fixture call; timings
            for all resolutions are still returned.

    Returns:
        Dict mapping resolution label to elapsed seconds.
    """
    from viznoir.engine.renderer import RenderConfig, VTKRenderer

    data = _make_wavelet()
    timings: dict[str, float] = {}

    for label, (w, h) in _RESOLUTIONS.items():
        renderer = VTKRenderer(RenderConfig(width=w, height=h, array_name="RTData"))

        if benchmark is not None and label == "480p":
            # Only wrap the smallest resolution in the fixture to keep
            # benchmark runs fast; other resolutions are timed manually.
            def _run_480() -> bytes:
                return renderer.render(data)

            benchmark(_run_480)
            timings[label] = 0.0
            continue

        t0 = time.perf_counter()
        png = renderer.render(data)
        elapsed = time.perf_counter() - t0

        assert png[:4] == b"\x89PNG", f"resolution {label} did not produce valid PNG"
        timings[label] = elapsed

    return timings


# ---------------------------------------------------------------------------
# Benchmark: colormap switch
# ---------------------------------------------------------------------------

_COLORMAPS = [
    "cool to warm",
    "viridis",
    "plasma",
    "inferno",
    "turbo",
    "jet",
]


def bench_colormap_switch(benchmark: Callable | None = None) -> dict[str, float]:
    """Benchmark: render time for each of six colormaps at 720p.

    Tests whether colormap look-up table construction introduces measurable
    overhead.  Each colormap is rendered independently so results are
    comparable.

    Args:
        benchmark: Optional pytest-benchmark fixture.  When provided the
            first colormap (``"cool to warm"``) is wrapped in the fixture.

    Returns:
        Dict mapping colormap name to elapsed seconds.
    """
    from viznoir.engine.renderer import RenderConfig, VTKRenderer

    data = _make_wavelet()
    timings: dict[str, float] = {}

    for cmap in _COLORMAPS:
        renderer = VTKRenderer(
            RenderConfig(width=1280, height=720, colormap=cmap, array_name="RTData")
        )

        if benchmark is not None and cmap == _COLORMAPS[0]:
            def _run_cmap() -> bytes:
                return renderer.render(data)

            benchmark(_run_cmap)
            timings[cmap] = 0.0
            continue

        t0 = time.perf_counter()
        png = renderer.render(data)
        elapsed = time.perf_counter() - t0

        assert png[:4] == b"\x89PNG", f"colormap {cmap!r} did not produce valid PNG"
        timings[cmap] = elapsed

    return timings


# ---------------------------------------------------------------------------
# pytest-benchmark wrappers (auto-discovered by pytest)
# ---------------------------------------------------------------------------

try:
    import pytest  # type: ignore[import-untyped]

    # ---------------------------------------------------------------------------
    # Detect whether pytest-benchmark is available.
    # When it is NOT installed we provide a minimal no-op ``benchmark`` fixture
    # so the test functions still run (as plain timing tests) without error.
    # ---------------------------------------------------------------------------
    try:
        import pytest_benchmark  # noqa: F401  # type: ignore[import-untyped]

        _HAVE_BENCHMARK = True
    except ImportError:
        _HAVE_BENCHMARK = False

    if not _HAVE_BENCHMARK:
        # Minimal stand-in: calls the callable once and returns the result.
        @pytest.fixture
        def benchmark() -> Callable[..., object]:  # type: ignore[misc]
            """Fallback benchmark fixture when pytest-benchmark is not installed."""

            def _bench(fn: Callable[..., object], *args: object, **kwargs: object) -> object:
                return fn(*args, **kwargs)

            return _bench

    @pytest.fixture(scope="module")
    def wavelet_data() -> object:
        """Module-scoped wavelet fixture for benchmark tests."""
        return _make_wavelet()

    def test_bench_wavelet_render(benchmark: Callable[..., object], wavelet_data: object) -> None:
        """Render the Wavelet dataset at 720p.

        With pytest-benchmark installed: measures mean/min/max latency over
        multiple rounds.  Without it: runs once and asserts a valid PNG.
        """
        from viznoir.engine.renderer import RenderConfig, VTKRenderer

        renderer = VTKRenderer(RenderConfig(width=1280, height=720, array_name="RTData"))
        result = benchmark(renderer.render, wavelet_data)
        assert isinstance(result, bytes) and result[:4] == b"\x89PNG"

    def test_bench_wavelet_slice(benchmark: Callable[..., object], wavelet_data: object) -> None:
        """Slice filter + render at 640x480.

        Measures ``slice_plane()`` + ``VTKRenderer.render()`` combined latency.
        """
        from viznoir.engine.filters import slice_plane
        from viznoir.engine.renderer import RenderConfig, VTKRenderer

        renderer = VTKRenderer(RenderConfig(width=640, height=480))

        def _run() -> bytes:
            sliced = slice_plane(wavelet_data, normal=(0.0, 0.0, 1.0))
            return renderer.render(sliced)

        result = benchmark(_run)
        assert isinstance(result, bytes) and result[:4] == b"\x89PNG"

    def test_bench_wavelet_contour(benchmark: Callable[..., object], wavelet_data: object) -> None:
        """Contour isosurface + render at 640x480.

        Extracts two isosurfaces (120, 200) from ``RTData`` then renders.
        """
        from viznoir.engine.filters import contour
        from viznoir.engine.renderer import RenderConfig, VTKRenderer

        renderer = VTKRenderer(RenderConfig(width=640, height=480, array_name="RTData"))

        def _run() -> bytes:
            iso = contour(wavelet_data, array_name="RTData", values=[120.0, 200.0])
            return renderer.render(iso)

        result = benchmark(_run)
        assert isinstance(result, bytes) and result[:4] == b"\x89PNG"

    @pytest.mark.parametrize("label,wh", list(_RESOLUTIONS.items()))
    def test_bench_resolution_scaling(
        benchmark: Callable[..., object],
        label: str,
        wh: tuple[int, int],
        wavelet_data: object,
    ) -> None:
        """Render wavelet at each output resolution (480p / 720p / 1080p / 4K)."""
        from viznoir.engine.renderer import RenderConfig, VTKRenderer

        w, h = wh
        renderer = VTKRenderer(RenderConfig(width=w, height=h, array_name="RTData"))
        result = benchmark(renderer.render, wavelet_data)
        assert isinstance(result, bytes) and result[:4] == b"\x89PNG"

    @pytest.mark.parametrize("cmap", _COLORMAPS)
    def test_bench_colormap_switch(
        benchmark: Callable[..., object],
        cmap: str,
        wavelet_data: object,
    ) -> None:
        """Render wavelet with each of the six built-in colormaps at 720p."""
        from viznoir.engine.renderer import RenderConfig, VTKRenderer

        renderer = VTKRenderer(
            RenderConfig(width=1280, height=720, colormap=cmap, array_name="RTData")
        )
        result = benchmark(renderer.render, wavelet_data)
        assert isinstance(result, bytes) and result[:4] == b"\x89PNG"

except ImportError:
    # pytest not installed — skip test function definitions silently.
    pass


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _fmt(seconds: float) -> str:
    """Format seconds to milliseconds string."""
    return f"{seconds * 1000:.1f} ms"


def _run_all() -> None:
    """Run all benchmarks and print a summary table."""
    separator = "-" * 52
    print()
    print("viznoir rendering benchmark")
    print(separator)

    # 1. Basic render
    try:
        elapsed = bench_wavelet_render()
        print(f"{'bench_wavelet_render':<35} {_fmt(elapsed):>10}")
    except Exception as exc:
        print(f"{'bench_wavelet_render':<35} {'ERROR':>10}  ({exc})")

    # 2. Slice
    try:
        elapsed = bench_wavelet_slice()
        print(f"{'bench_wavelet_slice':<35} {_fmt(elapsed):>10}")
    except Exception as exc:
        print(f"{'bench_wavelet_slice':<35} {'ERROR':>10}  ({exc})")

    # 3. Contour
    try:
        elapsed = bench_wavelet_contour()
        print(f"{'bench_wavelet_contour':<35} {_fmt(elapsed):>10}")
    except Exception as exc:
        print(f"{'bench_wavelet_contour':<35} {'ERROR':>10}  ({exc})")

    # 4. Resolution scaling
    print()
    print("bench_resolution_scaling")
    try:
        timings = bench_resolution_scaling()
        for label, t in timings.items():
            print(f"  {label:<31} {_fmt(t):>10}")
    except Exception as exc:
        print(f"  {'ERROR':<31}  ({exc})")

    # 5. Colormap switch
    print()
    print("bench_colormap_switch")
    try:
        timings_cm = bench_colormap_switch()
        for cmap, t in timings_cm.items():
            print(f"  {cmap:<31} {_fmt(t):>10}")
    except Exception as exc:
        print(f"  {'ERROR':<31}  ({exc})")

    print(separator)
    print()


if __name__ == "__main__":
    _run_all()
