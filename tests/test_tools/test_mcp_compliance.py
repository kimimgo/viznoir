"""MCP protocol compliance tests.

Validates viznoir follows MCP server best practices:
- All tools have descriptions (docstrings)
- All tools have typed parameters
- Resource URIs follow viznoir:// scheme
- Server metadata is correct
- Tool naming conventions are consistent
"""

from __future__ import annotations

import inspect
import re

import pytest


def _get_tool_functions() -> dict:
    """Get the underlying functions from FunctionTool objects."""
    from viznoir import server

    names = [
        "inspect_data", "render", "slice", "contour", "clip",
        "streamlines", "extract_stats", "plot_over_line",
        "integrate_surface", "animate", "split_animate",
        "execute_pipeline", "pv_isosurface",
        "cinematic_render", "compare",
        "probe_timeseries", "batch_render", "preview_3d",
    ]
    tools = {}
    for name in names:
        obj = getattr(server, name)
        # FunctionTool wraps the actual function as .fn
        fn = getattr(obj, "fn", obj)
        tools[name] = fn
    return tools


class TestToolCompliance:
    """Every tool must have a description and typed parameters."""

    def test_all_tools_have_docstrings(self):
        """MCP tools must have docstrings that become descriptions."""
        for name, fn in _get_tool_functions().items():
            doc = fn.__doc__ or ""
            assert len(doc) > 10, f"Tool {name} has no/short docstring"

    def test_all_tools_have_typed_parameters(self):
        """MCP tools must have type annotations for JSON schema generation."""
        for name, fn in _get_tool_functions().items():
            sig = inspect.signature(fn)
            for pname, param in sig.parameters.items():
                if pname in ("self", "ctx"):
                    continue
                assert param.annotation != inspect.Parameter.empty, (
                    f"Tool {name} param '{pname}' has no type annotation"
                )

    def test_all_tools_have_return_annotations(self):
        """MCP tools should have return type annotations."""
        for name, fn in _get_tool_functions().items():
            sig = inspect.signature(fn)
            assert sig.return_annotation != inspect.Signature.empty, (
                f"Tool {name} has no return type annotation"
            )

    def test_tool_names_are_snake_case(self):
        """MCP tool names should be snake_case."""
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for name in _get_tool_functions():
            assert pattern.match(name), f"Tool name '{name}' is not snake_case"

    def test_tool_count_matches_expected(self):
        """Guard against accidentally dropping or adding tools."""
        assert len(_get_tool_functions()) == 18

    def test_docstrings_are_unique(self):
        """No two tools should have the same first-line docstring."""
        seen: dict[str, str] = {}
        for name, fn in _get_tool_functions().items():
            doc = (fn.__doc__ or "").strip()
            first_line = doc.split("\n")[0].strip()
            if first_line in seen:
                pytest.fail(
                    f"Tools '{seen[first_line]}' and '{name}' share docstring: {first_line}"
                )
            seen[first_line] = name


class TestResourceCompliance:
    """Resource URIs must follow viznoir:// scheme."""

    def test_resource_uris_use_correct_scheme(self):
        from viznoir.server import mcp
        instr = mcp.instructions or ""
        uris = re.findall(r"viznoir://[\w/\-]+", instr)
        assert len(uris) >= 5, f"Expected 5+ resource URIs, found {len(uris)}"
        for uri in uris:
            assert uri.startswith("viznoir://"), f"Invalid URI: {uri}"

    def test_core_resources_documented(self):
        from viznoir.server import mcp
        instr = mcp.instructions or ""
        for res in ["viznoir://formats", "viznoir://filters",
                     "viznoir://colormaps", "viznoir://cameras"]:
            assert res in instr, f"Resource {res} not in instructions"


class TestServerMetadata:
    """Server-level MCP metadata compliance."""

    def test_server_name(self):
        from viznoir.server import mcp
        assert mcp.name == "viznoir"

    def test_instructions_present_and_substantial(self):
        from viznoir.server import mcp
        assert mcp.instructions is not None
        assert len(mcp.instructions) > 200

    def test_instructions_describe_workflow(self):
        from viznoir.server import mcp
        instr = mcp.instructions or ""
        assert "inspect_data" in instr
        assert "render" in instr

    def test_instructions_mention_capabilities(self):
        from viznoir.server import mcp
        instr = (mcp.instructions or "").lower()
        for cap in ["cfd", "fea", "cae", "visualization"]:
            assert cap in instr, f"Instructions missing '{cap}'"


class TestSecurityCompliance:
    """Security-related compliance checks."""

    def test_validate_file_path_exists(self):
        from viznoir.server import _validate_file_path
        assert callable(_validate_file_path)

    def test_file_path_param_on_data_tools(self):
        """Tools that read files must accept file_path."""
        data_tools = [
            "inspect_data", "render", "slice", "contour", "clip",
            "streamlines", "animate", "cinematic_render",
        ]
        for name, fn in _get_tool_functions().items():
            if name not in data_tools:
                continue
            sig = inspect.signature(fn)
            assert "file_path" in sig.parameters, (
                f"Data tool {name} missing file_path parameter"
            )
