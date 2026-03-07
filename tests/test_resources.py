"""Tests for resources/catalog.py — MCP resource registration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from viznoir.resources import catalog as _catalog_mod


def _capture_resources():
    """Register resources with a mock and return name→function mapping."""
    mcp = MagicMock()
    captured = {}

    def resource_decorator(uri):
        def wrapper(fn):
            captured[uri] = fn
            return fn
        return wrapper

    mcp.resource = resource_decorator
    # Reset idempotency guard — id() can be reused after GC of previous mocks
    _catalog_mod._registered_instances.discard(id(mcp))
    _catalog_mod.register_resources(mcp)
    return captured


class TestResourceRegistration:
    def test_all_resources_registered(self):
        resources = _capture_resources()
        expected = {
            "viznoir://formats",
            "viznoir://filters",
            "viznoir://colormaps",
            "viznoir://representations",
            "viznoir://case-presets",
            "viznoir://cameras",
            "viznoir://cinematic",
            "viznoir://pipelines/cfd",
            "viznoir://pipelines/fea",
            "viznoir://pipelines/split-animate",
            "viznoir://physics-defaults",
        }
        assert expected.issubset(set(resources.keys()))


class TestFormatsResource:
    def test_returns_valid_json(self):
        resources = _capture_resources()
        result = resources["viznoir://formats"]()
        data = json.loads(result)
        assert isinstance(data, dict)
        assert ".vtk" in data or ".vtu" in data

    def test_entries_have_reader(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://formats"]())
        for ext, info in data.items():
            assert "reader" in info


class TestFiltersResource:
    def test_returns_valid_json(self):
        resources = _capture_resources()
        result = resources["viznoir://filters"]()
        data = json.loads(result)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_entries_have_vtk_class(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://filters"]())
        for name, info in data.items():
            assert "vtk_class" in info


class TestCasePresetsResource:
    def test_returns_valid_json(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://case-presets"]())
        assert isinstance(data, dict)
        assert len(data) > 0


class TestCamerasResource:
    def test_has_presets_and_auto_camera(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://cameras"]())
        assert "presets" in data
        assert "auto_camera" in data
        assert "custom" in data


class TestCinematicResource:
    def test_has_all_sections(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://cinematic"]())
        assert "lighting_presets" in data
        assert "material_presets" in data
        assert "background_presets" in data
        assert "quality_presets" in data


class TestPipelineResources:
    def test_cfd_pipelines(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://pipelines/cfd"]())
        assert "pressure_distribution" in data
        assert "velocity_slice" in data
        assert "streamlines" in data

    def test_fea_pipelines(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://pipelines/fea"]())
        assert "deformation" in data
        assert "stress_threshold" in data

    def test_split_animate_pipelines(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://pipelines/split-animate"]())
        assert "dual_field_comparison" in data


class TestPhysicsDefaultsResource:
    def test_returns_valid_json(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://physics-defaults"]())
        assert isinstance(data, dict)
        assert "_usage" in data

    def test_has_known_physics(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://physics-defaults"]())
        keys = set(data.keys())
        # Should detect at least pressure, velocity, temperature
        assert "pressure" in keys or "Pressure" in keys


class TestColormapsResource:
    def test_returns_valid_json(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://colormaps"]())
        assert isinstance(data, dict)
        assert "colormaps" in data
        assert "field_recommendations" in data
        assert len(data["colormaps"]) >= 16

    def test_field_recommendations_reference_valid_colormaps(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://colormaps"]())
        guide_names = {k.lower() for k in data["colormaps"]}
        for field, cmap in data["field_recommendations"].items():
            if field.startswith("_"):
                continue
            assert cmap.lower() in guide_names, f"{field} → {cmap} not in guide"


class TestRepresentationsResource:
    def test_returns_valid_json(self):
        resources = _capture_resources()
        data = json.loads(resources["viznoir://representations"]())
        assert isinstance(data, dict)
