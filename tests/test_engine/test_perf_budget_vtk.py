"""Performance-budget regression tests — render latency must stay under budget.

These render on the GPU, so they are skipped on GitHub-hosted CI (``*_vtk.py``)
and run on the self-hosted runner where VIZNOIR_RUN_GPU_TESTS is set. Budgets are
deliberately generous (>10x the typical measured latency) so they catch gross
regressions — a render that suddenly takes seconds — without flaking on the
shared host's normal timing noise.
"""

from __future__ import annotations

from time import perf_counter

import pytest
import vtk

from viznoir.engine.renderer import RenderConfig, render_to_png


def _wavelet() -> vtk.vtkImageData:
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    return src.GetOutput()


@pytest.fixture(scope="module")
def wavelet() -> vtk.vtkImageData:
    data = _wavelet()
    # Warm up the singleton render window so the first timed render isn't paying
    # one-time GL/context init.
    render_to_png(data, RenderConfig(array_name="RTData", width=256, height=256))
    return data


def _render_ms(data, config: RenderConfig) -> float:
    t0 = perf_counter()
    png = render_to_png(data, config)
    dt = (perf_counter() - t0) * 1000.0
    assert png[:4] == b"\x89PNG", "render did not produce a valid PNG"
    return dt


class TestRenderBudget:
    def test_wavelet_render_budget(self, wavelet):
        dt = _render_ms(wavelet, RenderConfig(array_name="RTData"))
        assert dt < 3000.0, f"wavelet render {dt:.0f}ms exceeds 3000ms budget"

    def test_low_res_render_budget(self, wavelet):
        dt = _render_ms(wavelet, RenderConfig(array_name="RTData", width=480, height=270))
        assert dt < 1500.0, f"480p render {dt:.0f}ms exceeds 1500ms budget"

    def test_4k_render_budget(self, wavelet):
        dt = _render_ms(wavelet, RenderConfig(array_name="RTData", width=3840, height=2160))
        assert dt < 8000.0, f"4K render {dt:.0f}ms exceeds 8000ms budget"

    def test_colormap_switch_budget(self, wavelet):
        # switching colormaps must not blow up latency
        for cmap in ("viridis", "coolwarm", "turbo"):
            dt = _render_ms(wavelet, RenderConfig(array_name="RTData", colormap=cmap))
            assert dt < 3000.0, f"{cmap} render {dt:.0f}ms exceeds 3000ms budget"
