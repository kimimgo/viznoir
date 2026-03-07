"""Tests for tool implementation modules — validate PipelineDefinition construction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from viznoir.core.output import PipelineResult
from viznoir.core.runner import RunResult


def _mock_pipeline_result(**kwargs):
    rr = RunResult(stdout="", stderr="", exit_code=0, json_result={"ok": True})
    return PipelineResult(output_type="data", json_data={"ok": True}, raw=rr, **kwargs)


# ---------------------------------------------------------------------------
# animate_impl
# ---------------------------------------------------------------------------

class TestAnimateImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.animate.execute_pipeline")
    async def test_animate_builds_pipeline(self, mock_exec):
        from viznoir.tools.animate import animate_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await animate_impl(
            file_path="/data/case.vtk",
            field_name="velocity",
            runner=runner,
            mode="orbit",
            fps=30,
        )

        mock_exec.assert_called_once()
        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.source.file == "/data/case.vtk"
        assert pipeline_def.output.type == "animation"
        assert pipeline_def.output.animation is not None
        assert pipeline_def.output.animation.mode == "orbit"
        assert pipeline_def.output.animation.fps == 30
        assert pipeline_def.output.animation.render.field == "velocity"

    @pytest.mark.asyncio
    @patch("viznoir.tools.animate.execute_pipeline")
    async def test_animate_time_range(self, mock_exec):
        from viznoir.tools.animate import animate_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await animate_impl(
            file_path="/data/case.vtk",
            field_name="p",
            runner=runner,
            time_range=[0.0, 5.0],
            speed_factor=2.0,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.output.animation.time_range == [0.0, 5.0]
        assert pipeline_def.output.animation.speed_factor == 2.0

    @pytest.mark.asyncio
    @patch("viznoir.tools.animate.execute_pipeline")
    async def test_animate_video_output(self, mock_exec):
        from viznoir.tools.animate import animate_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await animate_impl(
            file_path="/data/case.vtk",
            field_name="p",
            runner=runner,
            output_format="mp4",
            video_quality=18,
            text_overlay="Test",
        )

        pipeline_def = mock_exec.call_args[0][0]
        anim = pipeline_def.output.animation
        assert anim.output_format == "mp4"
        assert anim.video_quality == 18
        assert anim.text_overlay == "Test"

    @pytest.mark.asyncio
    @patch("viznoir.tools.animate.execute_pipeline")
    async def test_animate_multi_file(self, mock_exec):
        from viznoir.tools.animate import animate_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await animate_impl(
            file_path="/data/case_0000.vtk",
            field_name="p",
            runner=runner,
            files=["/data/case_0000.vtk", "/data/case_0001.vtk"],
            file_pattern="case_*.vtk",
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.source.files == ["/data/case_0000.vtk", "/data/case_0001.vtk"]
        assert pipeline_def.source.file_pattern == "case_*.vtk"


# ---------------------------------------------------------------------------
# split_animate_impl
# ---------------------------------------------------------------------------

class TestSplitAnimateImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.split_animate.execute_split_animation")
    async def test_split_animate_builds_pipeline(self, mock_exec):
        from viznoir.tools.split_animate import split_animate_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        panes = [
            {"type": "render", "row": 0, "col": 0,
             "render_pane": {"render": {"field": "p"}}},
            {"type": "graph", "row": 0, "col": 1,
             "graph_pane": {"series": [{"field": "p", "stat": "max"}]}},
        ]

        await split_animate_impl(
            file_path="/data/case.vtk",
            panes=panes,
            runner=runner,
            fps=30,
        )

        mock_exec.assert_called_once()
        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.source.file == "/data/case.vtk"
        assert pipeline_def.output.type == "split_animation"
        assert pipeline_def.output.split_animation is not None
        assert len(pipeline_def.output.split_animation.panes) == 2
        assert pipeline_def.output.split_animation.fps == 30

    @pytest.mark.asyncio
    @patch("viznoir.tools.split_animate.execute_split_animation")
    async def test_split_animate_with_layout(self, mock_exec):
        from viznoir.tools.split_animate import split_animate_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        panes = [
            {"type": "render", "row": 0, "col": 0,
             "render_pane": {"render": {"field": "p"}}},
        ]

        await split_animate_impl(
            file_path="/data/case.vtk",
            panes=panes,
            runner=runner,
            layout={"rows": 2, "cols": 2},
            time_range=[0.0, 1.0],
            speed_factor=0.5,
            resolution=[3840, 2160],
        )

        pipeline_def = mock_exec.call_args[0][0]
        sa = pipeline_def.output.split_animation
        assert sa.layout.rows == 2
        assert sa.layout.cols == 2
        assert sa.time_range == [0.0, 1.0]
        assert sa.speed_factor == 0.5
        assert sa.resolution == [3840, 2160]


# ---------------------------------------------------------------------------
# isosurface_impl
# ---------------------------------------------------------------------------

class TestIsosurfaceImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_success(self, mock_subprocess, tmp_path):
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"done", b"")
        mock_subprocess.return_value = mock_proc

        bi4_dir = tmp_path / "bi4"
        bi4_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create fake VTK files
        (output_dir / "iso_0000.vtk").parent.mkdir(parents=True, exist_ok=True)
        (output_dir / "iso_0000.vtk").touch()
        (output_dir / "iso_0001.vtk").touch()

        result = await pv_isosurface_impl(str(bi4_dir), str(output_dir))
        assert result["count"] == 2
        assert len(result["iso_files"]) == 2

    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_failure(self, mock_subprocess, tmp_path):
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"IsoSurface error")
        mock_subprocess.return_value = mock_proc

        with pytest.raises(RuntimeError, match="IsoSurface failed"):
            await pv_isosurface_impl(str(tmp_path), str(tmp_path / "out"))

    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_custom_params(self, mock_subprocess, tmp_path):
        """Custom docker_image, vars, and only_type parameters are passed correctly."""
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"ok", b"")
        mock_subprocess.return_value = mock_proc

        bi4_dir = tmp_path / "bi4"
        bi4_dir.mkdir()
        output_dir = tmp_path / "out"

        result = await pv_isosurface_impl(
            str(bi4_dir), str(output_dir),
            vars="+vel", only_type="+all", docker_image="custom:v2",
        )
        assert result["count"] == 0  # no iso_*.vtk files created

        # Verify Docker command includes custom params
        call_args = mock_subprocess.call_args[0]
        assert "custom:v2" in call_args
        assert "-vars:+vel" in call_args
        assert "-onlytype:+all" in call_args

    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_empty_output(self, mock_subprocess, tmp_path):
        """Zero output files returns count=0."""
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")
        mock_subprocess.return_value = mock_proc

        bi4_dir = tmp_path / "bi4"
        bi4_dir.mkdir()
        output_dir = tmp_path / "out"

        result = await pv_isosurface_impl(str(bi4_dir), str(output_dir))
        assert result["count"] == 0
        assert result["iso_files"] == []
        assert result["stdout"] == ""

    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_stdout_truncation(self, mock_subprocess, tmp_path):
        """Stdout is truncated to last 500 chars."""
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        long_output = b"x" * 1000
        mock_proc.communicate.return_value = (long_output, b"")
        mock_subprocess.return_value = mock_proc

        bi4_dir = tmp_path / "bi4"
        bi4_dir.mkdir()
        output_dir = tmp_path / "out"

        result = await pv_isosurface_impl(str(bi4_dir), str(output_dir))
        assert len(result["stdout"]) == 500

    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_error_includes_exit_code(self, mock_subprocess, tmp_path):
        """Error message includes the exit code."""
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 137
        mock_proc.communicate.return_value = (b"", b"Killed")
        mock_subprocess.return_value = mock_proc

        with pytest.raises(RuntimeError, match="exit 137"):
            await pv_isosurface_impl(str(tmp_path), str(tmp_path / "out"))

    @pytest.mark.asyncio
    @patch("viznoir.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_creates_output_dir(self, mock_subprocess, tmp_path):
        """Output directory is created automatically if it doesn't exist."""
        from viznoir.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"ok", b"")
        mock_subprocess.return_value = mock_proc

        bi4_dir = tmp_path / "bi4"
        bi4_dir.mkdir()
        output_dir = tmp_path / "nested" / "output"

        result = await pv_isosurface_impl(str(bi4_dir), str(output_dir))
        assert output_dir.is_dir()
        assert result["output_dir"] == str(output_dir.resolve())


# ---------------------------------------------------------------------------
# extract impls
# ---------------------------------------------------------------------------

class TestExtractImpls:
    @pytest.mark.asyncio
    @patch("viznoir.tools.extract.execute_pipeline")
    async def test_integrate_surface_with_boundary(self, mock_exec):
        from viznoir.tools.extract import integrate_surface_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await integrate_surface_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            runner=runner,
            boundary="inlet",
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert len(pipeline_def.pipeline) == 3  # ExtractBlock + ExtractSurface + IntegrateVariables
        assert pipeline_def.pipeline[0].filter == "ExtractBlock"
        assert pipeline_def.pipeline[0].params["selector"] == "inlet"

    @pytest.mark.asyncio
    @patch("viznoir.tools.extract.execute_pipeline")
    async def test_integrate_surface_no_boundary(self, mock_exec):
        from viznoir.tools.extract import integrate_surface_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await integrate_surface_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            runner=runner,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert len(pipeline_def.pipeline) == 2  # ExtractSurface + IntegrateVariables


# ---------------------------------------------------------------------------
# preview_3d_impl
# ---------------------------------------------------------------------------

class TestPreview3dImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.preview3d.export_gltf")
    @patch("viznoir.tools.preview3d.read_dataset")
    async def test_preview_3d_basic(self, mock_read, mock_export, tmp_path):
        from viznoir.tools.preview3d import preview_3d_impl

        mock_read.return_value = MagicMock()
        mock_export.return_value = {
            "path": str(tmp_path / "preview.glb"),
            "format": ".glb",
            "size_bytes": 1024,
        }
        runner = MagicMock()

        import os
        with patch.dict(os.environ, {"VIZNOIR_OUTPUT_DIR": str(tmp_path)}):
            result = await preview_3d_impl(
                file_path="/data/case.vtk",
                runner=runner,
            )

        assert result["format"] == ".glb"
        assert "viewer_hint" in result
        mock_read.assert_called_once()
        mock_export.assert_called_once()

    @pytest.mark.asyncio
    @patch("viznoir.tools.preview3d.get_timesteps")
    @patch("viznoir.tools.preview3d.export_gltf")
    @patch("viznoir.tools.preview3d.read_dataset")
    async def test_preview_3d_latest_timestep(self, mock_read, mock_export, mock_ts, tmp_path):
        from viznoir.tools.preview3d import preview_3d_impl

        mock_ts.return_value = [0.0, 1.0, 2.0]
        mock_read.return_value = MagicMock()
        mock_export.return_value = {"path": "p.glb", "format": ".glb", "size_bytes": 512}
        runner = MagicMock()

        import os
        with patch.dict(os.environ, {"VIZNOIR_OUTPUT_DIR": str(tmp_path)}):
            await preview_3d_impl(
                file_path="/data/case.vtk",
                runner=runner,
                timestep="latest",
            )

        mock_read.assert_called_once_with("/data/case.vtk", timestep=2.0)

    @pytest.mark.asyncio
    @patch("viznoir.tools.preview3d.export_gltf")
    @patch("viznoir.tools.preview3d.read_dataset")
    async def test_preview_3d_string_timestep(self, mock_read, mock_export, tmp_path):
        """String timestep (not 'latest') is converted to float."""
        from viznoir.tools.preview3d import preview_3d_impl

        mock_read.return_value = MagicMock()
        mock_export.return_value = {"path": "p.glb", "format": ".glb", "size_bytes": 512}
        runner = MagicMock()

        import os
        with patch.dict(os.environ, {"VIZNOIR_OUTPUT_DIR": str(tmp_path)}):
            await preview_3d_impl(
                file_path="/data/case.vtk",
                runner=runner,
                timestep="1.5",
            )

        mock_read.assert_called_once_with("/data/case.vtk", timestep=1.5)


# ---------------------------------------------------------------------------
# slice_impl, streamlines_impl (zoom branch coverage)
# ---------------------------------------------------------------------------

class TestSliceImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.filters.execute_pipeline")
    async def test_slice_with_zoom(self, mock_exec):
        from viznoir.tools.filters import slice_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await slice_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            runner=runner,
            zoom=2.0,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.output.render.camera.zoom == 2.0

    @pytest.mark.asyncio
    @patch("viznoir.tools.filters.execute_pipeline")
    async def test_slice_basic(self, mock_exec):
        from viznoir.tools.filters import slice_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await slice_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            runner=runner,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.pipeline[0].filter == "Slice"
        assert pipeline_def.output.render.field == "pressure"


class TestStreamlinesImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.filters.execute_pipeline")
    async def test_streamlines_with_zoom(self, mock_exec):
        from viznoir.tools.filters import streamlines_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await streamlines_impl(
            file_path="/data/case.vtk",
            vector_field="velocity",
            runner=runner,
            zoom=1.5,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.output.render.camera.zoom == 1.5

    @pytest.mark.asyncio
    @patch("viznoir.tools.filters.execute_pipeline")
    async def test_streamlines_basic(self, mock_exec):
        from viznoir.tools.filters import streamlines_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await streamlines_impl(
            file_path="/data/case.vtk",
            vector_field="velocity",
            runner=runner,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.pipeline[0].filter == "StreamTracer"
        assert pipeline_def.output.render.field == "velocity"


# ---------------------------------------------------------------------------
# render_impl
# ---------------------------------------------------------------------------

class TestRenderImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.render.execute_pipeline")
    async def test_render_builds_pipeline(self, mock_exec):
        from viznoir.tools.render import render_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await render_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            runner=runner,
        )

        mock_exec.assert_called_once()
        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.source.file == "/data/case.vtk"
        assert pipeline_def.output.type == "image"
        assert pipeline_def.output.render.field == "pressure"

    @pytest.mark.asyncio
    @patch("viznoir.tools.render.execute_pipeline")
    async def test_render_with_zoom(self, mock_exec):
        from viznoir.tools.render import render_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await render_impl(
            file_path="/data/case.vtk",
            field_name="velocity",
            runner=runner,
            zoom=2.5,
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.output.render.camera.zoom == 2.5

    @pytest.mark.asyncio
    @patch("viznoir.tools.render.execute_pipeline")
    async def test_render_with_background(self, mock_exec):
        from viznoir.tools.render import render_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await render_impl(
            file_path="/data/case.vtk",
            field_name="temperature",
            runner=runner,
            background=[0.1, 0.2, 0.3],
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.output.render.background == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    @patch("viznoir.tools.render.execute_pipeline")
    async def test_render_with_all_options(self, mock_exec):
        from viznoir.tools.render import render_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await render_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            runner=runner,
            association="CELLS",
            colormap="Plasma",
            camera="top",
            scalar_range=[0.0, 100.0],
            width=800,
            height=600,
            timestep="latest",
            blocks=["inlet", "outlet"],
            zoom=1.5,
            background=[1.0, 1.0, 1.0],
            output_filename="my_render.png",
        )

        pipeline_def = mock_exec.call_args[0][0]
        render_def = pipeline_def.output.render
        assert render_def.association == "CELLS"
        assert render_def.colormap == "Plasma"
        assert render_def.camera.preset == "top"
        assert render_def.camera.zoom == 1.5
        assert render_def.scalar_range == [0.0, 100.0]
        assert render_def.resolution == [800, 600]
        assert render_def.output_filename == "my_render.png"
        assert render_def.background == [1.0, 1.0, 1.0]
        assert pipeline_def.source.timestep == "latest"
        assert pipeline_def.source.blocks == ["inlet", "outlet"]


# ---------------------------------------------------------------------------
# batch_render_impl
# ---------------------------------------------------------------------------

class TestProbeTimeseriesImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.probe.execute_pipeline")
    async def test_probe_builds_pipeline(self, mock_exec):
        from viznoir.tools.probe import probe_timeseries_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await probe_timeseries_impl(
            file_path="/data/case.vtk",
            field_name="pressure",
            point=[0.5, 0.5, 0.0],
            runner=runner,
        )

        mock_exec.assert_called_once()
        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.source.file == "/data/case.vtk"
        assert len(pipeline_def.pipeline) == 1
        assert pipeline_def.pipeline[0].filter == "ProbePoint"
        assert pipeline_def.pipeline[0].params["point"] == [0.5, 0.5, 0.0]
        assert pipeline_def.output.type == "data"

    @pytest.mark.asyncio
    @patch("viznoir.tools.probe.execute_pipeline")
    async def test_probe_with_files(self, mock_exec):
        from viznoir.tools.probe import probe_timeseries_impl

        mock_exec.return_value = _mock_pipeline_result()
        runner = MagicMock()

        await probe_timeseries_impl(
            file_path="/data/case_0000.vtk",
            field_name="p",
            point=[0.0, 0.0, 0.0],
            runner=runner,
            files=["/data/case_0000.vtk", "/data/case_0001.vtk"],
            file_pattern="case_*.vtk",
        )

        pipeline_def = mock_exec.call_args[0][0]
        assert pipeline_def.source.files == ["/data/case_0000.vtk", "/data/case_0001.vtk"]
        assert pipeline_def.source.file_pattern == "case_*.vtk"


class TestBatchRenderImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.batch.cinematic_render")
    @patch("viznoir.tools.batch.read_dataset")
    async def test_batch_render_basic(self, mock_read, mock_cine):
        from viznoir.tools.batch import batch_render_impl

        mock_read.return_value = MagicMock()
        mock_cine.return_value = b"\x89PNG\r\n\x1a\nfake"
        runner = MagicMock()

        result = await batch_render_impl(
            file_path="/data/case.vtk",
            fields=["pressure", "velocity"],
            runner=runner,
        )

        assert result["count"] == 2
        assert len(result["images"]) == 2
        assert result["fields"] == ["pressure", "velocity"]
        for img in result["images"]:
            assert "base64" in img
            assert "field" in img
            assert img["size_bytes"] > 0

    @pytest.mark.asyncio
    @patch("viznoir.tools.batch.cinematic_render")
    @patch("viznoir.tools.batch.read_dataset")
    @patch("viznoir.tools.batch.get_timesteps")
    async def test_batch_render_latest_timestep(self, mock_ts, mock_read, mock_cine):
        from viznoir.tools.batch import batch_render_impl

        mock_ts.return_value = [0.0, 1.0, 2.0]
        mock_read.return_value = MagicMock()
        mock_cine.return_value = b"\x89PNG\r\n\x1a\nfake"
        runner = MagicMock()

        result = await batch_render_impl(
            file_path="/data/case.vtk",
            fields=["pressure"],
            runner=runner,
            timestep="latest",
        )

        assert result["count"] == 1
        mock_ts.assert_called_with("/data/case.vtk")
        mock_read.assert_called_with("/data/case.vtk", timestep=2.0)

    @pytest.mark.asyncio
    @patch("viznoir.tools.batch.cinematic_render")
    @patch("viznoir.tools.batch.read_dataset")
    async def test_batch_render_string_timestep(self, mock_read, mock_cine):
        from viznoir.tools.batch import batch_render_impl

        mock_read.return_value = MagicMock()
        mock_cine.return_value = b"\x89PNG\r\n\x1a\nfake"
        runner = MagicMock()

        result = await batch_render_impl(
            file_path="/data/case.vtk",
            fields=["temperature"],
            runner=runner,
            timestep="1.5",
        )

        assert result["count"] == 1
        mock_read.assert_called_with("/data/case.vtk", timestep=1.5)
