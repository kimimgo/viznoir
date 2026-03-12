"""Tests for anim/physics.py — Physics-driven animation presets."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from viznoir.anim.physics import FrameConfig
from viznoir.anim.physics import __all__ as physics_all

# ---------------------------------------------------------------------------
# FrameConfig
# ---------------------------------------------------------------------------


class TestFrameConfig:
    def test_defaults(self):
        cfg = FrameConfig()
        assert cfg.width == 1280
        assert cfg.height == 720
        assert cfg.fps == 24
        assert cfg.duration == 8.0
        assert cfg.background == (0.02, 0.02, 0.04)

    def test_n_frames(self):
        cfg = FrameConfig(fps=24, duration=8.0)
        assert cfg.n_frames == 192

    def test_n_frames_one_second(self):
        cfg = FrameConfig(fps=30, duration=1.0)
        assert cfg.n_frames == 30

    def test_n_frames_fractional(self):
        cfg = FrameConfig(fps=24, duration=0.5)
        assert cfg.n_frames == 12

    def test_custom_values(self):
        cfg = FrameConfig(width=1920, height=1080, fps=60, duration=4.0, background=(0, 0, 0))
        assert cfg.width == 1920
        assert cfg.height == 1080
        assert cfg.n_frames == 240


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


class TestExports:
    def test_all_contains_frame_config(self):
        assert "FrameConfig" in physics_all

    def test_all_contains_presets(self):
        expected_presets = [
            "layer_reveal",
            "streamline_growth",
            "clip_sweep",
            "iso_sweep",
            "threshold_reveal",
            "warp_oscillation",
            "light_orbit",
        ]
        for name in expected_presets:
            assert name in physics_all, f"{name} not in __all__"

    def test_all_importable(self):
        import viznoir.anim.physics as mod

        for name in physics_all:
            assert hasattr(mod, name), f"{name} not importable from module"

    def test_all_callables_except_frameconfig(self):
        import viznoir.anim.physics as mod

        for name in physics_all:
            obj = getattr(mod, name)
            if name == "FrameConfig":
                assert isinstance(obj, type)
            else:
                assert callable(obj), f"{name} should be callable"


# ---------------------------------------------------------------------------
# _render_loop
# ---------------------------------------------------------------------------


class TestRenderLoop:
    @patch("viznoir.engine.renderer._capture_png", return_value=b"\x89PNG")
    @patch("viznoir.engine.renderer._get_render_window")
    def test_render_loop_creates_frames(self, mock_get_rw, mock_capture):
        from viznoir.anim.physics import _render_loop

        mock_rw = MagicMock()
        mock_renderers = MagicMock()
        mock_rw.GetRenderers.return_value = mock_renderers
        mock_get_rw.return_value = mock_rw

        mock_ren = MagicMock()

        def setup_fn(rw):
            rw.AddRenderer(mock_ren)
            return mock_ren

        frame_calls = []

        def frame_fn(ren, rw, t, idx):
            frame_calls.append((t, idx))

        cfg = FrameConfig(fps=2, duration=1.0)  # 2 frames

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = _render_loop(cfg, setup_fn, frame_fn, tmpdir)

            assert len(paths) == 2
            assert len(frame_calls) == 2
            assert frame_calls[0] == (0.0, 0)
            assert frame_calls[1] == (1.0, 1)

            for p in paths:
                assert os.path.exists(p)
                assert p.endswith(".png")

    @patch("viznoir.engine.renderer._capture_png", return_value=b"\x89PNG")
    @patch("viznoir.engine.renderer._get_render_window")
    def test_render_loop_t_normalized(self, mock_get_rw, mock_capture):
        from viznoir.anim.physics import _render_loop

        mock_rw = MagicMock()
        mock_rw.GetRenderers.return_value = MagicMock()
        mock_get_rw.return_value = mock_rw

        mock_ren = MagicMock()

        t_values = []

        def setup_fn(rw):
            rw.AddRenderer(mock_ren)
            return mock_ren

        def frame_fn(ren, rw, t, idx):
            t_values.append(t)

        cfg = FrameConfig(fps=5, duration=1.0)  # 5 frames

        with tempfile.TemporaryDirectory() as tmpdir:
            _render_loop(cfg, setup_fn, frame_fn, tmpdir)

        assert t_values[0] == pytest.approx(0.0)
        assert t_values[-1] == pytest.approx(1.0)
        # All values should be in [0, 1]
        for t in t_values:
            assert 0.0 <= t <= 1.0


# ---------------------------------------------------------------------------
# Preset function signatures (no VTK execution needed)
# ---------------------------------------------------------------------------


class TestPresetSignatures:
    """Verify each preset accepts expected arguments via inspect."""

    def test_layer_reveal_signature(self):
        import inspect

        from viznoir.anim.physics import layer_reveal

        sig = inspect.signature(layer_reveal)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "layers" in params
        assert "colormap" in params
        assert "config" in params
        assert "output_dir" in params

    def test_clip_sweep_signature(self):
        import inspect

        from viznoir.anim.physics import clip_sweep

        sig = inspect.signature(clip_sweep)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "axis" in params
        assert "bounce" in params

    def test_iso_sweep_signature(self):
        import inspect

        from viznoir.anim.physics import iso_sweep

        sig = inspect.signature(iso_sweep)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "iso_range" in params

    def test_threshold_reveal_signature(self):
        import inspect

        from viznoir.anim.physics import threshold_reveal

        sig = inspect.signature(threshold_reveal)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "threshold_range" in params

    def test_warp_oscillation_signature(self):
        import inspect

        from viznoir.anim.physics import warp_oscillation

        sig = inspect.signature(warp_oscillation)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "displacement_field" in params
        assert "max_scale" in params
        assert "n_cycles" in params

    def test_light_orbit_signature(self):
        import inspect

        from viznoir.anim.physics import light_orbit

        sig = inspect.signature(light_orbit)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "color" in params

    def test_streamline_growth_signature(self):
        import inspect

        from viznoir.anim.physics import streamline_growth

        sig = inspect.signature(streamline_growth)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "vector_field" in params
        assert "n_seeds" in params
        assert "seed_center" in params


# ---------------------------------------------------------------------------
# Preset defaults
# ---------------------------------------------------------------------------


class TestPresetDefaults:
    def test_clip_sweep_default_axis(self):
        import inspect

        from viznoir.anim.physics import clip_sweep

        sig = inspect.signature(clip_sweep)
        assert sig.parameters["axis"].default == "x"

    def test_clip_sweep_default_bounce(self):
        import inspect

        from viznoir.anim.physics import clip_sweep

        sig = inspect.signature(clip_sweep)
        assert sig.parameters["bounce"].default is True

    def test_warp_oscillation_defaults(self):
        import inspect

        from viznoir.anim.physics import warp_oscillation

        sig = inspect.signature(warp_oscillation)
        assert sig.parameters["max_scale"].default == 25.0
        assert sig.parameters["n_cycles"].default == 2
        assert sig.parameters["displacement_field"].default == "Displacement"

    def test_streamline_growth_defaults(self):
        import inspect

        from viznoir.anim.physics import streamline_growth

        sig = inspect.signature(streamline_growth)
        assert sig.parameters["vector_field"].default == "Velocity"
        assert sig.parameters["n_seeds"].default == 30

    def test_light_orbit_default_color(self):
        import inspect

        from viznoir.anim.physics import light_orbit

        sig = inspect.signature(light_orbit)
        assert sig.parameters["color"].default == (0.5, 0.47, 0.42)


# ---------------------------------------------------------------------------
# Physics docstrings (ensure each explains WHY)
# ---------------------------------------------------------------------------


class TestPhysicsDocstrings:
    """Every preset must have a docstring with 'Physics' explanation."""

    @pytest.mark.parametrize(
        "name",
        [
            "layer_reveal",
            "clip_sweep",
            "iso_sweep",
            "threshold_reveal",
            "warp_oscillation",
            "light_orbit",
            "streamline_growth",
        ],
    )
    def test_has_physics_explanation(self, name):
        import viznoir.anim.physics as mod

        func = getattr(mod, name)
        assert func.__doc__ is not None, f"{name} has no docstring"
        assert "Physics" in func.__doc__, f"{name} docstring must explain physics"
