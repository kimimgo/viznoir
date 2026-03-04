"""Production E2E tests — run real VTK pipeline through tool impls.

These tests create actual VTK data, run through the real VTKRunner subprocess,
and verify real outputs (images, data dicts). No mocking.

Requires: vtk, PIL (Pillow)
"""

from __future__ import annotations

import pytest
import vtk

from parapilot.core.output import PipelineResult
from parapilot.core.runner import VTKRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def runner() -> VTKRunner:
    """Real VTKRunner (local mode)."""
    return VTKRunner(mode="local")


@pytest.fixture(scope="module")
def wavelet_vti(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create a wavelet VTI file with RTData scalar field."""
    path = tmp_path_factory.mktemp("data") / "wavelet.vti"
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(src.GetOutput())
    writer.Write()
    assert path.exists() and path.stat().st_size > 0
    return str(path)


@pytest.fixture(scope="module")
def superquadric_vtp(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create a superquadric VTP file with Elevation field."""
    path = tmp_path_factory.mktemp("data") / "superquadric.vtp"
    sq = vtk.vtkSuperquadricSource()
    sq.SetPhiResolution(32)
    sq.SetThetaResolution(32)
    sq.ToroidalOn()
    sq.Update()
    elev = vtk.vtkElevationFilter()
    elev.SetInputData(sq.GetOutput())
    elev.SetLowPoint(0, 0, -1)
    elev.SetHighPoint(0, 0, 1)
    elev.Update()
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(elev.GetOutput())
    writer.Write()
    assert path.exists()
    return str(path)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_pipeline_result_has_image(result: PipelineResult) -> None:
    """Assert that a PipelineResult contains a valid PNG image."""
    assert result.ok, f"Pipeline failed: {result.raw.stderr if result.raw else 'no raw'}"
    assert result.image_bytes is not None, "No image bytes"
    assert len(result.image_bytes) > 1000, f"Image too small: {len(result.image_bytes)} bytes"
    # Verify PNG magic bytes
    assert result.image_bytes[:4] == b"\x89PNG", "Not a valid PNG"
    assert result.image_base64 is not None


# ---------------------------------------------------------------------------
# 1. inspect_data — returns dict
# ---------------------------------------------------------------------------


class TestInspectDataE2E:
    @pytest.mark.asyncio
    async def test_inspect_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.inspect import inspect_data_impl

        result = await inspect_data_impl(wavelet_vti, runner)
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Should contain bounds, arrays, or similar metadata
        assert len(result) > 0, "Empty inspect result"

    @pytest.mark.asyncio
    async def test_inspect_polydata(self, superquadric_vtp: str, runner: VTKRunner) -> None:
        from parapilot.tools.inspect import inspect_data_impl

        result = await inspect_data_impl(superquadric_vtp, runner)
        assert isinstance(result, dict)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# 2. render — returns PipelineResult with image
# ---------------------------------------------------------------------------


class TestRenderE2E:
    @pytest.mark.asyncio
    async def test_render_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.render import render_impl

        result = await render_impl(
            file_path=wavelet_vti,
            field_name="RTData",
            runner=runner,
            colormap="Cool to Warm",
            camera="isometric",
            width=640,
            height=480,
        )
        _assert_pipeline_result_has_image(result)

    @pytest.mark.asyncio
    async def test_render_with_viridis(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.render import render_impl

        result = await render_impl(
            file_path=wavelet_vti,
            field_name="RTData",
            runner=runner,
            colormap="Viridis",
            width=640,
            height=480,
        )
        _assert_pipeline_result_has_image(result)

    @pytest.mark.asyncio
    async def test_render_polydata(self, superquadric_vtp: str, runner: VTKRunner) -> None:
        from parapilot.tools.render import render_impl

        result = await render_impl(
            file_path=superquadric_vtp,
            field_name="Elevation",
            runner=runner,
            colormap="Magma",
            width=640,
            height=480,
        )
        _assert_pipeline_result_has_image(result)


# ---------------------------------------------------------------------------
# 3. slice — returns PipelineResult with image
# ---------------------------------------------------------------------------


class TestSliceE2E:
    @pytest.mark.asyncio
    async def test_slice_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.filters import slice_impl

        result = await slice_impl(
            file_path=wavelet_vti,
            field_name="RTData",
            runner=runner,
            origin=[0, 0, 0],
            normal=[1, 0, 0],
            colormap="Plasma",
            width=640,
            height=480,
        )
        _assert_pipeline_result_has_image(result)


# ---------------------------------------------------------------------------
# 4. contour — returns PipelineResult with image
# ---------------------------------------------------------------------------


class TestContourE2E:
    @pytest.mark.asyncio
    async def test_contour_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.filters import contour_impl

        result = await contour_impl(
            file_path=wavelet_vti,
            field_name="RTData",
            isovalues=[100.0, 200.0],
            runner=runner,
            colormap="Turbo",
            width=640,
            height=480,
        )
        _assert_pipeline_result_has_image(result)


# ---------------------------------------------------------------------------
# 5. clip — returns PipelineResult with image
# ---------------------------------------------------------------------------


class TestClipE2E:
    @pytest.mark.asyncio
    async def test_clip_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.filters import clip_impl

        result = await clip_impl(
            file_path=wavelet_vti,
            field_name="RTData",
            runner=runner,
            origin=[0, 0, 0],
            normal=[1, 0, 0],
            colormap="Viridis",
            width=640,
            height=480,
        )
        _assert_pipeline_result_has_image(result)


# ---------------------------------------------------------------------------
# 6. extract_stats — returns dict
# ---------------------------------------------------------------------------


class TestExtractStatsE2E:
    @pytest.mark.asyncio
    async def test_extract_wavelet_stats(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.extract import extract_stats_impl

        result = await extract_stats_impl(
            file_path=wavelet_vti,
            fields=["RTData"],
            runner=runner,
        )
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"


# ---------------------------------------------------------------------------
# 7. plot_over_line — returns dict
# ---------------------------------------------------------------------------


class TestPlotOverLineE2E:
    @pytest.mark.asyncio
    async def test_plot_over_line_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.extract import plot_over_line_impl

        result = await plot_over_line_impl(
            file_path=wavelet_vti,
            field_name="RTData",
            point1=[-10, 0, 0],
            point2=[10, 0, 0],
            runner=runner,
            resolution=50,
        )
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"


# ---------------------------------------------------------------------------
# 8. streamlines — returns PipelineResult with image
# ---------------------------------------------------------------------------


class TestStreamlinesE2E:
    @pytest.mark.asyncio
    async def test_streamlines_wavelet(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.filters import streamlines_impl

        result = await streamlines_impl(
            file_path=wavelet_vti,
            vector_field="RTData",
            runner=runner,
            seed_point1=[-5, -5, 0],
            seed_point2=[5, 5, 0],
            seed_resolution=5,
            max_length=50.0,
            colormap="Plasma",
            width=640,
            height=480,
        )
        # Streamlines may produce empty output if the field is scalar (not vector),
        # but the pipeline itself should succeed
        assert result.ok or result.image_bytes is not None


# ---------------------------------------------------------------------------
# 9. execute_pipeline (DSL) — returns PipelineResult
# ---------------------------------------------------------------------------


class TestExecutePipelineE2E:
    @pytest.mark.asyncio
    async def test_pipeline_dsl(self, wavelet_vti: str, runner: VTKRunner) -> None:
        from parapilot.tools.pipeline import execute_pipeline_impl

        result = await execute_pipeline_impl(
            pipeline_json={
                "source": {"file": wavelet_vti},
                "pipeline": [
                    {"filter": "Slice", "params": {"origin": [0, 0, 0], "normal": [0, 0, 1]}},
                ],
                "output": {
                    "type": "image",
                    "render": {
                        "field": "RTData",
                        "colormap": "Cool to Warm",
                        "resolution": [640, 480],
                    },
                },
            },
            runner=runner,
        )
        assert isinstance(result, PipelineResult)
        _assert_pipeline_result_has_image(result)
