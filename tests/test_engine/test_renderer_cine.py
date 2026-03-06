"""Tests for engine/renderer_cine.py — cinematic renderer integration."""

from __future__ import annotations

import os

import pytest
import vtk

from parapilot.engine.renderer_cine import (
    QUALITY_PRESETS,
    CinematicConfig,
    _apply_quality_preset,
    _scene_diagonal,
    cinematic_render,
)

_skip_rendering = pytest.mark.skipif(
    bool(os.environ.get("CI")),
    reason="VTK offscreen rendering requires GPU (not available in CI)",
)


@pytest.fixture
def wavelet():
    """Standard VTK wavelet test dataset."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()
    return src.GetOutput()


@pytest.fixture
def sphere():
    """Simple sphere polydata."""
    src = vtk.vtkSphereSource()
    src.SetRadius(1.0)
    src.SetThetaResolution(32)
    src.SetPhiResolution(32)
    src.Update()
    return src.GetOutput()


class TestCinematicConfig:
    def test_defaults(self):
        config = CinematicConfig()
        assert config.lighting_preset == "cinematic"
        assert config.ssao is True
        assert config.fxaa is True
        assert config.auto_camera is True

    def test_quality_preset_override(self):
        config = CinematicConfig(quality="draft")
        _apply_quality_preset(config)
        assert config.render.width == 960
        assert config.ssao is False

    def test_publication_preset(self):
        config = CinematicConfig(quality="publication")
        _apply_quality_preset(config)
        assert config.render.width == 2400
        assert config.lighting_preset == "publication"
        assert config.ground_plane is False

    def test_unknown_quality_no_crash(self):
        config = CinematicConfig(quality="nonexistent")
        _apply_quality_preset(config)  # should not raise


class TestQualityPresets:
    def test_all_presets_have_required_keys(self):
        for name, preset in QUALITY_PRESETS.items():
            assert "width" in preset, f"{name} missing width"
            assert "height" in preset, f"{name} missing height"


class TestSceneDiagonal:
    def test_unit_cube(self):
        src = vtk.vtkCubeSource()
        src.SetXLength(2.0)
        src.SetYLength(2.0)
        src.SetZLength(2.0)
        src.Update()
        diag = _scene_diagonal(src.GetOutput())
        assert diag == pytest.approx(2.0 * (3**0.5), rel=0.01)

    def test_degenerate(self):
        src = vtk.vtkSphereSource()
        src.SetRadius(0.0)
        src.Update()
        diag = _scene_diagonal(src.GetOutput())
        assert diag == 1.0  # fallback


@_skip_rendering
class TestCinematicRender:
    def test_basic_render_produces_png(self, wavelet):
        config = CinematicConfig(quality="draft")
        png = cinematic_render(wavelet, config)
        assert len(png) > 1000
        assert png[:4] == b"\x89PNG"

    def test_standard_quality(self, sphere):
        config = CinematicConfig(quality="standard")
        png = cinematic_render(sphere, config)
        assert png[:4] == b"\x89PNG"

    def test_cinematic_quality(self, wavelet):
        config = CinematicConfig(quality="cinematic")
        png = cinematic_render(wavelet, config)
        assert len(png) > 1000

    def test_publication_quality(self, sphere):
        config = CinematicConfig(quality="publication")
        png = cinematic_render(sphere, config)
        assert png[:4] == b"\x89PNG"

    def test_custom_azimuth_elevation(self, wavelet):
        config = CinematicConfig(quality="draft", azimuth=90.0, elevation=45.0)
        png = cinematic_render(wavelet, config)
        assert len(png) > 1000

    def test_no_lighting(self, sphere):
        config = CinematicConfig(quality="draft", lighting_preset=None)
        png = cinematic_render(sphere, config)
        assert png[:4] == b"\x89PNG"

    def test_no_background_preset(self, sphere):
        config = CinematicConfig(quality="draft", background_preset=None)
        png = cinematic_render(sphere, config)
        assert png[:4] == b"\x89PNG"

    def test_with_ground_plane(self, sphere):
        config = CinematicConfig(quality="draft", ground_plane=True)
        png = cinematic_render(sphere, config)
        assert png[:4] == b"\x89PNG"

    def test_pbr_metallic(self, sphere):
        config = CinematicConfig(quality="draft", metallic=0.9, roughness=0.1)
        png = cinematic_render(sphere, config)
        assert png[:4] == b"\x89PNG"

    def test_auto_camera_disabled(self, wavelet):
        config = CinematicConfig(quality="draft", auto_camera=False)
        png = cinematic_render(wavelet, config)
        assert png[:4] == b"\x89PNG"

    def test_none_config_uses_defaults(self, wavelet):
        png = cinematic_render(wavelet)
        assert png[:4] == b"\x89PNG"

    def test_fill_ratio(self, sphere):
        config_50 = CinematicConfig(quality="draft", fill_ratio=0.5)
        config_90 = CinematicConfig(quality="draft", fill_ratio=0.9)
        png_50 = cinematic_render(sphere, config_50)
        png_90 = cinematic_render(sphere, config_90)
        # Both should be valid PNGs with different framing
        assert png_50[:4] == b"\x89PNG"
        assert png_90[:4] == b"\x89PNG"
