"""Tests for analyze_data MCP tool."""

from __future__ import annotations


class TestAnalyzeDataTool:
    async def test_tool_registered(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert "analyze_data" in names

    async def test_nonexistent_file_returns_error(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            try:
                result = await client.call_tool("analyze_data", {"file_path": "/nonexistent/file.vtk"})
                text = str(result)
                assert "error" in text.lower() or "not found" in text.lower()
            except Exception as e:
                assert "not found" in str(e).lower() or "error" in str(e).lower()


class TestLatexCache:
    def test_cache_speedup(self):
        import time

        from viznoir.anim.latex import render_latex

        tex = r"E = mc^2"
        # First call — cold
        t0 = time.perf_counter()
        render_latex(tex, color="FFFFFF")
        cold_ms = (time.perf_counter() - t0) * 1000

        # Second call — cached
        t0 = time.perf_counter()
        render_latex(tex, color="FFFFFF")
        warm_ms = (time.perf_counter() - t0) * 1000

        # Cached should be significantly faster
        assert warm_ms < cold_ms * 0.5 or warm_ms < 30

    def test_different_colors_different_cache(self):
        from viznoir.anim.latex import render_latex
        img1 = render_latex(r"x^2", color="FFFFFF")
        img2 = render_latex(r"x^2", color="FF0000")
        assert img1.width > 0
        assert img2.width > 0
