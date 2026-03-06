"""In-memory MCP integration tests using FastMCP Client.

Tests the server at the MCP protocol level — verifying tool listing,
resource reading, and prompt retrieval work correctly through the
actual MCP message flow (no HTTP, no subprocess).
"""

from __future__ import annotations

import json

from parapilot.server import mcp

# Resources and prompts are now registered at module import time in server.py,
# so no explicit registration is needed here.


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------


class TestMCPToolListing:
    """Verify all tools are discoverable via MCP protocol."""

    async def test_list_tools_returns_18(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            tools = await client.list_tools()
            assert len(tools) == 18

    async def test_all_tool_names_present(self):
        from fastmcp import Client

        expected_names = {
            "inspect_data", "render", "slice", "contour", "clip",
            "streamlines", "cinematic_render", "compare",
            "probe_timeseries", "batch_render", "preview_3d",
            "extract_stats", "plot_over_line", "integrate_surface",
            "animate", "split_animate", "execute_pipeline", "pv_isosurface",
        }
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert expected_names == tool_names

    async def test_tools_have_descriptions(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            tools = await client.list_tools()
            for tool in tools:
                assert tool.description, f"Tool {tool.name} has no description"

    async def test_tools_have_input_schema(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            tools = await client.list_tools()
            for tool in tools:
                assert tool.inputSchema, f"Tool {tool.name} has no input schema"
                props = tool.inputSchema.get("properties", {})
                assert len(props) > 0, f"Tool {tool.name} has empty properties"


# ---------------------------------------------------------------------------
# Resource listing and reading
# ---------------------------------------------------------------------------


class TestMCPResources:
    """Verify resources are readable via MCP protocol."""

    async def test_list_resources_returns_expected(self):
        from fastmcp import Client

        expected_uris = {
            "parapilot://formats",
            "parapilot://filters",
            "parapilot://colormaps",
            "parapilot://representations",
            "parapilot://case-presets",
            "parapilot://cameras",
            "parapilot://cinematic",
            "parapilot://pipelines/cfd",
            "parapilot://pipelines/fea",
            "parapilot://pipelines/split-animate",
            "parapilot://physics-defaults",
        }
        async with Client(mcp) as client:
            resources = await client.list_resources()
            uris = {str(r.uri) for r in resources}
            assert expected_uris.issubset(uris), f"Missing: {expected_uris - uris}"

    async def test_read_formats_resource(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            result = await client.read_resource("parapilot://formats")
            # Result is a list of content items
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            assert isinstance(data, dict)
            assert ".vtk" in data or ".vtu" in data

    async def test_read_colormaps_resource(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            result = await client.read_resource("parapilot://colormaps")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            assert "colormaps" in data
            assert "field_recommendations" in data
            assert len(data["colormaps"]) >= 16

    async def test_read_cameras_resource(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            result = await client.read_resource("parapilot://cameras")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            assert "presets" in data
            assert "isometric" in data["presets"]

    async def test_read_physics_defaults_resource(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            result = await client.read_resource("parapilot://physics-defaults")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            assert "_usage" in data


# ---------------------------------------------------------------------------
# Prompt listing
# ---------------------------------------------------------------------------


class TestMCPPrompts:
    """Verify prompts are accessible via MCP protocol."""

    async def test_list_prompts(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            prompts = await client.list_prompts()
            assert len(prompts) >= 3
            prompt_names = {p.name for p in prompts}
            expected = {"cfd_postprocess", "fea_postprocess", "visualization_guide"}
            assert expected.issubset(prompt_names), f"Missing: {expected - prompt_names}"

    async def test_get_cfd_postprocess_prompt(self):
        from fastmcp import Client

        async with Client(mcp) as client:
            result = await client.get_prompt("cfd_postprocess")
            assert result.messages
            content = str(result.messages[0].content)
            assert len(content) > 50  # Should have substantial content


# ---------------------------------------------------------------------------
# Tool call (with mock)
# ---------------------------------------------------------------------------


class TestMCPToolCall:
    """Verify tool calls work through MCP protocol."""

    async def test_inspect_data_returns_error_for_nonexistent_file(self):
        """Calling inspect_data with a non-existent file should return an error."""
        from fastmcp import Client

        async with Client(mcp) as client:
            # FastMCP may raise or return error content
            try:
                result = await client.call_tool(
                    "inspect_data",
                    {"file_path": "/nonexistent/file.vtk"},
                )
                text = str(result)
                assert "error" in text.lower() or "not found" in text.lower() or "File not found" in text
            except Exception as e:
                # Exception is acceptable — server correctly rejected bad input
                assert "not found" in str(e).lower() or "File not found" in str(e)


# ---------------------------------------------------------------------------
# MCP Tasks support (FastMCP >= 3.0)
# ---------------------------------------------------------------------------


class TestMCPTasksSupport:
    """Verify MCP Tasks feature detection and tool registration."""

    def test_tasks_available_flag(self):
        """_TASKS_AVAILABLE reflects FastMCP version."""
        from parapilot.server import _TASKS_AVAILABLE, _has_mcp_tasks

        assert _TASKS_AVAILABLE == _has_mcp_tasks()

    def test_has_mcp_tasks_returns_bool(self):
        """_has_mcp_tasks always returns a boolean."""
        from parapilot.server import _has_mcp_tasks

        result = _has_mcp_tasks()
        assert isinstance(result, bool)

    def test_long_running_tools_registered(self):
        """animate, split_animate, execute_pipeline should be registered tools."""
        from fastmcp import Client

        async def _check():
            async with Client(mcp) as client:
                tools = await client.list_tools()
                names = {t.name for t in tools}
                assert "animate" in names
                assert "split_animate" in names
                assert "execute_pipeline" in names

        import asyncio
        asyncio.run(_check())

    def test_has_mcp_tasks_with_mock_old_version(self):
        """Simulating FastMCP 2.x should return False."""
        from unittest.mock import patch

        from parapilot.server import _has_mcp_tasks

        with patch("importlib.metadata.version", return_value="2.14.5"):
            result = _has_mcp_tasks()
            assert result is False

    def test_has_mcp_tasks_with_mock_new_version(self):
        """Simulating FastMCP 3.x should return True."""
        from unittest.mock import patch

        from parapilot.server import _has_mcp_tasks

        with patch("importlib.metadata.version", return_value="3.1.0"):
            result = _has_mcp_tasks()
            assert result is True

    def test_has_mcp_tasks_handles_import_error(self):
        """Missing packaging should return False gracefully."""
        from unittest.mock import patch

        from parapilot.server import _has_mcp_tasks

        with patch("importlib.metadata.version", side_effect=Exception("no package")):
            result = _has_mcp_tasks()
            assert result is False
