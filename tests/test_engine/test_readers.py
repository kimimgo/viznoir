"""Tests for engine/readers.py — DataReader format detection and metadata (mock VTK)."""

from __future__ import annotations

import json
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

    def test_unsupported_extension_no_meshio(self, tmp_path):
        from parapilot.engine.readers import DataReader
        from parapilot.errors import FileFormatError

        xyz_file = tmp_path / "file.xyz"
        xyz_file.write_text("data")

        reader = DataReader(xyz_file)
        with patch.dict("sys.modules", {"meshio": None}):
            with pytest.raises(FileFormatError, match="Unsupported file format"):
                reader.read()

    def test_unsupported_extension_hint_message(self, tmp_path):
        from parapilot.engine.readers import DataReader
        from parapilot.errors import FileFormatError

        xyz_file = tmp_path / "file.xyz"
        xyz_file.write_text("data")

        reader = DataReader(xyz_file)
        with patch.dict("sys.modules", {"meshio": None}):
            with pytest.raises(FileFormatError, match="pip install mcp-server-parapilot"):
                reader.read()

    def test_typo_extension_suggests_match(self, tmp_path):
        """Test that a typo'd extension like .vtt gets a 'Did you mean .vtu?' suggestion."""
        from parapilot.engine.readers import DataReader
        from parapilot.errors import FileFormatError

        typo_file = tmp_path / "file.vtt"
        typo_file.write_text("data")

        reader = DataReader(typo_file)
        with patch.dict("sys.modules", {"meshio": None}):
            with pytest.raises(FileFormatError, match="Did you mean"):
                reader.read()


class TestFormatSuggestion:
    def test_close_match(self):
        from parapilot.engine.readers import _format_suggestion

        assert _format_suggestion(".vtt") in (".vtk", ".vtp", ".vtu")

    def test_no_match(self):
        from parapilot.engine.readers import _format_suggestion

        assert _format_suggestion(".zzz") is None

    def test_exact_match_not_needed(self):
        from parapilot.engine.readers import _format_suggestion

        # .stll is close to .stl
        result = _format_suggestion(".stll")
        assert result == ".stl"


# ---------------------------------------------------------------------------
# meshio fallback
# ---------------------------------------------------------------------------


class TestMeshioFallback:
    vtk = pytest.importorskip("vtk")

    def test_meshio_to_vtk_conversion(self):
        """Test the _meshio_to_vtk helper with a mock meshio.Mesh."""
        import numpy as np

        from parapilot.engine.readers import _meshio_to_vtk

        mesh = MagicMock()
        mesh.points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        cell_block = MagicMock()
        cell_block.type = "tetra"
        cell_block.data = np.array([[0, 1, 2, 3]])
        mesh.cells = [cell_block]
        mesh.point_data = {"pressure": np.array([1.0, 2.0, 3.0, 4.0])}

        grid = _meshio_to_vtk(mesh)
        assert grid.GetNumberOfPoints() == 4
        assert grid.GetNumberOfCells() == 1
        assert grid.GetPointData().GetArray("pressure") is not None

    def test_meshio_to_vtk_2d_mesh(self):
        """Test 2D mesh is padded to 3D."""
        import numpy as np

        from parapilot.engine.readers import _meshio_to_vtk

        mesh = MagicMock()
        mesh.points = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        cell_block = MagicMock()
        cell_block.type = "triangle"
        cell_block.data = np.array([[0, 1, 2]])
        mesh.cells = [cell_block]
        mesh.point_data = {}

        grid = _meshio_to_vtk(mesh)
        assert grid.GetNumberOfPoints() == 3

    def test_meshio_to_vtk_skips_unknown_cell_types(self):
        """Test that unknown cell types are skipped gracefully."""
        import numpy as np

        from parapilot.engine.readers import _meshio_to_vtk

        mesh = MagicMock()
        mesh.points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        cell_block = MagicMock()
        cell_block.type = "unknown_cell_type_xyz"
        cell_block.data = np.array([[0, 1]])
        mesh.cells = [cell_block]
        mesh.point_data = {}

        grid = _meshio_to_vtk(mesh)
        assert grid.GetNumberOfPoints() == 2
        assert grid.GetNumberOfCells() == 0

    def test_meshio_cell_type_map(self):
        """Test that common cell types are mapped."""
        from parapilot.engine.readers import _MESHIO_TO_VTK_TYPE

        expected = {"vertex", "line", "triangle", "quad", "tetra", "hexahedron", "wedge", "pyramid"}
        assert expected.issubset(set(_MESHIO_TO_VTK_TYPE.keys()))
