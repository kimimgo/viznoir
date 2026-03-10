"""Tests for Compositor — split-pane frame composition."""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import patch

import pytest

from viznoir.pipeline.models import (
    SplitAnimationDef,
)


def _make_split_anim(
    panes: list[dict[str, Any]] | None = None,
    rows: int = 1,
    cols: int = 2,
    resolution: list[int] | None = None,
    gif: bool = True,
) -> SplitAnimationDef:
    """Helper to create a SplitAnimationDef for testing."""
    if panes is None:
        panes = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}, "title": "Pressure"}},
            {"type": "render", "row": 0, "col": 1, "render_pane": {"render": {"field": "U", "colormap": "Viridis"}}},
        ]
    return SplitAnimationDef.model_validate(
        {
            "panes": panes,
            "layout": {"rows": rows, "cols": cols},
            "resolution": resolution or [800, 400],
            "gif": gif,
            "fps": 10,
        }
    )


def _make_png(width: int = 100, height: int = 100, color: str = "red") -> bytes:
    """Create a minimal PNG for testing."""
    from PIL import Image as PILImage

    img = PILImage.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestCompositorInit:
    def test_cell_dimensions(self) -> None:
        from viznoir.core.compositor import Compositor

        sa = _make_split_anim(resolution=[800, 400], rows=1, cols=2)
        c = Compositor(sa)
        # 800 total, 2 cols, gap=4 → (800-4)/2 = 398
        assert c.cell_width == 398
        assert c.cell_height == 400

    def test_cell_dimensions_2x2(self) -> None:
        from viznoir.core.compositor import Compositor

        sa = _make_split_anim(resolution=[804, 404], rows=2, cols=2)
        c = Compositor(sa)
        # (804 - 4) / 2 = 400, (404 - 4) / 2 = 200
        assert c.cell_width == 400
        assert c.cell_height == 200


class TestCompositorCompose:
    def test_compose_render_only(self) -> None:
        """Compose 2 render panes without graphs."""
        from viznoir.core.compositor import Compositor

        sa = _make_split_anim(resolution=[800, 400], rows=1, cols=2, gif=False)
        c = Compositor(sa)

        pane_data = {
            "pane_0_frame_000000.png": _make_png(398, 400, "red"),
            "pane_1_frame_000000.png": _make_png(398, 400, "blue"),
        }
        stats: dict[str, Any] = {"timesteps": [0.0], "fields": {}}

        composed_bytes, gif_bytes = c.compose_all(pane_data, stats, frame_count=1)
        assert len(composed_bytes) == 1
        assert gif_bytes is None

        # Verify composed image is valid PNG
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(composed_bytes[0]))
        assert img.size == (800, 400)

    def test_compose_generates_gif(self) -> None:
        """Compose multiple frames and generate GIF."""
        from viznoir.core.compositor import Compositor

        sa = _make_split_anim(resolution=[800, 400], rows=1, cols=2, gif=True)
        c = Compositor(sa)

        pane_data = {}
        for frame in range(3):
            pane_data[f"pane_0_frame_{frame:06d}.png"] = _make_png(398, 400, "red")
            pane_data[f"pane_1_frame_{frame:06d}.png"] = _make_png(398, 400, "blue")

        stats: dict[str, Any] = {"timesteps": [0.0, 0.5, 1.0], "fields": {}}

        composed_bytes, gif_bytes = c.compose_all(pane_data, stats, frame_count=3)
        assert len(composed_bytes) == 3
        assert gif_bytes is not None
        assert len(gif_bytes) > 0
        # GIF magic bytes
        assert gif_bytes[:6] in (b"GIF87a", b"GIF89a")


class TestCompositorGraphPane:
    def test_compose_with_graph(self) -> None:
        """Compose render + graph panes."""
        from viznoir.core.compositor import Compositor

        panes: list[dict[str, Any]] = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}}},
            {
                "type": "graph",
                "row": 0,
                "col": 1,
                "graph_pane": {
                    "series": [{"field": "p", "stat": "max"}],
                    "title": "Max Pressure",
                    "y_label": "p [Pa]",
                },
            },
        ]
        sa = _make_split_anim(panes=panes, resolution=[800, 400], rows=1, cols=2, gif=False)
        c = Compositor(sa)

        pane_data = {
            "pane_0_frame_000000.png": _make_png(398, 400, "red"),
            "pane_0_frame_000001.png": _make_png(398, 400, "red"),
        }
        stats: dict[str, Any] = {
            "timesteps": [0.0, 0.5],
            "fields": {
                "p": {"min": [0.0, 0.1], "max": [1.0, 1.5], "mean": [0.5, 0.8]},
            },
        }

        composed_bytes, _ = c.compose_all(pane_data, stats, frame_count=2)
        assert len(composed_bytes) == 2


class TestCompositorGif:
    def test_gif_duration(self) -> None:
        """GIF frame duration should match fps."""
        from viznoir.core.compositor import Compositor

        sa = _make_split_anim(resolution=[200, 100], rows=1, cols=2, gif=True)
        sa_with_fps = sa.model_copy(update={"fps": 10})
        c = Compositor(sa_with_fps)

        # Use different colors per frame to prevent GIF optimize from merging
        colors = ["red", "blue", "green"]
        pane_data = {}
        for frame in range(3):
            pane_data[f"pane_0_frame_{frame:06d}.png"] = _make_png(98, 100, colors[frame])
            pane_data[f"pane_1_frame_{frame:06d}.png"] = _make_png(98, 100, colors[frame])

        stats: dict[str, Any] = {"timesteps": [0.0, 0.1, 0.2], "fields": {}}
        _, gif_bytes = c.compose_all(pane_data, stats, frame_count=3)
        assert gif_bytes is not None

        from PIL import Image as PILImage

        gif = PILImage.open(io.BytesIO(gif_bytes))
        # 1000ms / 10fps = 100ms per frame
        assert gif.info.get("duration") == 100
        assert gif.n_frames == 3


class TestCompositorGraphEdgeCases:
    def test_graph_with_missing_field_stats(self) -> None:
        """Graph pane with series referencing missing field should not crash."""
        from viznoir.core.compositor import Compositor

        panes: list[dict[str, Any]] = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}}},
            {
                "type": "graph",
                "row": 0,
                "col": 1,
                "graph_pane": {
                    "series": [{"field": "nonexistent_field", "stat": "max"}],
                    "title": "Missing",
                },
            },
        ]
        sa = _make_split_anim(panes=panes, resolution=[800, 400], rows=1, cols=2, gif=False)
        c = Compositor(sa)
        pane_data = {
            "pane_0_frame_000000.png": _make_png(398, 400, "red"),
        }
        stats: dict[str, Any] = {"timesteps": [0.0], "fields": {}}
        composed, _ = c.compose_all(pane_data, stats, frame_count=1)
        assert len(composed) == 1

    def test_graph_with_y_range(self) -> None:
        """Graph pane with y_range set applies axis limits."""
        from viznoir.core.compositor import Compositor

        panes: list[dict[str, Any]] = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}}},
            {
                "type": "graph",
                "row": 0,
                "col": 1,
                "graph_pane": {
                    "series": [{"field": "p", "stat": "max"}],
                    "y_range": [0.0, 10.0],
                    "y_label": "p [Pa]",
                },
            },
        ]
        sa = _make_split_anim(panes=panes, resolution=[800, 400], rows=1, cols=2, gif=False)
        c = Compositor(sa)
        pane_data = {
            "pane_0_frame_000000.png": _make_png(398, 400, "red"),
        }
        stats: dict[str, Any] = {
            "timesteps": [0.0],
            "fields": {"p": {"max": [5.0]}},
        }
        composed, _ = c.compose_all(pane_data, stats, frame_count=1)
        assert len(composed) == 1

    def test_compose_font_fallback(self) -> None:
        """Font OSError in _compose_single_frame falls back to default."""
        from viznoir.core.compositor import Compositor

        panes: list[dict[str, Any]] = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}, "title": "Titled Pane"}},
        ]
        sa = _make_split_anim(panes=panes, resolution=[400, 400], rows=1, cols=1, gif=False)
        c = Compositor(sa)

        from PIL import Image as PILImage
        from PIL import ImageFont

        render_img = PILImage.new("RGB", (400, 400), "red")
        render_images = {(0, 0): render_img}

        orig_truetype = ImageFont.truetype

        def selective_fail(font=None, size=10, *a, **kw):
            if font and "DejaVuSans.ttf" in str(font):
                raise OSError("font not found")
            return orig_truetype(font, size, *a, **kw)

        with patch.object(ImageFont, "truetype", side_effect=selective_fail):
            result = c._compose_single_frame(render_images, {})
        assert result is not None
        assert result.size == (400, 400)


class TestCompositorDependencyCheck:
    def test_missing_pillow_raises(self) -> None:
        """Should raise ImportError when pillow is not available."""
        from viznoir.core import compositor

        original = compositor._PIL_AVAILABLE
        try:
            compositor._PIL_AVAILABLE = None
            with patch.dict("sys.modules", {"PIL": None}):
                compositor._PIL_AVAILABLE = None
                with pytest.raises(ImportError, match="pillow"):
                    compositor._check_pillow()
        finally:
            compositor._PIL_AVAILABLE = original

    def test_missing_matplotlib_raises(self) -> None:
        """Should raise ImportError when matplotlib is not available."""
        from viznoir.core import compositor

        original = compositor._MPL_AVAILABLE
        try:
            compositor._MPL_AVAILABLE = None
            with patch.dict("sys.modules", {"matplotlib": None}):
                compositor._MPL_AVAILABLE = None
                with pytest.raises(ImportError, match="matplotlib"):
                    compositor._check_matplotlib()
        finally:
            compositor._MPL_AVAILABLE = original
