"""Tests for engine/lighting.py — cinematic lighting presets."""

from __future__ import annotations

import pytest
import vtk

from viznoir.engine.lighting import (
    LIGHTING_PRESETS,
    LightDef,
    apply_lighting,
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


class TestLightingPresets:
    def test_all_presets_exist(self):
        expected = {"cinematic", "dramatic", "studio", "publication", "outdoor"}
        assert expected == set(LIGHTING_PRESETS.keys())

    def test_each_preset_has_lights(self):
        for name, preset in LIGHTING_PRESETS.items():
            assert len(preset.lights) > 0, f"{name} has no lights"
            assert preset.name == name

    def test_get_preset_names(self):
        names = get_preset_names()
        assert isinstance(names, list)
        assert "cinematic" in names

    def test_light_def_frozen(self):
        ldef = LightDef("directional", (1, 0, 0), (1, 1, 1), 1.0)
        with pytest.raises(AttributeError):
            ldef.type = "ambient"  # type: ignore[misc]


class TestApplyLighting:
    @pytest.mark.parametrize("preset_name", list(LIGHTING_PRESETS.keys()))
    def test_apply_each_preset(self, renderer, preset_name):
        apply_lighting(renderer, preset_name)
        lights = renderer.GetLights()
        assert lights.GetNumberOfItems() > 0

    def test_replaces_existing_lights(self, renderer):
        # Add a dummy light first
        light = vtk.vtkLight()
        renderer.AddLight(light)
        assert renderer.GetLights().GetNumberOfItems() >= 1

        apply_lighting(renderer, "cinematic")
        # Should have exactly the preset's lights, not the old one + new ones
        assert renderer.GetLights().GetNumberOfItems() == len(LIGHTING_PRESETS["cinematic"].lights)

    def test_invalid_preset_raises(self, renderer):
        with pytest.raises(KeyError):
            apply_lighting(renderer, "nonexistent")

    def test_cinematic_has_three_lights(self, renderer):
        apply_lighting(renderer, "cinematic")
        assert renderer.GetLights().GetNumberOfItems() == 3

    def test_publication_has_two_lights(self, renderer):
        apply_lighting(renderer, "publication")
        assert renderer.GetLights().GetNumberOfItems() == 2

    def test_positional_light(self, renderer):
        """Cover positional light type branch (lines 108-113)."""
        from viznoir.engine.lighting import LightingPreset

        # Temporarily add a positional-light preset
        LIGHTING_PRESETS["_test_spot"] = LightingPreset(
            "_test_spot",
            (
                LightDef("positional", (5.0, 5.0, 5.0), (1.0, 1.0, 1.0), 1.0, 30.0),
            ),
        )
        try:
            apply_lighting(renderer, "_test_spot")
            lights = renderer.GetLights()
            assert lights.GetNumberOfItems() == 1
        finally:
            del LIGHTING_PRESETS["_test_spot"]

    def test_positional_light_no_cone(self, renderer):
        """Positional light with cone_angle=0 skips SetConeAngle."""
        from viznoir.engine.lighting import LightingPreset

        LIGHTING_PRESETS["_test_pos_nocone"] = LightingPreset(
            "_test_pos_nocone",
            (
                LightDef("positional", (3.0, 3.0, 3.0), (1.0, 1.0, 1.0), 0.8, 0.0),
            ),
        )
        try:
            apply_lighting(renderer, "_test_pos_nocone")
            assert renderer.GetLights().GetNumberOfItems() == 1
        finally:
            del LIGHTING_PRESETS["_test_pos_nocone"]
