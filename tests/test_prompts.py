"""Tests for prompts/guides.py — MCP prompt registration."""

from __future__ import annotations

from unittest.mock import MagicMock

from viznoir.prompts import guides as _guides_mod


class TestPromptRegistration:
    def test_register_creates_prompts(self):
        mcp = MagicMock()
        # Make @mcp.prompt() return the function unchanged
        mcp.prompt.return_value = lambda fn: fn
        _guides_mod._registered_instances.discard(id(mcp))
        _guides_mod.register_prompts(mcp)
        assert mcp.prompt.call_count == 4  # cfd, fea, visualization, story_planning


class TestCFDGuide:
    def _get_cfd_prompt(self):
        mcp = MagicMock()
        captured = {}

        def prompt_decorator():
            def wrapper(fn):
                captured[fn.__name__] = fn
                return fn
            return wrapper

        mcp.prompt = prompt_decorator
        _guides_mod._registered_instances.discard(id(mcp))
        _guides_mod.register_prompts(mcp)
        return captured.get("cfd_postprocess")

    def test_general(self):
        fn = self._get_cfd_prompt()
        result = fn()
        assert "CFD" in result
        assert "inspect_data" in result

    def test_external_aero(self):
        fn = self._get_cfd_prompt()
        result = fn("external_aero")
        assert "Aerodynamics" in result

    def test_internal_flow(self):
        fn = self._get_cfd_prompt()
        result = fn("internal_flow")
        assert "Internal Flow" in result

    def test_multiphase(self):
        fn = self._get_cfd_prompt()
        result = fn("multiphase")
        assert "Multiphase" in result

    def test_thermal(self):
        fn = self._get_cfd_prompt()
        result = fn("thermal")
        assert "Thermal" in result

    def test_unknown_returns_general(self):
        fn = self._get_cfd_prompt()
        result = fn("unknown_type")
        assert "CFD Post-Processing Guide" in result


class TestFEAGuide:
    def _get_fea_prompt(self):
        mcp = MagicMock()
        captured = {}

        def prompt_decorator():
            def wrapper(fn):
                captured[fn.__name__] = fn
                return fn
            return wrapper

        mcp.prompt = prompt_decorator
        _guides_mod._registered_instances.discard(id(mcp))
        _guides_mod.register_prompts(mcp)
        return captured.get("fea_postprocess")

    def test_static(self):
        fn = self._get_fea_prompt()
        result = fn("static")
        assert "Static FEA" in result

    def test_modal(self):
        fn = self._get_fea_prompt()
        result = fn("modal")
        assert "Modal" in result

    def test_default_is_static(self):
        fn = self._get_fea_prompt()
        result = fn()
        assert "Static FEA" in result


class TestVisualizationGuide:
    def _get_viz_prompt(self):
        mcp = MagicMock()
        captured = {}

        def prompt_decorator():
            def wrapper(fn):
                captured[fn.__name__] = fn
                return fn
            return wrapper

        mcp.prompt = prompt_decorator
        _guides_mod._registered_instances.discard(id(mcp))
        _guides_mod.register_prompts(mcp)
        return captured.get("visualization_guide")

    def test_returns_guide(self):
        fn = self._get_viz_prompt()
        result = fn()
        assert "Colormap" in result
        assert "Camera" in result
