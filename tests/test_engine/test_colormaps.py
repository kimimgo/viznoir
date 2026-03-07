"""Tests for engine/colormaps.py — colormap presets and LUT building."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from viznoir.engine.colormaps import (
    COLORMAP_REGISTRY,
    build_lut,
    list_colormaps,
)

# ---------------------------------------------------------------------------
# list_colormaps
# ---------------------------------------------------------------------------

class TestListColormaps:
    def test_returns_sorted_list(self):
        result = list_colormaps()
        assert isinstance(result, list)
        assert result == sorted(result)

    def test_includes_core_presets(self):
        result = list_colormaps()
        for name in ("viridis", "cool to warm", "plasma", "inferno", "jet",
                      "magma", "cividis", "twilight",
                      "blue to red rainbow", "x ray"):
            assert name in result

    def test_count_matches_registry(self):
        assert len(list_colormaps()) == len(COLORMAP_REGISTRY)

    def test_no_duplicates(self):
        result = list_colormaps()
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# COLORMAP_REGISTRY
# ---------------------------------------------------------------------------

class TestColormapRegistry:
    def test_all_entries_are_tuples(self):
        for name, points in COLORMAP_REGISTRY.items():
            assert isinstance(points, list), f"{name} is not a list"
            for pt in points:
                assert len(pt) == 4, f"{name} point {pt} doesn't have 4 values"

    def test_positions_are_0_to_1(self):
        for name, points in COLORMAP_REGISTRY.items():
            positions = [pt[0] for pt in points]
            assert positions[0] == pytest.approx(0.0), f"{name} doesn't start at 0"
            assert positions[-1] == pytest.approx(1.0), f"{name} doesn't end at 1"

    def test_rgb_values_in_range(self):
        for name, points in COLORMAP_REGISTRY.items():
            for pt in points:
                for val in pt[1:]:
                    assert 0.0 <= val <= 1.0, f"{name} has out-of-range RGB: {pt}"

    def test_coolwarm_alias(self):
        assert COLORMAP_REGISTRY["coolwarm"] is COLORMAP_REGISTRY["cool to warm"]


# ---------------------------------------------------------------------------
# build_lut (requires VTK mock)
# ---------------------------------------------------------------------------

class TestBuildLut:
    @pytest.fixture
    def mock_vtk(self):
        """Mock the vtk module so tests work without VTK installed."""
        mock = MagicMock()
        mock_ctf = MagicMock()
        mock.vtkColorTransferFunction.return_value = mock_ctf
        return mock, mock_ctf

    def test_build_lut_returns_ctf(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            result = build_lut("viridis")
            assert result is mock_ctf

    def test_build_lut_adds_rgb_points(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis", scalar_range=(0.0, 100.0))
            assert mock_ctf.AddRGBPoint.call_count == len(COLORMAP_REGISTRY["viridis"])

    def test_build_lut_unknown_falls_back(self, mock_vtk):
        """Unknown colormap name should fall back to Cool to Warm."""
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("nonexistent_colormap")
            assert mock_ctf.AddRGBPoint.call_count == len(COLORMAP_REGISTRY["cool to warm"])

    def test_build_lut_case_insensitive(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("VIRIDIS")
            assert mock_ctf.AddRGBPoint.call_count == len(COLORMAP_REGISTRY["viridis"])

    def test_build_lut_linear_scale_default(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis")
            mock_ctf.SetScaleToLinear.assert_called_once()
            mock_ctf.SetScaleToLog10.assert_not_called()

    def test_build_lut_log_scale(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis", scalar_range=(1.0, 100.0), log_scale=True)
            mock_ctf.SetScaleToLog10.assert_called_once()

    def test_build_lut_log_scale_zero_min_stays_linear(self, mock_vtk):
        """Log scale with lo=0 should stay linear (log(0) undefined)."""
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis", scalar_range=(0.0, 100.0), log_scale=True)
            mock_ctf.SetScaleToLinear.assert_called_once()

    def test_build_lut_nan_color(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis", nan_color=(1.0, 0.0, 0.0))
            mock_ctf.SetNanColor.assert_called_once_with(1.0, 0.0, 0.0)

    def test_build_lut_above_range_color(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis", above_range_color=(0.5, 0.0, 0.0))
            mock_ctf.SetAboveRangeColor.assert_called_once_with(0.5, 0.0, 0.0, 1.0)
            mock_ctf.SetUseAboveRangeColor.assert_called_with(True)

    def test_build_lut_below_range_color(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis", below_range_color=(0.0, 0.0, 0.5))
            mock_ctf.SetBelowRangeColor.assert_called_once_with(0.0, 0.0, 0.5, 1.0)
            mock_ctf.SetUseBelowRangeColor.assert_called_with(True)

    def test_build_lut_no_above_below_defaults(self, mock_vtk):
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("viridis")
            mock_ctf.SetUseAboveRangeColor.assert_called_with(False)
            mock_ctf.SetUseBelowRangeColor.assert_called_with(False)

    def test_build_lut_scalar_range_maps_points(self, mock_vtk):
        """Control points should be mapped to [lo, hi] range."""
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            build_lut("grayscale", scalar_range=(10.0, 20.0))
            # Grayscale has 2 points: (0.0,...) and (1.0,...)
            calls = mock_ctf.AddRGBPoint.call_args_list
            assert calls[0][0][0] == pytest.approx(10.0)  # lo + 0.0*(20-10)
            assert calls[1][0][0] == pytest.approx(20.0)  # lo + 1.0*(20-10)

    @pytest.mark.parametrize("name", [
        "blue to red rainbow", "x ray",
    ])
    def test_build_lut_new_colormaps(self, mock_vtk, name):
        """New colormaps (blue to red rainbow, x ray) build successfully."""
        mock, mock_ctf = mock_vtk
        with patch.dict("sys.modules", {"vtk": mock}):
            result = build_lut(name)
            assert result is mock_ctf
            assert mock_ctf.AddRGBPoint.call_count == len(COLORMAP_REGISTRY[name])
