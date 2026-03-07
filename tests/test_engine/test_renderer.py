"""Tests for engine/renderer.py — VTKRenderer config and helpers."""

from __future__ import annotations

from viznoir.engine.renderer import RenderConfig


class TestRenderConfig:
    def test_default_values(self):
        config = RenderConfig()
        assert config.width == 1920
        assert config.height == 1080
        assert config.background == (0.2, 0.2, 0.2)
        assert config.colormap == "cool to warm"
        assert config.scalar_range is None
        assert config.log_scale is False
        assert config.array_name is None
        assert config.component == -1
        assert config.representation == "surface"
        assert config.opacity == 1.0
        assert config.show_scalar_bar is True
        assert config.edge_visibility is False
        assert config.point_size == 2.0
        assert config.line_width == 1.0

    def test_custom_values(self):
        config = RenderConfig(
            width=800,
            height=600,
            background=(1.0, 1.0, 1.0),
            colormap="viridis",
            scalar_range=(0.0, 100.0),
            log_scale=True,
            array_name="pressure",
            representation="wireframe",
            opacity=0.5,
        )
        assert config.width == 800
        assert config.height == 600
        assert config.colormap == "viridis"
        assert config.scalar_range == (0.0, 100.0)
        assert config.log_scale is True
        assert config.array_name == "pressure"
        assert config.representation == "wireframe"
        assert config.opacity == 0.5

    def test_scalar_bar_title(self):
        config = RenderConfig(scalar_bar_title="Pressure [Pa]")
        assert config.scalar_bar_title == "Pressure [Pa]"

    def test_edge_config(self):
        config = RenderConfig(
            edge_visibility=True,
            edge_color=(0.5, 0.5, 0.5),
        )
        assert config.edge_visibility is True
        assert config.edge_color == (0.5, 0.5, 0.5)

    def test_volume_representation(self):
        config = RenderConfig(representation="volume")
        assert config.representation == "volume"
