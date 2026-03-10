"""Tests for viznoir.config — PVConfig and helper functions."""

from __future__ import annotations

from unittest.mock import patch


class TestPVConfig:
    def test_default_config(self):
        from viznoir.config import PVConfig

        config = PVConfig()
        assert config.default_resolution == (1920, 1080)
        assert config.default_timeout == 600.0

    def test_frozen_immutability(self):
        """PVConfig must be frozen (immutable) — mutation test anchor."""
        import pytest

        from viznoir.config import PVConfig

        config = PVConfig()
        with pytest.raises(AttributeError):
            config.default_timeout = 999.0  # type: ignore[misc]

    def test_output_dir_default(self):
        """Default output_dir must be /output."""
        from viznoir.config import PVConfig

        config = PVConfig()
        assert str(config.output_dir) == "/output"

    def test_gpu_device_default(self):
        """Default gpu_device must be 0."""
        from viznoir.config import PVConfig

        config = PVConfig()
        assert config.gpu_device == 0

    def test_python_bin_from_env(self, monkeypatch):
        """VIZNOIR_PYTHON_BIN env var must be respected."""
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_PYTHON_BIN", "/usr/local/bin/python3.11")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert config.python_bin == "/usr/local/bin/python3.11"

    def test_docker_image_default(self):
        """Default docker_image must be viznoir:latest."""
        from viznoir.config import PVConfig

        config = PVConfig()
        assert config.docker_image == "viznoir:latest"

    def test_data_dir_from_env(self, monkeypatch):
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_DATA_DIR", "/test/data")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert str(config.data_dir) == "/test/data"

    def test_data_dir_none_when_unset(self, monkeypatch):
        from importlib import reload

        import viznoir.config

        monkeypatch.delenv("VIZNOIR_DATA_DIR", raising=False)
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert config.data_dir is None

    def test_output_dir_from_env(self, monkeypatch):
        """VIZNOIR_OUTPUT_DIR env var must be respected."""
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_OUTPUT_DIR", "/custom/output")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert str(config.output_dir) == "/custom/output"

    def test_timeout_from_env(self, monkeypatch):
        """VIZNOIR_TIMEOUT env var must be respected."""
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_TIMEOUT", "120")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert config.default_timeout == 120.0

    def test_docker_image_from_env(self, monkeypatch):
        """VIZNOIR_DOCKER_IMAGE env var must be respected."""
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_DOCKER_IMAGE", "my-viznoir:v2")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert config.docker_image == "my-viznoir:v2"

    def test_vtk_backend_from_env(self, monkeypatch):
        """VIZNOIR_VTK_BACKEND env var must be respected."""
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_VTK_BACKEND", "osmesa")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert config.vtk_backend == "osmesa"

    def test_render_backend_from_env(self, monkeypatch):
        """VIZNOIR_RENDER_BACKEND env var must be respected."""
        from importlib import reload

        import viznoir.config

        monkeypatch.setenv("VIZNOIR_RENDER_BACKEND", "cpu")
        reload(viznoir.config)
        config = viznoir.config.PVConfig()
        assert config.render_backend == "cpu"

    def test_use_gpu_true_for_gpu_backend(self):
        from viznoir.config import PVConfig

        config = PVConfig(render_backend="gpu")
        assert config.use_gpu is True

    def test_use_gpu_false_for_cpu_backend(self):
        from viznoir.config import PVConfig

        config = PVConfig(render_backend="cpu")
        assert config.use_gpu is False

    def test_use_gpu_auto_with_gpu_available(self):
        from viznoir.config import PVConfig

        config = PVConfig(render_backend="auto")
        with patch("viznoir.config._gpu_available", return_value=True):
            assert config.use_gpu is True

    def test_use_gpu_auto_without_gpu(self):
        from viznoir.config import PVConfig

        config = PVConfig(render_backend="auto")
        with patch("viznoir.config._gpu_available", return_value=False):
            assert config.use_gpu is False


class TestParseRenderBackend:
    def test_valid_values(self):
        from viznoir.config import _parse_render_backend

        assert _parse_render_backend("gpu") == "gpu"
        assert _parse_render_backend("cpu") == "cpu"
        assert _parse_render_backend("auto") == "auto"

    def test_each_valid_value_returns_itself_not_fallback(self):
        """Ensure gpu/cpu/auto go through the match branch, not the fallback.

        This kills equivalent mutants where the fallback coincidentally
        returns the same value as the match.
        """
        from viznoir.config import _parse_render_backend

        # If "cpu" goes through match branch, result is "cpu".
        # If "cpu" goes through fallback, result is "gpu". So this test
        # verifies the match branch handles "cpu" correctly.
        assert _parse_render_backend("cpu") == "cpu"  # not "gpu"
        assert _parse_render_backend("auto") == "auto"  # not "gpu"

    def test_case_insensitive(self):
        from viznoir.config import _parse_render_backend

        assert _parse_render_backend("GPU") == "gpu"
        assert _parse_render_backend("  Auto  ") == "auto"

    def test_invalid_falls_back_to_gpu(self):
        from viznoir.config import _parse_render_backend

        assert _parse_render_backend("invalid") == "gpu"


class TestParseVtkBackend:
    def test_valid_values(self):
        from viznoir.config import _parse_vtk_backend

        assert _parse_vtk_backend("egl") == "egl"
        assert _parse_vtk_backend("osmesa") == "osmesa"
        assert _parse_vtk_backend("auto") == "auto"

    def test_invalid_falls_back_to_auto(self):
        from viznoir.config import _parse_vtk_backend

        assert _parse_vtk_backend("invalid") == "auto"


class TestGpuAvailable:
    def test_gpu_available_with_nvidia_smi(self):
        from viznoir.config import _gpu_available

        with patch("shutil.which", return_value="/usr/bin/nvidia-smi") as mock_which:
            assert _gpu_available() is True
            mock_which.assert_called_once_with("nvidia-smi")

    def test_gpu_unavailable(self):
        from viznoir.config import _gpu_available

        with patch("shutil.which", return_value=None) as mock_which:
            assert _gpu_available() is False
            mock_which.assert_called_once_with("nvidia-smi")
