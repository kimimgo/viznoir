"""Tests for server.py tool functions via mocking — covers tool-level logic.

Each test mocks the underlying tool impl to avoid VTK dependency,
verifying that server.py correctly delegates args and handles results.

FastMCP @mcp.tool() wraps functions into FunctionTool objects.
We access the original async function via .fn attribute.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline_result(image_bytes=b"\x89PNG_test", json_data=None, output_type="image"):
    """Create a mock PipelineResult."""
    r = MagicMock()
    r.image_bytes = image_bytes
    r.json_data = json_data
    r.output_type = output_type
    r.ok = True
    return r


def _get_tool_fn(name: str):
    """Get the original async function from a FunctionTool."""
    import viznoir.server as srv
    tool = getattr(srv, name)
    return tool.fn if hasattr(tool, "fn") else tool


@pytest.fixture(autouse=True)
def _unset_data_dir(monkeypatch):
    """Ensure no data dir restriction and bypass file existence check for tests."""
    monkeypatch.delenv("VIZNOIR_DATA_DIR", raising=False)
    monkeypatch.setattr("viznoir.server._validate_file_path", lambda fp: str(fp))


# ---------------------------------------------------------------------------
# inspect_data
# ---------------------------------------------------------------------------


class TestInspectDataTool:
    @pytest.mark.asyncio
    async def test_inspect_data_delegates(self):
        mock_result = {"bounds": [0, 1, 0, 1, 0, 1], "fields": ["p", "U"]}
        with patch("viznoir.tools.inspect.inspect_data_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("inspect_data")
            result = await fn(file_path="/tmp/test.vtk")
            assert result == mock_result


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


class TestRenderTool:
    @pytest.mark.asyncio
    async def test_render_returns_image(self):
        mock_pr = _make_pipeline_result()
        with patch("viznoir.tools.render.render_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("render")
            result = await fn(file_path="/tmp/test.vtk", field_name="p")
            assert result.data == b"\x89PNG_test"

    @pytest.mark.asyncio
    async def test_render_raises_on_no_image(self):
        mock_pr = _make_pipeline_result(image_bytes=None)
        with patch("viznoir.tools.render.render_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("render")
            with pytest.raises(RuntimeError, match="Rendering failed"):
                await fn(file_path="/tmp/test.vtk", field_name="p")

    @pytest.mark.asyncio
    async def test_render_passes_all_params(self):
        mock_pr = _make_pipeline_result()
        mock_impl = AsyncMock(return_value=mock_pr)
        with patch("viznoir.tools.render.render_impl", mock_impl):
            fn = _get_tool_fn("render")
            await fn(
                file_path="/tmp/test.vtk", field_name="p",
                association="CELLS", colormap="Viridis", camera="top",
                scalar_range=[0.0, 1.0], width=800, height=600,
                timestep="latest", blocks=["wall"],
                output_filename="out.png",
            )
            _, kwargs = mock_impl.call_args
            assert kwargs["association"] == "CELLS"
            assert kwargs["colormap"] == "Viridis"
            assert kwargs["camera"] == "top"
            assert kwargs["width"] == 800


# ---------------------------------------------------------------------------
# slice
# ---------------------------------------------------------------------------


class TestSliceTool:
    @pytest.mark.asyncio
    async def test_slice_returns_image(self):
        mock_pr = _make_pipeline_result()
        with patch("viznoir.tools.filters.slice_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("slice")
            result = await fn(file_path="/tmp/test.vtk", field_name="p")
            assert result.data == b"\x89PNG_test"

    @pytest.mark.asyncio
    async def test_slice_raises_on_no_image(self):
        mock_pr = _make_pipeline_result(image_bytes=None)
        with patch("viznoir.tools.filters.slice_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("slice")
            with pytest.raises(RuntimeError, match="Slice rendering failed"):
                await fn(file_path="/tmp/test.vtk", field_name="p")


# ---------------------------------------------------------------------------
# contour
# ---------------------------------------------------------------------------


class TestContourTool:
    @pytest.mark.asyncio
    async def test_contour_returns_image(self):
        mock_pr = _make_pipeline_result()
        with patch("viznoir.tools.filters.contour_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("contour")
            result = await fn(file_path="/tmp/test.vtk", field_name="p", isovalues=[0.5])
            assert result.data == b"\x89PNG_test"

    @pytest.mark.asyncio
    async def test_contour_raises_on_no_image(self):
        mock_pr = _make_pipeline_result(image_bytes=None)
        with patch("viznoir.tools.filters.contour_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("contour")
            with pytest.raises(RuntimeError, match="Contour rendering failed"):
                await fn(file_path="/tmp/test.vtk", field_name="p", isovalues=[0.5])


# ---------------------------------------------------------------------------
# clip
# ---------------------------------------------------------------------------


class TestClipTool:
    @pytest.mark.asyncio
    async def test_clip_returns_image(self):
        mock_pr = _make_pipeline_result()
        with patch("viznoir.tools.filters.clip_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("clip")
            result = await fn(file_path="/tmp/test.vtk", field_name="p")
            assert result.data == b"\x89PNG_test"

    @pytest.mark.asyncio
    async def test_clip_raises_on_no_image(self):
        mock_pr = _make_pipeline_result(image_bytes=None)
        with patch("viznoir.tools.filters.clip_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("clip")
            with pytest.raises(RuntimeError, match="Clip rendering failed"):
                await fn(file_path="/tmp/test.vtk", field_name="p")


# ---------------------------------------------------------------------------
# streamlines
# ---------------------------------------------------------------------------


class TestStreamlinesTool:
    @pytest.mark.asyncio
    async def test_streamlines_returns_image(self):
        mock_pr = _make_pipeline_result()
        with patch("viznoir.tools.filters.streamlines_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("streamlines")
            result = await fn(file_path="/tmp/test.vtk", vector_field="U")
            assert result.data == b"\x89PNG_test"

    @pytest.mark.asyncio
    async def test_streamlines_raises_on_no_image(self):
        mock_pr = _make_pipeline_result(image_bytes=None)
        with patch("viznoir.tools.filters.streamlines_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("streamlines")
            with pytest.raises(RuntimeError, match="Streamline rendering failed"):
                await fn(file_path="/tmp/test.vtk", vector_field="U")


# ---------------------------------------------------------------------------
# extract_stats
# ---------------------------------------------------------------------------


class TestExtractStatsTool:
    @pytest.mark.asyncio
    async def test_extract_stats_delegates(self):
        mock_result = {"p": {"min": 0.0, "max": 1.0, "mean": 0.5}}
        with patch("viznoir.tools.extract.extract_stats_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("extract_stats")
            result = await fn(file_path="/tmp/test.vtk", fields=["p"])
            assert result["p"]["min"] == 0.0


# ---------------------------------------------------------------------------
# plot_over_line
# ---------------------------------------------------------------------------


class TestPlotOverLineTool:
    @pytest.mark.asyncio
    async def test_plot_over_line_delegates(self):
        mock_result = {"distance": [0, 1, 2], "p": [1.0, 0.5, 0.0]}
        with patch("viznoir.tools.extract.plot_over_line_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("plot_over_line")
            result = await fn(
                file_path="/tmp/test.vtk", field_name="p",
                point1=[0, 0, 0], point2=[1, 0, 0],
            )
            assert result["distance"] == [0, 1, 2]


# ---------------------------------------------------------------------------
# integrate_surface
# ---------------------------------------------------------------------------


class TestIntegrateSurfaceTool:
    @pytest.mark.asyncio
    async def test_integrate_surface_delegates(self):
        mock_result = {"integral": 42.0, "area": 10.0}
        with patch("viznoir.tools.extract.integrate_surface_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("integrate_surface")
            result = await fn(file_path="/tmp/test.vtk", field_name="p")
            assert result["integral"] == 42.0


# ---------------------------------------------------------------------------
# animate
# ---------------------------------------------------------------------------


class TestAnimateTool:
    @pytest.mark.asyncio
    async def test_animate_returns_json(self):
        mock_pr = _make_pipeline_result(
            image_bytes=None, json_data={"frames": 10, "output": "/output/anim"},
            output_type="animation",
        )
        with patch("viznoir.tools.animate.animate_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("animate")
            result = await fn(file_path="/tmp/test.vtk", field_name="p")
            assert result["frames"] == 10

    @pytest.mark.asyncio
    async def test_animate_fallback_on_none_json(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data=None, output_type="animation")
        with patch("viznoir.tools.animate.animate_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("animate")
            result = await fn(file_path="/tmp/test.vtk", field_name="p")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_animate_validates_files_list(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data={"frames": 3}, output_type="animation")
        with patch("viznoir.tools.animate.animate_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("animate")
            result = await fn(
                file_path="/tmp/test.vtk", field_name="p",
                files=["/tmp/f1.vtk", "/tmp/f2.vtk"],
            )
            assert result["frames"] == 3


# ---------------------------------------------------------------------------
# split_animate
# ---------------------------------------------------------------------------


class TestSplitAnimateTool:
    @pytest.mark.asyncio
    async def test_split_animate_gif(self):
        mock_pr = _make_pipeline_result(image_bytes=b"GIF89a_test")
        with patch("viznoir.tools.split_animate.split_animate_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("split_animate")
            panes = [{"type": "render", "row": 0, "col": 0}]
            result = await fn(file_path="/tmp/test.vtk", panes=panes, gif=True)
            assert result.data == b"GIF89a_test"

    @pytest.mark.asyncio
    async def test_split_animate_no_gif(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data={"frames": 5})
        with patch("viznoir.tools.split_animate.split_animate_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("split_animate")
            panes = [{"type": "render", "row": 0, "col": 0}]
            result = await fn(file_path="/tmp/test.vtk", panes=panes, gif=False)
            assert result["frames"] == 5

    @pytest.mark.asyncio
    async def test_split_animate_no_gif_fallback(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data=None)
        with patch("viznoir.tools.split_animate.split_animate_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("split_animate")
            panes = [{"type": "render", "row": 0, "col": 0}]
            result = await fn(file_path="/tmp/test.vtk", panes=panes, gif=False)
            assert "error" in result


# ---------------------------------------------------------------------------
# execute_pipeline
# ---------------------------------------------------------------------------


class TestExecutePipelineTool:
    @pytest.mark.asyncio
    async def test_pipeline_image_output(self):
        mock_pr = _make_pipeline_result(output_type="image")
        with patch("viznoir.tools.pipeline.execute_pipeline_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("execute_pipeline")
            result = await fn(pipeline={
                "source": {"file": "/tmp/test.vtk"},
                "output": {"type": "image"},
            })
            assert result.data == b"\x89PNG_test"

    @pytest.mark.asyncio
    async def test_pipeline_data_output(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data={"stats": "ok"}, output_type="data")
        with patch("viznoir.tools.pipeline.execute_pipeline_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("execute_pipeline")
            result = await fn(pipeline={"source": {"file": "/tmp/test.vtk"}})
            assert result["stats"] == "ok"

    @pytest.mark.asyncio
    async def test_pipeline_no_source_file(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data={"ok": True}, output_type="data")
        with patch("viznoir.tools.pipeline.execute_pipeline_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("execute_pipeline")
            result = await fn(pipeline={"output": {"type": "data"}})
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_pipeline_fallback_json(self):
        mock_pr = _make_pipeline_result(image_bytes=None, json_data=None, output_type="data")
        with patch("viznoir.tools.pipeline.execute_pipeline_impl", new_callable=AsyncMock, return_value=mock_pr):
            fn = _get_tool_fn("execute_pipeline")
            result = await fn(pipeline={"output": {"type": "data"}})
            assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# cinematic_render
# ---------------------------------------------------------------------------


class TestCinematicRenderTool:
    @pytest.mark.asyncio
    async def test_cinematic_returns_image(self):
        mock = AsyncMock(return_value=b"\x89PNG_cine")
        with patch("viznoir.tools.cinematic.cinematic_render_impl", mock):
            fn = _get_tool_fn("cinematic_render")
            result = await fn(file_path="/tmp/test.vtk")
            assert result.data == b"\x89PNG_cine"

    @pytest.mark.asyncio
    async def test_cinematic_raises_on_none(self):
        with patch("viznoir.tools.cinematic.cinematic_render_impl", new_callable=AsyncMock, return_value=None):
            fn = _get_tool_fn("cinematic_render")
            with pytest.raises(RuntimeError, match="Cinematic rendering failed"):
                await fn(file_path="/tmp/test.vtk")

    @pytest.mark.asyncio
    async def test_cinematic_all_params(self):
        mock_impl = AsyncMock(return_value=b"\x89PNG")
        with patch("viznoir.tools.cinematic.cinematic_render_impl", mock_impl):
            fn = _get_tool_fn("cinematic_render")
            await fn(
                file_path="/tmp/test.vtk", field_name="T",
                colormap="Inferno", quality="cinematic",
                lighting="dramatic", background="dark_gradient",
                azimuth=45.0, elevation=30.0, fill_ratio=0.8,
                metallic=0.5, roughness=0.3, ground_plane=True,
                ssao=True, fxaa=True, width=3840, height=2160,
                scalar_range=[0.0, 500.0], timestep="latest",
                output_filename="thermal.png",
            )
            _, kwargs = mock_impl.call_args
            assert kwargs["quality"] == "cinematic"
            assert kwargs["lighting"] == "dramatic"
            assert kwargs["width"] == 3840


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


class TestCompareTool:
    @pytest.mark.asyncio
    async def test_compare_returns_image(self):
        with patch("viznoir.tools.compare.compare_impl", new_callable=AsyncMock, return_value=b"\x89PNG_cmp"):
            fn = _get_tool_fn("compare")
            result = await fn(file_a="/tmp/a.vtk", file_b="/tmp/b.vtk")
            assert result.data == b"\x89PNG_cmp"

    @pytest.mark.asyncio
    async def test_compare_raises_on_none(self):
        with patch("viznoir.tools.compare.compare_impl", new_callable=AsyncMock, return_value=None):
            fn = _get_tool_fn("compare")
            with pytest.raises(RuntimeError, match="Compare failed"):
                await fn(file_a="/tmp/a.vtk", file_b="/tmp/b.vtk")

    @pytest.mark.asyncio
    async def test_compare_diff_mode(self):
        mock_impl = AsyncMock(return_value=b"\x89PNG_diff")
        with patch("viznoir.tools.compare.compare_impl", mock_impl):
            fn = _get_tool_fn("compare")
            await fn(file_a="/tmp/a.vtk", file_b="/tmp/b.vtk", mode="diff", field_name="p")
            _, kwargs = mock_impl.call_args
            assert kwargs["mode"] == "diff"
            assert kwargs["field_name"] == "p"


# ---------------------------------------------------------------------------
# probe_timeseries
# ---------------------------------------------------------------------------


class TestProbeTimeseriesTool:
    @pytest.mark.asyncio
    async def test_probe_delegates(self):
        mock_result = {"times": [0, 1], "values": [100.0, 200.0]}
        with patch("viznoir.tools.probe.probe_timeseries_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("probe_timeseries")
            result = await fn(
                file_path="/tmp/test.vtk", field_name="p", point=[0, 0, 0],
            )
            assert result["values"] == [100.0, 200.0]


# ---------------------------------------------------------------------------
# batch_render
# ---------------------------------------------------------------------------


class TestBatchRenderTool:
    @pytest.mark.asyncio
    async def test_batch_render_delegates(self):
        mock_result = {"count": 2, "images": [{"field": "p"}, {"field": "U"}]}
        with patch("viznoir.tools.batch.batch_render_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("batch_render")
            result = await fn(file_path="/tmp/test.vtk", fields=["p", "U"])
            assert result["count"] == 2


# ---------------------------------------------------------------------------
# preview_3d
# ---------------------------------------------------------------------------


class TestPreview3dTool:
    @pytest.mark.asyncio
    async def test_preview_3d_delegates(self):
        mock_result = {"file": "/output/preview.glb", "format": "glb"}
        with patch("viznoir.tools.preview3d.preview_3d_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("preview_3d")
            result = await fn(file_path="/tmp/test.vtk")
            assert result["format"] == "glb"


# ---------------------------------------------------------------------------
# pv_isosurface
# ---------------------------------------------------------------------------


class TestPvIsosurfaceTool:
    @pytest.mark.asyncio
    async def test_pv_isosurface_delegates(self):
        mock_result = {"files": ["/output/iso_0000.vtk"], "count": 1}
        with patch("viznoir.tools.isosurface.pv_isosurface_impl", new_callable=AsyncMock, return_value=mock_result):
            fn = _get_tool_fn("pv_isosurface")
            result = await fn(bi4_dir="/data/bi4", output_dir="/output/iso")
            assert result["count"] == 1


# ---------------------------------------------------------------------------
# _validate_file_path edge cases
# ---------------------------------------------------------------------------


class TestValidateFilePathSuggestions:
    def test_nonexistent_file_with_similar_siblings(self, tmp_path):
        """When file doesn't exist but similar files do, log suggests them."""
        (tmp_path / "cavity.vtk").touch()
        (tmp_path / "cavity.vtu").touch()
        from viznoir.server import _validate_file_path
        result = _validate_file_path(str(tmp_path / "caviti.vtk"))
        assert "caviti.vtk" in result

    def test_nonexistent_file_no_siblings(self, tmp_path):
        """When parent dir has no similar files, no crash."""
        from viznoir.server import _validate_file_path
        result = _validate_file_path(str(tmp_path / "nonexistent.vtk"))
        assert "nonexistent.vtk" in result


# ---------------------------------------------------------------------------
# _register_resources / _register_prompts
# ---------------------------------------------------------------------------


class TestRegistrations:
    def test_register_resources(self):
        from viznoir.server import _register_resources
        with patch("viznoir.resources.catalog.register_resources") as mock_reg:
            _register_resources()
            mock_reg.assert_called_once()

    def test_register_prompts(self):
        from viznoir.server import _register_prompts
        with patch("viznoir.prompts.guides.register_prompts") as mock_reg:
            _register_prompts()
            mock_reg.assert_called_once()


# ---------------------------------------------------------------------------
# _protect_stdout
# ---------------------------------------------------------------------------


class TestProtectStdout:
    def test_protect_stdout_redirects_fd1(self):
        """_protect_stdout redirects fd 1 and wraps sys.stdout."""
        import io
        import sys

        from viznoir.server import _protect_stdout

        original_stdout = sys.stdout

        _protect_stdout()

        # sys.stdout should now be a TextIOWrapper on a saved fd
        assert isinstance(sys.stdout, io.TextIOWrapper)
        # Writing should still work
        sys.stdout.write("test\n")
        sys.stdout.flush()

        # Restore for other tests
        sys.stdout = original_stdout


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_stdio(self):
        """main() with stdio transport calls mcp.run()."""
        with patch("sys.argv", ["mcp-server-viznoir"]), \
             patch("viznoir.server._protect_stdout"), \
             patch("viznoir.server._register_resources"), \
             patch("viznoir.server._register_prompts"), \
             patch("viznoir.server.mcp") as mock_mcp, \
             patch("viznoir.server.VTKRunner") as mock_runner_cls:
            mock_runner_cls.cleanup_orphaned_containers = AsyncMock(return_value=0)
            from viznoir.server import main
            main()
            mock_mcp.run.assert_called_once_with()

    def test_main_sse(self):
        """main() with sse transport passes host/port."""
        with patch("sys.argv", ["mcp-server-viznoir", "--transport", "sse", "--port", "9000"]), \
             patch("viznoir.server._protect_stdout"), \
             patch("viznoir.server._register_resources"), \
             patch("viznoir.server._register_prompts"), \
             patch("viznoir.server.mcp") as mock_mcp, \
             patch("viznoir.server.VTKRunner") as mock_runner_cls:
            mock_runner_cls.cleanup_orphaned_containers = AsyncMock(return_value=0)
            from viznoir.server import main
            main()
            mock_mcp.run.assert_called_once_with(
                transport="sse", host="0.0.0.0", port=9000
            )

    def test_main_streamable_http(self):
        """main() with streamable-http transport."""
        with patch(
            "sys.argv",
            ["mcp-server-viznoir", "--transport", "streamable-http"],
        ), \
             patch("viznoir.server._protect_stdout"), \
             patch("viznoir.server._register_resources"), \
             patch("viznoir.server._register_prompts"), \
             patch("viznoir.server.mcp") as mock_mcp, \
             patch("viznoir.server.VTKRunner") as mock_runner_cls:
            mock_runner_cls.cleanup_orphaned_containers = AsyncMock(return_value=0)
            from viznoir.server import main
            main()
            mock_mcp.run.assert_called_once_with(
                transport="streamable-http", host="0.0.0.0", port=8000
            )

    def test_main_cleanup_logs_removed(self):
        """main() logs when orphaned containers are removed (line 979)."""
        import viznoir.server as srv_mod
        with patch("sys.argv", ["mcp-server-viznoir"]), \
             patch("viznoir.server._protect_stdout"), \
             patch("viznoir.server._register_resources"), \
             patch("viznoir.server._register_prompts"), \
             patch("viznoir.server.mcp"), \
             patch("viznoir.core.runner.VTKRunner") as mock_runner_cls, \
             patch.object(srv_mod, "logger") as mock_logger:
            mock_runner_cls.cleanup_orphaned_containers = AsyncMock(return_value=3)
            srv_mod.main()
            mock_logger.info.assert_any_call(
                "cleaned up %d orphaned container(s)", 3
            )

    def test_main_cleanup_runtime_error(self):
        """main() handles RuntimeError from event loop (lines 980-982)."""
        import asyncio as real_asyncio
        with patch("sys.argv", ["mcp-server-viznoir"]), \
             patch("viznoir.server._protect_stdout"), \
             patch("viznoir.server._register_resources"), \
             patch("viznoir.server._register_prompts"), \
             patch("viznoir.server.mcp"), \
             patch.object(real_asyncio, "new_event_loop", side_effect=RuntimeError("no event loop")):
            from viznoir.server import main
            main()  # Should not raise


