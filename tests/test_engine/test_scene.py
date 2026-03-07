"""Tests for engine/scene.py — background and ground plane."""

from __future__ import annotations

import pytest
import vtk

from viznoir.engine.scene import (
    BACKGROUND_PRESETS,
    add_ground_plane,
    apply_background,
    apply_gradient_background,
    get_preset_names,
)


@pytest.fixture
def renderer():
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(True)
    rw.SetSize(100, 100)
    ren = vtk.vtkRenderer()
    rw.AddRenderer(ren)
    return ren


class TestBackgroundPresets:
    def test_all_presets_have_colors(self):
        for name, preset in BACKGROUND_PRESETS.items():
            assert len(preset.top_color) == 3
            assert len(preset.bottom_color) == 3
            assert preset.name == name

    def test_get_preset_names(self):
        names = get_preset_names()
        assert "dark_gradient" in names
        assert "publication" in names

    @pytest.mark.parametrize("preset_name", list(BACKGROUND_PRESETS.keys()))
    def test_apply_each_preset(self, renderer, preset_name):
        apply_background(renderer, preset_name)
        bg = renderer.GetBackground()
        assert len(bg) == 3

    def test_gradient_preset_enables_gradient(self, renderer):
        apply_background(renderer, "dark_gradient")
        assert renderer.GetGradientBackground() is True

    def test_solid_preset_disables_gradient(self, renderer):
        apply_background(renderer, "solid_white")
        assert renderer.GetGradientBackground() is False

    def test_invalid_preset_raises(self, renderer):
        with pytest.raises(KeyError):
            apply_background(renderer, "nonexistent")


class TestGradientBackground:
    def test_custom_gradient(self, renderer):
        apply_gradient_background(renderer, top=(0.1, 0.2, 0.3), bottom=(0.4, 0.5, 0.6))
        assert renderer.GetGradientBackground() is True
        assert renderer.GetBackground() == pytest.approx((0.4, 0.5, 0.6))
        assert renderer.GetBackground2() == pytest.approx((0.1, 0.2, 0.3))


class TestGroundPlane:
    def test_adds_actor(self, renderer):
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        initial = renderer.GetActors().GetNumberOfItems()
        add_ground_plane(renderer, bounds)
        assert renderer.GetActors().GetNumberOfItems() == initial + 1

    def test_custom_color_opacity(self, renderer):
        bounds = (0.0, 2.0, 0.0, 2.0, 0.0, 2.0)
        add_ground_plane(renderer, bounds, color=(0.5, 0.5, 0.5), opacity=0.8)
        actors = renderer.GetActors()
        actors.InitTraversal()
        actor = actors.GetNextActor()
        assert actor.GetProperty().GetOpacity() == pytest.approx(0.8)

    def test_degenerate_bounds(self, renderer):
        bounds = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        add_ground_plane(renderer, bounds)
        assert renderer.GetActors().GetNumberOfItems() == 1
