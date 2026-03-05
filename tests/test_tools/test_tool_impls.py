"""Tests for tool implementation modules — validate PipelineDefinition construction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from parapilot.core.output import PipelineResult
from parapilot.core.runner import RunResult


def _mock_pipeline_result(**kwargs):
    rr = RunResult(stdout="", stderr="", exit_code=0, json_result={"ok": True})
    return PipelineResult(output_type="data", json_data={"ok": True}, raw=rr, **kwargs)


# ---------------------------------------------------------------------------
# animate_impl
# ---------------------------------------------------------------------------

class TestAnimateImpl:
    @pytest.mark.asyncio
    @patch("parapilot.tools.animate.execute_pipeline")
    async def test_animate_builds_pipeline(self, mock_exec):
        from parapilot.tools.animate import animate_impl

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
    @patch("parapilot.tools.animate.execute_pipeline")
    async def test_animate_time_range(self, mock_exec):
        from parapilot.tools.animate import animate_impl

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
    @patch("parapilot.tools.animate.execute_pipeline")
    async def test_animate_video_output(self, mock_exec):
        from parapilot.tools.animate import animate_impl

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
    @patch("parapilot.tools.animate.execute_pipeline")
    async def test_animate_multi_file(self, mock_exec):
        from parapilot.tools.animate import animate_impl

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
    @patch("parapilot.tools.split_animate.execute_split_animation")
    async def test_split_animate_builds_pipeline(self, mock_exec):
        from parapilot.tools.split_animate import split_animate_impl

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
    @patch("parapilot.tools.split_animate.execute_split_animation")
    async def test_split_animate_with_layout(self, mock_exec):
        from parapilot.tools.split_animate import split_animate_impl

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
    @patch("parapilot.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_success(self, mock_subprocess, tmp_path):
        from parapilot.tools.isosurface import pv_isosurface_impl

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
    @patch("parapilot.tools.isosurface.asyncio.create_subprocess_exec")
    async def test_isosurface_failure(self, mock_subprocess, tmp_path):
        from parapilot.tools.isosurface import pv_isosurface_impl

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"IsoSurface error")
        mock_subprocess.return_value = mock_proc

        with pytest.raises(RuntimeError, match="IsoSurface failed"):
            await pv_isosurface_impl(str(tmp_path), str(tmp_path / "out"))


# ---------------------------------------------------------------------------
# extract impls
# ---------------------------------------------------------------------------

class TestExtractImpls:
    @pytest.mark.asyncio
    @patch("parapilot.tools.extract.execute_pipeline")
    async def test_integrate_surface_with_boundary(self, mock_exec):
        from parapilot.tools.extract import integrate_surface_impl

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
    @patch("parapilot.tools.extract.execute_pipeline")
    async def test_integrate_surface_no_boundary(self, mock_exec):
        from parapilot.tools.extract import integrate_surface_impl

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
    @patch("parapilot.tools.preview3d.export_gltf")
    @patch("parapilot.tools.preview3d.read_dataset")
    async def test_preview_3d_basic(self, mock_read, mock_export, tmp_path):
        from parapilot.tools.preview3d import preview_3d_impl

        mock_read.return_value = MagicMock()
        mock_export.return_value = {
            "path": str(tmp_path / "preview.glb"),
            "format": ".glb",
            "size_bytes": 1024,
        }
        runner = MagicMock()

        import os
        with patch.dict(os.environ, {"PARAPILOT_OUTPUT_DIR": str(tmp_path)}):
            result = await preview_3d_impl(
                file_path="/data/case.vtk",
                runner=runner,
            )

        assert result["format"] == ".glb"
        assert "viewer_hint" in result
        mock_read.assert_called_once()
        mock_export.assert_called_once()

    @pytest.mark.asyncio
    @patch("parapilot.tools.preview3d.get_timesteps")
    @patch("parapilot.tools.preview3d.export_gltf")
    @patch("parapilot.tools.preview3d.read_dataset")
    async def test_preview_3d_latest_timestep(self, mock_read, mock_export, mock_ts, tmp_path):
        from parapilot.tools.preview3d import preview_3d_impl

        mock_ts.return_value = [0.0, 1.0, 2.0]
        mock_read.return_value = MagicMock()
        mock_export.return_value = {"path": "p.glb", "format": ".glb", "size_bytes": 512}
        runner = MagicMock()

        import os
        with patch.dict(os.environ, {"PARAPILOT_OUTPUT_DIR": str(tmp_path)}):
            await preview_3d_impl(
                file_path="/data/case.vtk",
                runner=runner,
                timestep="latest",
            )

        mock_read.assert_called_once_with("/data/case.vtk", timestep=2.0)


# ---------------------------------------------------------------------------
# batch_render_impl
# ---------------------------------------------------------------------------

class TestBatchRenderImpl:
    @pytest.mark.asyncio
    @patch("parapilot.tools.batch.cinematic_render")
    @patch("parapilot.tools.batch.read_dataset")
    async def test_batch_render_basic(self, mock_read, mock_cine):
        from parapilot.tools.batch import batch_render_impl

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
