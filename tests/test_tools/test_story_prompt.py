"""Tests for story_planning prompt and storytelling resource."""

from __future__ import annotations

import json


class TestStoryPlanningPrompt:
    async def test_prompt_registered(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            prompts = await client.list_prompts()
            names = {p.name for p in prompts}
            assert "story_planning" in names

    async def test_prompt_returns_guide(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.get_prompt("story_planning", arguments={"domain": "cfd"})
            text = result.messages[0].content.text
            assert "Science Storytelling Guide" in text
            assert "cfd" in text

    async def test_prompt_default_domain(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.get_prompt("story_planning")
            text = result.messages[0].content.text
            assert "Science Storytelling Guide (cfd)" in text

    async def test_prompt_custom_domain(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.get_prompt("story_planning", arguments={"domain": "fea"})
            text = result.messages[0].content.text
            assert "Science Storytelling Guide (fea)" in text
            assert "fea" in text

    async def test_prompt_contains_narrative_structure(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.get_prompt("story_planning", arguments={"domain": "cfd"})
            text = result.messages[0].content.text
            for section in ["HOOK", "CONTEXT", "EVIDENCE", "EQUATION", "CONCLUSION"]:
                assert section in text, f"Missing narrative section: {section}"

    async def test_prompt_contains_compose_assets_example(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.get_prompt("story_planning", arguments={"domain": "cfd"})
            text = result.messages[0].content.text
            assert "compose_assets" in text

    async def test_prompt_has_description(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            prompts = await client.list_prompts()
            story = next(p for p in prompts if p.name == "story_planning")
            assert story.description
            assert "story" in story.description.lower() or "data-driven" in story.description.lower()


class TestStorytellingResource:
    async def test_resource_registered(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            resources = await client.list_resources()
            uris = {str(r.uri) for r in resources}
            assert "viznoir://storytelling" in uris

    async def test_resource_contains_templates(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.read_resource("viznoir://storytelling")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            assert "scene_templates" in data
            assert "narrative_patterns" in data

    async def test_resource_scene_templates_valid(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.read_resource("viznoir://storytelling")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            templates = data["scene_templates"]
            assert "overview" in templates
            assert "zoom_anomaly" in templates
            assert "cross_section" in templates
            assert "equation_overlay" in templates

    async def test_resource_narrative_patterns_domains(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.read_resource("viznoir://storytelling")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            patterns = data["narrative_patterns"]
            assert "cfd" in patterns
            assert "fea" in patterns
            assert "thermal" in patterns
            # Each pattern should be a list
            for domain, steps in patterns.items():
                assert isinstance(steps, list), f"Pattern for {domain} should be a list"
                assert len(steps) >= 4, f"Pattern for {domain} should have at least 4 steps"

    async def test_resource_annotation_styles(self):
        from fastmcp import Client

        from viznoir.server import mcp

        async with Client(mcp) as client:
            result = await client.read_resource("viznoir://storytelling")
            text = result[0].text if hasattr(result[0], "text") else str(result[0])
            data = json.loads(text)
            assert "annotation_styles" in data
            styles = data["annotation_styles"]
            assert "insight" in styles
            assert "warning" in styles
            assert "reference" in styles


class TestStoryPlanningGuideContent:
    """Unit tests for the guide constant itself, no MCP round-trip needed."""

    def test_guide_constant_exists(self):
        from viznoir.prompts.guides import _STORY_PLANNING_GUIDE

        assert isinstance(_STORY_PLANNING_GUIDE, str)
        assert len(_STORY_PLANNING_GUIDE) > 200

    def test_guide_has_domain_placeholder(self):
        from viznoir.prompts.guides import _STORY_PLANNING_GUIDE

        assert "{domain}" in _STORY_PLANNING_GUIDE

    def test_storytelling_data_exists(self):
        from viznoir.resources.catalog import _STORYTELLING_DATA

        assert isinstance(_STORYTELLING_DATA, dict)
        assert "scene_templates" in _STORYTELLING_DATA
        assert "narrative_patterns" in _STORYTELLING_DATA
        assert "annotation_styles" in _STORYTELLING_DATA
