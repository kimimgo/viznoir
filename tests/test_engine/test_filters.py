"""Tests for engine/filters.py — VTK filter chain (mock VTK)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from viznoir.engine.filters import (
    _FILTER_REGISTRY,
    apply_filter,
    apply_filters,
    clean_polydata,
    list_filters,
    probe_point,
    shrink,
    smooth_mesh,
    tube,
)

# ---------------------------------------------------------------------------
# list_filters
# ---------------------------------------------------------------------------


class TestListFilters:
    def test_returns_sorted_list(self):
        result = list_filters()
        assert isinstance(result, list)
        assert result == sorted(result)

    def test_includes_core_filters(self):
        result = list_filters()
        for name in ("slice", "clip", "contour", "threshold", "calculator", "streamlines"):
            assert name in result


# ---------------------------------------------------------------------------
# _FILTER_REGISTRY
# ---------------------------------------------------------------------------


class TestFilterRegistry:
    def test_all_entries_are_callable(self):
        for name, func in _FILTER_REGISTRY.items():
            assert callable(func), f"{name} is not callable"

    def test_registry_count(self):
        assert len(_FILTER_REGISTRY) >= 25


# ---------------------------------------------------------------------------
# apply_filter
# ---------------------------------------------------------------------------


class TestApplyFilter:
    def test_unknown_filter_raises(self):
        mock_data = MagicMock()
        with pytest.raises(ValueError, match="Unknown filter"):
            apply_filter(mock_data, "nonexistent_filter")

    def test_known_filter_calls_function(self):
        mock_data = MagicMock()
        mock_func = MagicMock(return_value=mock_data)

        with patch.dict(_FILTER_REGISTRY, {"test_filter": mock_func}):
            result = apply_filter(mock_data, "test_filter", key="value")
            mock_func.assert_called_once_with(mock_data, key="value")
            assert result is mock_data


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------


class TestApplyFilters:
    def test_empty_chain_returns_input(self):
        mock_data = MagicMock()
        result = apply_filters(mock_data, [])
        assert result is mock_data

    def test_chain_applies_sequentially(self):
        data_in = MagicMock(name="input")
        data_mid = MagicMock(name="mid")
        data_out = MagicMock(name="output")

        mock_f1 = MagicMock(return_value=data_mid)
        mock_f2 = MagicMock(return_value=data_out)

        with patch.dict(_FILTER_REGISTRY, {"f1": mock_f1, "f2": mock_f2}):
            result = apply_filters(
                data_in,
                [
                    ("f1", {"key1": "val1"}),
                    ("f2", {"key2": "val2"}),
                ],
            )

        mock_f1.assert_called_once_with(data_in, key1="val1")
        mock_f2.assert_called_once_with(data_mid, key2="val2")
        assert result is data_out


# ---------------------------------------------------------------------------
# New filter functions (real VTK)
# ---------------------------------------------------------------------------

vtk = pytest.importorskip("vtk")


def _make_sphere() -> vtk.vtkPolyData:
    """Create a simple sphere polydata for testing."""
    src = vtk.vtkSphereSource()
    src.SetThetaResolution(16)
    src.SetPhiResolution(16)
    src.Update()
    return src.GetOutput()


def _make_line() -> vtk.vtkPolyData:
    """Create a simple line polydata for testing."""
    line = vtk.vtkLineSource()
    line.SetPoint1(0, 0, 0)
    line.SetPoint2(1, 0, 0)
    line.SetResolution(10)
    line.Update()
    return line.GetOutput()


def _make_wavelet() -> vtk.vtkImageData:
    """Create a wavelet image data for testing."""
    src = vtk.vtkRTAnalyticSource()
    src.Update()
    return src.GetOutput()


class TestSmoothMesh:
    def test_smooths_polydata(self):
        sphere = _make_sphere()
        result = smooth_mesh(sphere, iterations=10, relaxation_factor=0.2)
        assert isinstance(result, vtk.vtkPolyData)
        assert result.GetNumberOfPoints() > 0

    def test_converts_non_polydata(self):
        wavelet = _make_wavelet()
        result = smooth_mesh(wavelet)
        assert isinstance(result, vtk.vtkPolyData)
        assert result.GetNumberOfPoints() > 0

    def test_registry_aliases(self):
        assert "smooth_mesh" in _FILTER_REGISTRY
        assert "smooth" in _FILTER_REGISTRY


class TestProbePoint:
    def test_probes_at_point(self):
        wavelet = _make_wavelet()
        result = probe_point(wavelet, point=(0.0, 0.0, 0.0))
        assert isinstance(result, vtk.vtkPolyData)
        assert result.GetNumberOfPoints() == 1

    def test_registry_aliases(self):
        assert "probe_point" in _FILTER_REGISTRY
        assert "probe" in _FILTER_REGISTRY


class TestCleanPolydata:
    def test_cleans_polydata(self):
        sphere = _make_sphere()
        original_points = sphere.GetNumberOfPoints()
        result = clean_polydata(sphere)
        assert isinstance(result, vtk.vtkPolyData)
        assert result.GetNumberOfPoints() <= original_points

    def test_with_tolerance(self):
        sphere = _make_sphere()
        result = clean_polydata(sphere, tolerance=0.1)
        assert isinstance(result, vtk.vtkPolyData)
        assert result.GetNumberOfPoints() > 0

    def test_registry_aliases(self):
        assert "clean_polydata" in _FILTER_REGISTRY
        assert "clean" in _FILTER_REGISTRY


class TestShrink:
    def test_shrinks_cells(self):
        wavelet = _make_wavelet()
        result = shrink(wavelet, shrink_factor=0.5)
        assert result.GetNumberOfCells() > 0

    def test_registry_entry(self):
        assert "shrink" in _FILTER_REGISTRY


class TestTube:
    def test_adds_tube_to_lines(self):
        line = _make_line()
        result = tube(line, radius=0.05, sides=12)
        assert isinstance(result, vtk.vtkPolyData)
        assert result.GetNumberOfPoints() > line.GetNumberOfPoints()

    def test_registry_entry(self):
        assert "tube" in _FILTER_REGISTRY
