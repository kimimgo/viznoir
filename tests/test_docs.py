"""Tests for the tool-reference generator + doc drift guards (#68).

The generated reference must cover every live MCP tool, so docs can't silently
drift from code.
"""

from __future__ import annotations

import asyncio
import importlib.util
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "gen_tool_reference.py"
_REF = _ROOT / "docs" / "tools" / "reference.md"

_spec = importlib.util.spec_from_file_location("gen_tool_reference", _SCRIPT)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


class TestRenderMarkdown:
    def test_structure(self):
        md = gen.render_markdown(
            [
                {
                    "name": "foo",
                    "description": "does foo",
                    "params": [
                        {"name": "x", "type": "string", "required": True, "description": "the x"},
                        {"name": "n", "type": "integer", "required": False, "default": 3, "description": ""},
                    ],
                }
            ]
        )
        assert "`foo`" in md
        assert "does foo" in md
        assert "x" in md and "string" in md
        assert "n" in md  # optional param listed too

    def test_empty_params_ok(self):
        md = gen.render_markdown([{"name": "bar", "description": "no args", "params": []}])
        assert "`bar`" in md


class TestDrift:
    def test_reference_covers_all_live_tools(self):
        tools = asyncio.run(gen.collect_tools())
        assert len(tools) >= 24, f"expected >=24 tools, got {len(tools)}"
        assert _REF.is_file(), "docs/tools/reference.md must be committed"
        ref = _REF.read_text()
        missing = [t["name"] for t in tools if f"`{t['name']}`" not in ref]
        assert not missing, f"reference.md is stale — missing tools: {missing}"

    def test_migration_guide_exists(self):
        mg = _ROOT / "docs" / "migration-0.x-to-1.0.md"
        assert mg.is_file(), "migration guide must exist"
        assert "1.0" in mg.read_text()

    def test_domain_gallery_exists(self):
        gal = _ROOT / "docs" / "gallery.md"
        text = gal.read_text() if gal.is_file() else ""
        assert gal.is_file(), "domain gallery must exist"
        for domain in ("CFD", "FEA", "Medical"):
            assert domain in text, f"gallery missing domain: {domain}"
