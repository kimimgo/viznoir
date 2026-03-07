"""Tests for engine/materials.py — PBR material presets."""

from __future__ import annotations

import pytest
import vtk

from viznoir.engine.materials import (
    MATERIAL_PRESETS,
    apply_material,
    get_preset_names,
)


@pytest.fixture
def actor():
    src = vtk.vtkSphereSource()
    src.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(src.GetOutput())
    a = vtk.vtkActor()
    a.SetMapper(mapper)
    return a


class TestMaterialPresets:
    def test_all_presets_valid(self):
        for name, preset in MATERIAL_PRESETS.items():
            assert 0.0 <= preset.metallic <= 1.0
            assert 0.0 <= preset.roughness <= 1.0
            assert 0.0 <= preset.opacity <= 1.0
            assert preset.name == name

    def test_get_preset_names(self):
        names = get_preset_names()
        assert "brushed_metal" in names
        assert "matte_vis" in names
        assert len(names) == len(MATERIAL_PRESETS)

    def test_frozen(self):
        preset = MATERIAL_PRESETS["ceramic"]
        with pytest.raises(AttributeError):
            preset.metallic = 0.5  # type: ignore[misc]


class TestApplyMaterial:
    @pytest.mark.parametrize("preset_name", list(MATERIAL_PRESETS.keys()))
    def test_apply_each_preset(self, actor, preset_name):
        apply_material(actor, preset_name)
        prop = actor.GetProperty()
        preset = MATERIAL_PRESETS[preset_name]
        assert prop.GetMetallic() == pytest.approx(preset.metallic)
        assert prop.GetRoughness() == pytest.approx(preset.roughness)

    def test_invalid_preset_raises(self, actor):
        with pytest.raises(KeyError):
            apply_material(actor, "nonexistent")

    def test_glass_opacity(self, actor):
        apply_material(actor, "glass")
        assert actor.GetProperty().GetOpacity() == pytest.approx(0.3)

    def test_matte_vis_no_color_override(self, actor):
        original_color = actor.GetProperty().GetColor()
        apply_material(actor, "matte_vis")
        # matte_vis has no color → actor color should be unchanged
        assert actor.GetProperty().GetColor() == original_color
