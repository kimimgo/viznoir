"""Tests for server tool/resource/prompt registration counts."""

from __future__ import annotations


class TestServerRegistration:
    def test_mcp_instance_exists(self):
        from viznoir.server import mcp
        assert mcp is not None
        assert mcp.name == "viznoir"

    def test_tool_count(self):
        """Verify all expected tools are registered."""

        # Check expected tool functions exist in server module
        from viznoir import server

        tool_funcs = [
            "inspect_data", "render", "slice", "contour", "clip",
            "streamlines", "extract_stats", "plot_over_line",
            "integrate_surface", "animate", "split_animate",
            "execute_pipeline", "pv_isosurface",
            "cinematic_render", "compare",
            "probe_timeseries", "batch_render", "preview_3d",
        ]
        for name in tool_funcs:
            assert hasattr(server, name), f"Missing tool function: {name}"

    def test_validate_file_path_helper(self):
        from viznoir.server import _validate_file_path
        assert callable(_validate_file_path)

    def test_runner_and_config_exist(self):
        from viznoir.server import _config, _runner
        assert _config is not None
        assert _runner is not None

    def test_register_resources_function(self):
        from viznoir.server import _register_resources
        assert callable(_register_resources)

    def test_register_prompts_function(self):
        from viznoir.server import _register_prompts
        assert callable(_register_prompts)

    def test_instructions_mention_key_tools(self):
        from viznoir.server import mcp
        instr = mcp.instructions or ""
        for keyword in ["inspect_data", "render", "slice", "animate", "cinematic_render", "compare"]:
            assert keyword in instr, f"Instructions missing mention of {keyword}"
