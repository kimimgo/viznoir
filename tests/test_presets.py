"""Tests for presets package — case-type rendering defaults."""

from __future__ import annotations

from viznoir.presets import CASE_PRESETS, get_preset, list_presets
from viznoir.presets.registry import CAMERAS, COLORMAP_GUIDE, REPRESENTATION_GUIDE


class TestCameraPresets:
    def test_all_cameras_have_required_keys(self):
        for name, cam in CAMERAS.items():
            assert "position" in cam, f"{name} missing position"
            assert "focal_point" in cam, f"{name} missing focal_point"
            assert "view_up" in cam, f"{name} missing view_up"
            assert len(cam["position"]) == 3
            assert len(cam["focal_point"]) == 3
            assert len(cam["view_up"]) == 3

    def test_standard_cameras_exist(self):
        expected = {"isometric", "top", "front", "right", "left", "back"}
        assert expected.issubset(set(CAMERAS.keys()))


class TestCasePresets:
    def test_all_presets_have_description(self):
        for name, preset in CASE_PRESETS.items():
            assert "description" in preset, f"{name} missing description"

    def test_all_presets_have_fields(self):
        for name, preset in CASE_PRESETS.items():
            assert "fields" in preset, f"{name} missing fields"

    def test_all_presets_have_views(self):
        for name, preset in CASE_PRESETS.items():
            assert "views" in preset, f"{name} missing views"

    def test_known_presets_exist(self):
        expected = {"external_aero", "internal_flow", "multiphase", "thermal", "structural_fea"}
        assert expected.issubset(set(CASE_PRESETS.keys()))

    def test_field_entries_have_colormap(self):
        for preset_name, preset in CASE_PRESETS.items():
            for field_name, field_cfg in preset["fields"].items():
                assert "colormap" in field_cfg, f"{preset_name}.{field_name} missing colormap"


class TestPresetAPI:
    def test_list_presets(self):
        names = list_presets()
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)

    def test_get_preset_valid(self):
        preset = get_preset("external_aero")
        assert preset is not None
        assert "description" in preset

    def test_get_preset_invalid(self):
        import pytest

        with pytest.raises(KeyError, match="nonexistent"):
            get_preset("nonexistent_preset_name")


class TestGuides:
    def test_colormap_guide_not_empty(self):
        assert len(COLORMAP_GUIDE) > 0

    def test_representation_guide_not_empty(self):
        assert len(REPRESENTATION_GUIDE) > 0
