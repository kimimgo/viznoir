"""Tests for transfer function presets."""

from __future__ import annotations

import pytest

from viznoir.engine.transfer_functions import (
    TRANSFER_PRESETS,
    build_opacity_function,
    list_presets,
)


class TestTransferPresets:
    def test_list_presets_returns_sorted(self):
        presets = list_presets()
        assert presets == sorted(presets)
        assert len(presets) >= 5

    def test_known_presets_exist(self):
        presets = list_presets()
        for name in ["ct_bone", "ct_tissue", "mri_brain", "thermal", "generic"]:
            assert name in presets, f"Missing preset: {name}"

    @pytest.mark.parametrize("preset_name", list(TRANSFER_PRESETS.keys()))
    def test_each_preset_has_required_keys(self, preset_name):
        preset = TRANSFER_PRESETS[preset_name]
        assert "opacity_points" in preset
        assert "description" in preset
        points = preset["opacity_points"]
        assert len(points) >= 2
        for val, opacity in points:
            assert 0.0 <= val <= 1.0
            assert 0.0 <= opacity <= 1.0


class TestBuildOpacityFunction:
    def test_returns_vtk_piecewise(self):
        import vtk
        otf = build_opacity_function("generic", scalar_range=(0.0, 100.0))
        assert isinstance(otf, vtk.vtkPiecewiseFunction)

    def test_custom_range_maps_correctly(self):
        otf = build_opacity_function("generic", scalar_range=(10.0, 50.0))
        assert otf.GetSize() >= 2

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="no_such_preset"):
            build_opacity_function("no_such_preset", scalar_range=(0.0, 1.0))
