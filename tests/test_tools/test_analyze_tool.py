"""Tests for analyze_data MCP tool."""

from __future__ import annotations

import vtk


class TestAnalyzeDataImpl:
    async def test_analyze_impl_returns_report(self, tmp_path):
        """analyze_data_impl should return a report dict for a valid VTK file."""
        from viznoir.tools.analyze import analyze_data_impl

        # Create a VTK file
        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(-4, 4, -4, 4, -4, 4)
        src.Update()

        writer = vtk.vtkXMLImageDataWriter()
        path = str(tmp_path / "test.vti")
        writer.SetFileName(path)
        writer.SetInputData(src.GetOutput())
        writer.Write()

        from viznoir.core.runner import VTKRunner

        runner = VTKRunner()
        result = await analyze_data_impl(path, runner)

        assert "summary" in result
        assert result["summary"]["num_points"] > 0
        assert len(result["field_analyses"]) >= 1
        assert len(result["suggested_equations"]) >= 1


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

        from viznoir.anim.latex import CAIROSVG_AVAILABLE, LATEX_AVAILABLE, render_latex

        tex = r"E = mc^2"
        # First call — cold
        t0 = time.perf_counter()
        render_latex(tex, color="FFFFFF")
        cold_ms = (time.perf_counter() - t0) * 1000

        # Second call — cached
        t0 = time.perf_counter()
        render_latex(tex, color="FFFFFF")
        warm_ms = (time.perf_counter() - t0) * 1000

        if LATEX_AVAILABLE and CAIROSVG_AVAILABLE:
            # SVG cache: warm should be significantly faster
            assert warm_ms < cold_ms * 0.5 or warm_ms < 30
        else:
            # Matplotlib fallback: no SVG cache, just verify it runs
            assert warm_ms < 5000

    def test_different_colors_different_cache(self):
        from viznoir.anim.latex import render_latex
        img1 = render_latex(r"x^2", color="FFFFFF")
        img2 = render_latex(r"x^2", color="FF0000")
        assert img1.width > 0
        assert img2.width > 0
