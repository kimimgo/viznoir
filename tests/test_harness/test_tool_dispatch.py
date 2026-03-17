"""Tests for TOOL_DISPATCH — verify all image-producing tools are registered."""

from __future__ import annotations

import pytest

from viznoir.harness.registry import TOOL_DISPATCH


class TestToolDispatch:
    """Verify TOOL_DISPATCH covers all visualization tools."""

    EXPECTED_TOOLS = [
        "render",
        "cinematic_render",
        "slice",
        "contour",
        "clip",
        "streamlines",
        "compare",
        "batch_render",
        "volume_render",
    ]

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_registered(self, tool_name):
        assert tool_name in TOOL_DISPATCH, f"{tool_name} missing from TOOL_DISPATCH"

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_is_callable(self, tool_name):
        assert callable(TOOL_DISPATCH[tool_name])

    def test_no_data_only_tools(self):
        """Data extraction tools (extract_stats, plot_over_line) should NOT be in dispatch.
        They don't produce images."""
        assert "extract_stats" not in TOOL_DISPATCH
        assert "plot_over_line" not in TOOL_DISPATCH
        assert "inspect_data" not in TOOL_DISPATCH

    def test_dispatch_keys_are_strings(self):
        for key in TOOL_DISPATCH:
            assert isinstance(key, str)
