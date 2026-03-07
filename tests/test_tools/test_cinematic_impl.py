"""Tests for tools/cinematic.py — cinematic render tool implementation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestCinematicRenderImpl:
    async def test_run_inner_function(self):
        """Test the inner _run function constructs correct configs."""
        with patch("viznoir.engine.readers.read_dataset") as mock_read, \
             patch("viznoir.engine.readers.get_timesteps"), \
             patch("viznoir.engine.renderer_cine.cinematic_render") as mock_cine:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG_test"

            from viznoir.engine.renderer_cine import CinematicConfig

            # Simulate what cinematic_render_impl._run() does
            from viznoir.tools.cinematic import cinematic_render_impl
            runner = MagicMock()

            # Call with await — it uses run_in_executor internally
            result = await cinematic_render_impl(
                file_path="/data/test.vtk",
                runner=runner,
                field_name="pressure",
                colormap="Plasma",
                quality="draft",
                lighting="studio",
                background="white",
                azimuth=45.0,
                elevation=30.0,
                fill_ratio=0.8,
                metallic=0.5,
                roughness=0.3,
                ground_plane=True,
                ssao=False,
                fxaa=True,
                width=800,
                height=600,
                scalar_range=[0.0, 100.0],
            )

            assert result == b"\x89PNG_test"
            mock_read.assert_called_once_with("/data/test.vtk", timestep=None)
            mock_cine.assert_called_once()

            # Verify CinematicConfig
            config = mock_cine.call_args[0][1]
            assert isinstance(config, CinematicConfig)
            assert config.quality == "draft"
            assert config.lighting_preset == "studio"
            assert config.background_preset == "white"
            assert config.azimuth == 45.0
            assert config.elevation == 30.0
            assert config.fill_ratio == 0.8
            assert config.metallic == 0.5
            assert config.roughness == 0.3
            assert config.ground_plane is True
            assert config.ssao is False
            assert config.fxaa is True

            # Verify RenderConfig
            rc = config.render
            assert rc.colormap == "plasma"
            assert rc.array_name == "pressure"
            assert rc.width == 800
            assert rc.height == 600
            assert rc.scalar_range == (0.0, 100.0)

    async def test_latest_timestep_resolution(self):
        """Test that timestep='latest' resolves to last available step."""
        with patch("viznoir.engine.readers.read_dataset") as mock_read, \
             patch("viznoir.engine.readers.get_timesteps") as mock_ts, \
             patch("viznoir.engine.renderer_cine.cinematic_render") as mock_cine:

            mock_ts.return_value = [0.0, 0.5, 1.0, 1.5]
            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"

            from viznoir.tools.cinematic import cinematic_render_impl
            runner = MagicMock()

            await cinematic_render_impl(
                file_path="/data/series.pvd",
                runner=runner,
                timestep="latest",
            )

            mock_ts.assert_called_once_with("/data/series.pvd")
            mock_read.assert_called_once_with("/data/series.pvd", timestep=1.5)

    async def test_string_timestep_conversion(self):
        """Test that string timestep is converted to float."""
        with patch("viznoir.engine.readers.read_dataset") as mock_read, \
             patch("viznoir.engine.renderer_cine.cinematic_render") as mock_cine:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"

            from viznoir.tools.cinematic import cinematic_render_impl
            runner = MagicMock()

            await cinematic_render_impl(
                file_path="/data/test.vtk",
                runner=runner,
                timestep="2.5",
            )

            mock_read.assert_called_once_with("/data/test.vtk", timestep=2.5)

    async def test_no_scalar_range(self):
        """Test rendering without scalar_range."""
        with patch("viznoir.engine.readers.read_dataset") as mock_read, \
             patch("viznoir.engine.renderer_cine.cinematic_render") as mock_cine:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"

            from viznoir.tools.cinematic import cinematic_render_impl
            runner = MagicMock()

            await cinematic_render_impl(
                file_path="/data/test.vtk",
                runner=runner,
            )

            config = mock_cine.call_args[0][1]
            assert config.render.scalar_range is None

    async def test_default_parameters(self):
        """Test that default parameters are applied correctly."""
        with patch("viznoir.engine.readers.read_dataset") as mock_read, \
             patch("viznoir.engine.renderer_cine.cinematic_render") as mock_cine:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"

            from viznoir.tools.cinematic import cinematic_render_impl
            runner = MagicMock()

            await cinematic_render_impl(
                file_path="/data/test.vtk",
                runner=runner,
            )

            config = mock_cine.call_args[0][1]
            assert config.quality == "standard"
            assert config.lighting_preset == "cinematic"
            assert config.background_preset == "dark_gradient"
            assert config.fill_ratio == 0.75
            assert config.metallic == 0.0
            assert config.roughness == 0.5
            assert config.ground_plane is False
            assert config.ssao is True
            assert config.fxaa is True

    async def test_latest_timestep_empty_steps(self):
        """Test timestep='latest' with no available timesteps."""
        with patch("viznoir.engine.readers.read_dataset") as mock_read, \
             patch("viznoir.engine.readers.get_timesteps") as mock_ts, \
             patch("viznoir.engine.renderer_cine.cinematic_render") as mock_cine:

            mock_ts.return_value = []
            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"

            from viznoir.tools.cinematic import cinematic_render_impl
            runner = MagicMock()

            await cinematic_render_impl(
                file_path="/data/test.vtk",
                runner=runner,
                timestep="latest",
            )

            mock_read.assert_called_once_with("/data/test.vtk", timestep=None)
