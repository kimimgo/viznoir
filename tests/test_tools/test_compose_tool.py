"""Tests for compose_assets MCP tool registration and basic operation."""

from __future__ import annotations


class TestComposeAssetsTool:
    async def test_tool_registered(self):
        """compose_assets must be discoverable via FastMCP Client."""
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert "compose_assets" in names

    async def test_tool_has_required_params(self):
        """compose_assets schema must include 'assets' and 'layout' parameters."""
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            compose_tool = next(t for t in tools if t.name == "compose_assets")
            schema = compose_tool.inputSchema
            props = schema.get("properties", {})
            assert "assets" in props
            assert "layout" in props

    async def test_tool_layout_default_is_story(self):
        """Default layout should be 'story'."""
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            compose_tool = next(t for t in tools if t.name == "compose_assets")
            schema = compose_tool.inputSchema
            layout_prop = schema["properties"]["layout"]
            assert layout_prop.get("default") == "story"
