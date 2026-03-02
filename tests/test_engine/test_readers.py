"""Tests for engine/readers.py — DataReader format detection and metadata (mock VTK)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parapilot.engine.readers import (
    _READER_MAP,
    _parse_pvd,
    _parse_series,
    supported_extensions,
)


# ---------------------------------------------------------------------------
# supported_extensions
# ---------------------------------------------------------------------------

class TestSupportedExtensions:
    def test_returns_sorted_list(self):
        result = supported_extensions()
        assert isinstance(result, list)
        # .series at end, but rest should be sorted
        exts_without_series = [e for e in result if e != ".series"]
        assert exts_without_series == sorted(exts_without_series)

    def test_includes_core_formats(self):
        result = supported_extensions()
        for ext in (".vtk", ".vtu", ".vtp", ".stl", ".foam", ".pvd"):
            assert ext in result

    def test_includes_series(self):
        assert ".series" in supported_extensions()


# ---------------------------------------------------------------------------
# _READER_MAP
# ---------------------------------------------------------------------------

class TestReaderMap:
    def test_vtk_legacy(self):
        assert _READER_MAP[".vtk"][0] == "vtkGenericDataObjectReader"

    def test_openfoam(self):
        assert _READER_MAP[".foam"][0] == "vtkOpenFOAMReader"

    def test_stl(self):
        assert _READER_MAP[".stl"][0] == "vtkSTLReader"

    def test_pvd_is_special(self):
        assert _READER_MAP[".pvd"][0] == "__pvd__"

    @pytest.mark.parametrize("ext,expected_class", [
        (".vtu", "vtkXMLUnstructuredGridReader"),
        (".vtp", "vtkXMLPolyDataReader"),
        (".vts", "vtkXMLStructuredGridReader"),
        (".vti", "vtkXMLImageDataReader"),
        (".vtr", "vtkXMLRectilinearGridReader"),
        (".vtm", "vtkXMLMultiBlockDataReader"),
        (".cgns", "vtkCGNSReader"),
        (".exo", "vtkExodusIIReader"),
        (".e", "vtkExodusIIReader"),
        (".case", "vtkGenericEnSightReader"),
        (".xdmf", "vtkXdmf3Reader"),
    ])
    def test_format_mapping(self, ext, expected_class):
        assert _READER_MAP[ext][0] == expected_class


# ---------------------------------------------------------------------------
# PVD parsing
# ---------------------------------------------------------------------------

class TestParsePvd:
    def test_parse_valid_pvd(self, tmp_path):
        pvd_content = """<?xml version="1.0"?>
<VTKFile type="Collection">
  <Collection>
    <DataSet timestep="0.0" file="data_0000.vtu" part="0"/>
    <DataSet timestep="0.5" file="data_0001.vtu" part="0"/>
    <DataSet timestep="1.0" file="data_0002.vtu" part="0"/>
  </Collection>
</VTKFile>"""
        pvd_file = tmp_path / "case.pvd"
        pvd_file.write_text(pvd_content)

        entries = _parse_pvd(pvd_file)
        assert len(entries) == 3
        assert entries[0].time == pytest.approx(0.0)
        assert entries[0].file == "data_0000.vtu"
        assert entries[2].time == pytest.approx(1.0)

    def test_parse_empty_pvd(self, tmp_path):
        pvd_content = """<?xml version="1.0"?>
<VTKFile type="Collection">
  <Collection>
  </Collection>
</VTKFile>"""
        pvd_file = tmp_path / "empty.pvd"
        pvd_file.write_text(pvd_content)

        entries = _parse_pvd(pvd_file)
        assert entries == []

    def test_parse_pvd_sorted_by_time(self, tmp_path):
        pvd_content = """<?xml version="1.0"?>
<VTKFile type="Collection">
  <Collection>
    <DataSet timestep="1.0" file="b.vtu"/>
    <DataSet timestep="0.0" file="a.vtu"/>
    <DataSet timestep="0.5" file="c.vtu"/>
  </Collection>
</VTKFile>"""
        pvd_file = tmp_path / "unsorted.pvd"
        pvd_file.write_text(pvd_content)

        entries = _parse_pvd(pvd_file)
        times = [e.time for e in entries]
        assert times == sorted(times)


# ---------------------------------------------------------------------------
# Series parsing
# ---------------------------------------------------------------------------

class TestParseSeries:
    def test_parse_valid_series(self, tmp_path):
        series_data = {
            "file-series-version": "1.0",
            "files": [
                {"name": "data_0000.vtu", "time": 0.0},
                {"name": "data_0001.vtu", "time": 0.5},
                {"name": "data_0002.vtu", "time": 1.0},
            ],
        }
        series_file = tmp_path / "case.vtu.series"
        series_file.write_text(json.dumps(series_data))

        entries = _parse_series(series_file)
        assert len(entries) == 3
        assert entries[0].time == pytest.approx(0.0)
        assert entries[0].file == "data_0000.vtu"

    def test_parse_empty_series(self, tmp_path):
        series_data = {"file-series-version": "1.0", "files": []}
        series_file = tmp_path / "empty.vtu.series"
        series_file.write_text(json.dumps(series_data))

        entries = _parse_series(series_file)
        assert entries == []


# ---------------------------------------------------------------------------
# DataReader (requires VTK mock)
# ---------------------------------------------------------------------------

class TestDataReaderInit:
    def test_file_not_found_raises(self):
        from parapilot.engine.readers import DataReader

        with pytest.raises(FileNotFoundError, match="File not found"):
            DataReader("/nonexistent/file.vtk")

    def test_accepts_existing_file(self, tmp_path):
        from parapilot.engine.readers import DataReader

        vtk_file = tmp_path / "test.vtk"
        vtk_file.write_text("# vtk DataFile Version 2.0\n")

        reader = DataReader(vtk_file)
        assert reader.path == vtk_file.resolve()

    def test_unsupported_extension(self, tmp_path):
        from parapilot.engine.readers import DataReader

        xyz_file = tmp_path / "file.xyz"
        xyz_file.write_text("data")

        reader = DataReader(xyz_file)
        with pytest.raises(ValueError, match="Unsupported file format"):
            reader.read()
