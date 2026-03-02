"""Tests for engine/export.py — data inspection, stats, and file export."""

from __future__ import annotations

import pytest

from parapilot.engine.export import (
    _WRITER_MAP,
    supported_export_formats,
)


class TestWriterMap:
    def test_includes_core_formats(self):
        for ext in (".vtu", ".vtp", ".stl", ".vtk", ".csv"):
            assert ext in _WRITER_MAP

    @pytest.mark.parametrize("ext,expected_class", [
        (".vtu", "vtkXMLUnstructuredGridWriter"),
        (".vtp", "vtkXMLPolyDataWriter"),
        (".vtk", "vtkGenericDataObjectWriter"),
        (".stl", "vtkSTLWriter"),
        (".ply", "vtkPLYWriter"),
        (".csv", "__csv__"),
    ])
    def test_format_mapping(self, ext, expected_class):
        assert _WRITER_MAP[ext] == expected_class


class TestSupportedExportFormats:
    def test_returns_sorted_list(self):
        result = supported_export_formats()
        assert isinstance(result, list)
        assert result == sorted(result)

    def test_includes_core_formats(self):
        result = supported_export_formats()
        for ext in (".vtu", ".stl", ".csv"):
            assert ext in result
