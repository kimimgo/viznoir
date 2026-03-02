"""Tests for engine/filters.py — VTK filter chain (mock VTK)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from parapilot.engine.filters import (
    _FILTER_REGISTRY,
    apply_filter,
    apply_filters,
    list_filters,
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
        assert len(_FILTER_REGISTRY) >= 18


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
            result = apply_filters(data_in, [
                ("f1", {"key1": "val1"}),
                ("f2", {"key2": "val2"}),
            ])

        mock_f1.assert_called_once_with(data_in, key1="val1")
        mock_f2.assert_called_once_with(data_mid, key2="val2")
        assert result is data_out
