"""Tests for compose_assets MCP tool registration and basic operation."""

from __future__ import annotations

import os

import pytest
from PIL import Image


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


class TestResolveAssets:
    """Test _resolve_assets internal helper."""

    def test_resolve_latex_asset(self):
        from viznoir.tools.compose import _resolve_assets

        assets = [{"type": "latex", "tex": r"E = mc^2", "color": "FFFFFF"}]
        images = _resolve_assets(assets)
        assert len(images) == 1
        assert images[0].mode == "RGBA"
        assert images[0].width > 0

    def test_resolve_text_asset(self):
        from viznoir.tools.compose import _resolve_assets

        assets = [{"type": "text", "content": "Hello World"}]
        images = _resolve_assets(assets)
        assert len(images) == 1
        assert images[0].mode == "RGBA"

    def test_resolve_unknown_type_placeholder(self):
        from viznoir.tools.compose import _resolve_assets

        assets = [{"type": "unknown_type_xyz"}]
        images = _resolve_assets(assets)
        assert len(images) == 1
        assert images[0].size == (400, 300)

    def test_resolve_render_missing_file_placeholder(self):
        from viznoir.tools.compose import _resolve_assets

        assets = [{"type": "render", "path": "/nonexistent/file.png"}]
        images = _resolve_assets(assets)
        assert len(images) == 1
        assert images[0].size == (400, 300)  # grey placeholder

    def test_resolve_render_existing_file(self, tmp_path):
        from viznoir.tools.compose import _resolve_assets

        img = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
        path = tmp_path / "test.png"
        img.save(str(path))

        os.environ.pop("VIZNOIR_DATA_DIR", None)
        assets = [{"type": "render", "path": str(path)}]
        images = _resolve_assets(assets)
        assert len(images) == 1
        assert images[0].width == 100

    def test_path_traversal_blocked(self, tmp_path):
        from viznoir.tools.compose import _resolve_assets

        img = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
        path = tmp_path / "test.png"
        img.save(str(path))

        # Set data dir to somewhere else
        os.environ["VIZNOIR_DATA_DIR"] = "/nonexistent/safe/dir"
        os.environ["VIZNOIR_OUTPUT_DIR"] = "/nonexistent/output/dir"
        try:
            with pytest.raises(ValueError, match="outside allowed"):
                _resolve_assets([{"type": "render", "path": str(path)}])
        finally:
            os.environ.pop("VIZNOIR_DATA_DIR", None)
            os.environ.pop("VIZNOIR_OUTPUT_DIR", None)

    def test_resolve_multiple_assets(self):
        from viznoir.tools.compose import _resolve_assets

        assets = [
            {"type": "latex", "tex": r"x^2", "color": "FF0000"},
            {"type": "text", "content": "Caption"},
        ]
        images = _resolve_assets(assets)
        assert len(images) == 2


class TestTextToImage:
    def test_text_to_image(self):
        from viznoir.tools.compose import _text_to_image

        img = _text_to_image("Test text")
        assert img.mode == "RGBA"
        assert img.size == (600, 200)


class TestRenderStoryWrapper:
    def test_render_story_wrapper(self):
        from viznoir.tools.compose import _render_story

        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        result = _render_story([img], ["Label"], None, 800, 600)
        assert result.size == (800, 600)

    def test_render_story_with_title(self):
        from viznoir.tools.compose import _render_story

        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        result = _render_story([img], ["Label"], "Title", 800, 600)
        assert result.size == (800, 600)


class TestComposeImpl:
    async def test_story_layout(self, tmp_path):
        from viznoir.tools.compose import compose_assets_impl

        result = await compose_assets_impl(
            [{"type": "text", "content": "Hello", "label": "Text"}],
            layout="story",
            output_dir=str(tmp_path),
        )
        assert result["layout"] == "story"
        assert os.path.exists(result["output_path"])

    async def test_grid_layout(self, tmp_path):
        from viznoir.tools.compose import compose_assets_impl

        result = await compose_assets_impl(
            [{"type": "text", "content": "A"}, {"type": "text", "content": "B"}],
            layout="grid",
            output_dir=str(tmp_path),
        )
        assert result["layout"] == "grid"
        assert os.path.exists(result["output_path"])

    async def test_slides_layout(self, tmp_path):
        from viznoir.tools.compose import compose_assets_impl

        result = await compose_assets_impl(
            [{"type": "text", "content": "Slide 1"}, {"type": "text", "content": "Slide 2"}],
            layout="slides",
            output_dir=str(tmp_path),
        )
        assert result["layout"] == "slides"
        assert result["slide_count"] == 2
        assert len(result["output_paths"]) == 2

    async def test_unknown_layout_raises(self, tmp_path):
        from viznoir.tools.compose import compose_assets_impl

        with pytest.raises(ValueError, match="Unknown layout"):
            await compose_assets_impl(
                [{"type": "text", "content": "X"}],
                layout="nonexistent",
                output_dir=str(tmp_path),
            )


class TestRenderVideo:
    def test_render_video_builds_frames(self, tmp_path):
        """Test _render_video frame generation (ffmpeg may or may not be available)."""
        from unittest.mock import patch

        from viznoir.tools.compose import _render_video

        img1 = Image.new("RGBA", (320, 240), (255, 0, 0, 255))
        img2 = Image.new("RGBA", (320, 240), (0, 0, 255, 255))

        # Mock export_video to avoid ffmpeg dependency
        with patch("viznoir.anim.compositor.export_video") as mock_export:
            result = _render_video(
                [img1, img2],
                ["Scene 1", "Scene 2"],
                None,
                320,
                240,
                10,
                str(tmp_path),
            )
            assert result["layout"] == "video"
            assert result["scene_count"] == 2
            assert result["frame_count"] > 0
            assert result["fps"] == 10
            assert mock_export.called

    def test_render_video_with_custom_scenes(self, tmp_path):
        from unittest.mock import patch

        from viznoir.tools.compose import _render_video

        img = Image.new("RGBA", (160, 120), (0, 255, 0, 255))

        scenes = [
            {"asset_indices": [0], "duration": 1.0, "transition": "fade_in"},
            {"asset_indices": [0], "duration": 1.0, "transition": "dissolve"},
        ]
        with patch("viznoir.anim.compositor.export_video"):
            result = _render_video(
                [img],
                ["Label"],
                scenes,
                160,
                120,
                10,
                str(tmp_path),
            )
            assert result["scene_count"] == 2
            assert result["duration"] == 2.0
