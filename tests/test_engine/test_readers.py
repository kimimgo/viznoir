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

    def test_meshio_fallback_success(self, tmp_path):
        """Test meshio fallback success path (lines 258-267)."""
        import numpy as np

        from parapilot.engine.readers import DataReader

        med_file = tmp_path / "mesh.med"
        med_file.write_text("mesh data")

        reader = DataReader(med_file)

        mock_meshio = MagicMock()
        mock_mesh = MagicMock()
        mock_mesh.points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        cell_block = MagicMock()
        cell_block.type = "triangle"
        cell_block.data = np.array([[0, 1, 2]])
        mock_mesh.cells = [cell_block]
        mock_mesh.point_data = {"T": np.array([100.0, 200.0, 300.0])}
        mock_meshio.read.return_value = mock_mesh

        with patch.dict("sys.modules", {"meshio": mock_meshio}):
            data = reader.read()

        assert data.GetNumberOfPoints() == 3
        assert data.GetNumberOfCells() == 1
        assert reader._timesteps == []

    def test_meshio_fallback_read_fails(self, tmp_path):
        """Test meshio fallback when meshio is available but read fails."""
        from parapilot.engine.readers import DataReader
        from parapilot.errors import FileFormatError

        bad_file = tmp_path / "file.med"
        bad_file.write_text("not a real mesh")

        reader = DataReader(bad_file)
        mock_meshio = MagicMock()
        mock_meshio.read.side_effect = Exception("Cannot read")

        with patch.dict("sys.modules", {"meshio": mock_meshio}):
            with pytest.raises(FileFormatError, match="meshio also failed"):
                reader.read()

    def test_meshio_fallback_read_fails_with_hint(self, tmp_path):
        """meshio fail + typo extension includes 'Did you mean' hint."""
        from parapilot.engine.readers import DataReader
        from parapilot.errors import FileFormatError

        typo_file = tmp_path / "file.stll"  # close to .stl
        typo_file.write_text("data")

        reader = DataReader(typo_file)
        mock_meshio = MagicMock()
        mock_meshio.read.side_effect = Exception("Cannot read")

        with patch.dict("sys.modules", {"meshio": mock_meshio}):
            with pytest.raises(FileFormatError, match="Did you mean"):
                reader.read()


# ---------------------------------------------------------------------------
# PVD and Series reader integration
# ---------------------------------------------------------------------------


class TestPvdReader:
    vtk = pytest.importorskip("vtk")

    def test_read_pvd_file(self, tmp_path):
        """DataReader reads PVD files that reference real VTK files."""
        import vtk

        from parapilot.engine.readers import DataReader

        # Create a simple VTU file
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(1, 0, 0)
        pts.InsertNextPoint(0, 1, 0)
        grid = vtk.vtkUnstructuredGrid()
        grid.SetPoints(pts)
        writer = vtk.vtkXMLUnstructuredGridWriter()
        vtu_path = tmp_path / "data_0001.vtu"
        writer.SetFileName(str(vtu_path))
        writer.SetInputData(grid)
        writer.Write()

        # Create PVD referencing it
        pvd_content = """<?xml version="1.0"?>
<VTKFile type="Collection">
  <Collection>
    <DataSet timestep="0.0" file="data_0001.vtu"/>
  </Collection>
</VTKFile>"""
        pvd_path = tmp_path / "case.pvd"
        pvd_path.write_text(pvd_content)

        reader = DataReader(pvd_path)
        data = reader.read()
        assert data.GetNumberOfPoints() == 3

    def test_pvd_empty_raises(self, tmp_path):
        """PVD with no entries raises ValueError."""
        from parapilot.engine.readers import DataReader

        pvd_content = """<?xml version="1.0"?>
<VTKFile type="Collection"><Collection></Collection></VTKFile>"""
        pvd_path = tmp_path / "empty.pvd"
        pvd_path.write_text(pvd_content)

        reader = DataReader(pvd_path)
        with pytest.raises(ValueError, match="No dataset entries"):
            reader.read()

    def test_pvd_missing_file_raises(self, tmp_path):
        """PVD referencing nonexistent file raises FileNotFoundError."""
        from parapilot.engine.readers import DataReader

        pvd_content = """<?xml version="1.0"?>
<VTKFile type="Collection">
  <Collection>
    <DataSet timestep="0.0" file="nonexistent.vtu"/>
  </Collection>
</VTKFile>"""
        pvd_path = tmp_path / "bad.pvd"
        pvd_path.write_text(pvd_content)

        reader = DataReader(pvd_path)
        with pytest.raises(FileNotFoundError, match="PVD references missing file"):
            reader.read()


class TestSeriesReader:
    vtk = pytest.importorskip("vtk")

    def test_read_series_file(self, tmp_path):
        """DataReader reads .vtu.series files."""
        import vtk

        from parapilot.engine.readers import DataReader

        # Create VTU file
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(1, 0, 0)
        grid = vtk.vtkUnstructuredGrid()
        grid.SetPoints(pts)
        writer = vtk.vtkXMLUnstructuredGridWriter()
        vtu_path = tmp_path / "step_0000.vtu"
        writer.SetFileName(str(vtu_path))
        writer.SetInputData(grid)
        writer.Write()

        # Create .vtu.series
        series_data = {
            "file-series-version": "1.0",
            "files": [{"name": "step_0000.vtu", "time": 0.0}],
        }
        series_path = tmp_path / "output.vtu.series"
        series_path.write_text(json.dumps(series_data))

        reader = DataReader(series_path)
        data = reader.read()
        assert data.GetNumberOfPoints() == 2

    def test_series_empty_raises(self, tmp_path):
        """Series with no entries raises ValueError."""
        from parapilot.engine.readers import DataReader

        series_data = {"file-series-version": "1.0", "files": []}
        series_path = tmp_path / "empty.vtu.series"
        series_path.write_text(json.dumps(series_data))

        reader = DataReader(series_path)
        with pytest.raises(ValueError, match="No entries found"):
            reader.read()

    def test_series_missing_file_raises(self, tmp_path):
        """Series referencing nonexistent file raises FileNotFoundError."""
        from parapilot.engine.readers import DataReader

        series_data = {
            "file-series-version": "1.0",
            "files": [{"name": "missing.vtu", "time": 0.0}],
        }
        series_path = tmp_path / "bad.vtu.series"
        series_path.write_text(json.dumps(series_data))

        reader = DataReader(series_path)
        with pytest.raises(FileNotFoundError, match="Series references missing file"):
            reader.read()


# ---------------------------------------------------------------------------
# DataReader close / timestep / properties
# ---------------------------------------------------------------------------

class TestDataReaderProperties:
    def test_close_releases_reader(self, tmp_path):
        from parapilot.engine.readers import DataReader

        vtk_file = tmp_path / "test.vtk"
        vtk_file.write_text("# vtk DataFile Version 2.0\n")
        reader = DataReader(vtk_file)
        reader.close()
        assert reader.timesteps == []

    def test_path_property(self, tmp_path):
        from parapilot.engine.readers import DataReader

        vtk_file = tmp_path / "test.vtk"
        vtk_file.write_text("# vtk\n")
        reader = DataReader(vtk_file)
        assert reader.path == vtk_file.resolve()


# ---------------------------------------------------------------------------
# _extract_info / _get_array_names / _get_block_names / _first_leaf
# ---------------------------------------------------------------------------

class TestExtractInfo:
    vtk = pytest.importorskip("vtk")

    def test_extract_info_from_polydata(self):
        import vtk

        from parapilot.engine.readers import _extract_info

        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(1, 0, 0)
        pd.SetPoints(pts)

        info = _extract_info(pd, "/test.vtp", "vtkXMLPolyDataReader", [0.0, 1.0])
        assert info.num_points == 2
        assert info.timesteps == [0.0, 1.0]
        assert info.reader_type == "vtkXMLPolyDataReader"

    def test_extract_info_from_multiblock(self):
        import vtk

        from parapilot.engine.readers import _extract_info

        mb = vtk.vtkMultiBlockDataSet()
        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pd.SetPoints(pts)
        mb.SetBlock(0, pd)

        info = _extract_info(mb, "/test.vtm", "vtkXMLMultiBlockDataReader", [])
        assert info.num_blocks == 1
        assert info.num_points == 1

    def test_extract_info_empty_multiblock(self):
        import vtk

        from parapilot.engine.readers import _extract_info

        mb = vtk.vtkMultiBlockDataSet()
        info = _extract_info(mb, "/test.vtm", "vtkXMLMultiBlockDataReader", [])
        assert info.num_blocks == 0
        assert info.num_points == 0


class TestGetBlockNames:
    vtk = pytest.importorskip("vtk")

    def test_named_blocks(self):
        import vtk

        from parapilot.engine.readers import _get_block_names

        mb = vtk.vtkMultiBlockDataSet()
        pd = vtk.vtkPolyData()
        mb.SetBlock(0, pd)
        mb.GetMetaData(0).Set(mb.NAME(), "internalMesh")

        names = _get_block_names(mb)
        assert names == ["internalMesh"]

    def test_unnamed_blocks(self):
        import vtk

        from parapilot.engine.readers import _get_block_names

        mb = vtk.vtkMultiBlockDataSet()
        mb.SetBlock(0, vtk.vtkPolyData())
        names = _get_block_names(mb)
        assert names == ["Block_0"]


class TestFirstLeaf:
    vtk = pytest.importorskip("vtk")

    def test_first_leaf_simple(self):
        import vtk

        from parapilot.engine.readers import _first_leaf

        mb = vtk.vtkMultiBlockDataSet()
        pd = vtk.vtkPolyData()
        mb.SetBlock(0, pd)
        assert _first_leaf(mb) is pd

    def test_first_leaf_nested(self):
        import vtk

        from parapilot.engine.readers import _first_leaf

        outer = vtk.vtkMultiBlockDataSet()
        inner = vtk.vtkMultiBlockDataSet()
        pd = vtk.vtkPolyData()
        inner.SetBlock(0, pd)
        outer.SetBlock(0, inner)
        assert _first_leaf(outer) is pd

    def test_first_leaf_empty(self):
        import vtk

        from parapilot.engine.readers import _first_leaf

        mb = vtk.vtkMultiBlockDataSet()
        assert _first_leaf(mb) is None

    def test_first_leaf_skips_none(self):
        import vtk

        from parapilot.engine.readers import _first_leaf

        mb = vtk.vtkMultiBlockDataSet()
        mb.SetNumberOfBlocks(2)
        # Block 0 is None
        pd = vtk.vtkPolyData()
        mb.SetBlock(1, pd)
        assert _first_leaf(mb) is pd


class TestExtractBlocks:
    vtk = pytest.importorskip("vtk")

    def test_extract_named_block(self):
        import vtk

        from parapilot.engine.readers import _extract_blocks

        mb = vtk.vtkMultiBlockDataSet()
        pd1 = vtk.vtkPolyData()
        pd2 = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(1, 2, 3)
        pd2.SetPoints(pts)
        mb.SetBlock(0, pd1)
        mb.SetBlock(1, pd2)
        mb.GetMetaData(0).Set(mb.NAME(), "wall")
        mb.GetMetaData(1).Set(mb.NAME(), "inlet")

        result = _extract_blocks(mb, ["inlet"])
        assert result is pd2

    def test_extract_blocks_fallback(self):
        import vtk

        from parapilot.engine.readers import _extract_blocks

        mb = vtk.vtkMultiBlockDataSet()
        pd = vtk.vtkPolyData()
        mb.SetBlock(0, pd)
        mb.GetMetaData(0).Set(mb.NAME(), "wall")

        result = _extract_blocks(mb, ["nonexistent"])
        assert result is pd


class TestGetArrayNames:
    vtk = pytest.importorskip("vtk")

    def test_none_input(self):
        from parapilot.engine.readers import _get_array_names

        assert _get_array_names(None) == []

    def test_with_arrays(self):
        import numpy as np
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk

        from parapilot.engine.readers import _get_array_names

        pd = vtk.vtkPolyData()
        arr = numpy_to_vtk(np.array([1.0, 2.0, 3.0]))
        arr.SetName("pressure")
        pd.GetPointData().AddArray(arr)

        names = _get_array_names(pd.GetPointData())
        assert "pressure" in names


class TestPublicApiFunctions:
    """Tests for module-level public functions (read_dataset, get_timesteps, etc.)."""
    vtk = pytest.importorskip("vtk")

    def test_read_dataset_basic(self):
        """read_dataset returns data from DataReader."""
        from parapilot.engine.readers import read_dataset

        mock_grid = self.vtk.vtkUnstructuredGrid()
        pts = self.vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        mock_grid.SetPoints(pts)

        with patch("parapilot.engine.readers.DataReader") as mock_dr:
            inst = MagicMock()
            inst.read.return_value = mock_grid
            mock_dr.return_value = inst
            result = read_dataset("/fake/file.vtk")

        assert result is mock_grid
        inst.read.assert_called_once_with(None)

    def test_read_dataset_with_timestep(self):
        """read_dataset passes timestep through."""
        from parapilot.engine.readers import read_dataset

        with patch("parapilot.engine.readers.DataReader") as mock_dr:
            inst = MagicMock()
            inst.read.return_value = MagicMock()
            mock_dr.return_value = inst
            read_dataset("/fake/file.vtk", timestep=2.5)

        inst.read.assert_called_once_with(2.5)

    def test_read_dataset_with_blocks(self):
        """read_dataset extracts blocks from multiblock."""
        from parapilot.engine.readers import read_dataset

        mb = self.vtk.vtkMultiBlockDataSet()
        child = self.vtk.vtkUnstructuredGrid()
        mb.SetBlock(0, child)
        mb.GetMetaData(0).Set(self.vtk.vtkCompositeDataSet.NAME(), "internalMesh")

        with patch("parapilot.engine.readers.DataReader") as mock_dr:
            inst = MagicMock()
            inst.read.return_value = mb
            mock_dr.return_value = inst
            result = read_dataset("/fake/file.vtk", blocks=["internalMesh"])

        assert result is not None

    def test_get_timesteps(self):
        """get_timesteps returns timesteps list."""
        from parapilot.engine.readers import get_timesteps

        with patch("parapilot.engine.readers.DataReader") as mock_dr:
            inst = MagicMock()
            inst.read.return_value = MagicMock()
            inst.timesteps = [0.0, 1.0, 2.0]
            mock_dr.return_value = inst
            result = get_timesteps("/fake/file.vtk")

        assert result == [0.0, 1.0, 2.0]

    def test_list_arrays(self):
        """list_arrays returns dict with point/cell/field keys."""
        from parapilot.engine.readers import DatasetInfo, list_arrays

        info = DatasetInfo(
            file_path="/fake.vtk",
            reader_type="vtkXMLUnstructuredGridReader",
            dataset_type="vtkUnstructuredGrid",
            num_points=100,
            num_cells=50,
            bounds=(0, 1, 0, 1, 0, 1),
            point_arrays=["velocity", "pressure"],
            cell_arrays=["cellType"],
            field_arrays=[],
            num_blocks=0,
            block_names=[],
            timesteps=[],
        )
        with patch("parapilot.engine.readers.DataReader") as mock_dr:
            inst = MagicMock()
            inst.get_info.return_value = info
            mock_dr.return_value = inst
            result = list_arrays("/fake.vtk")

        assert result["point"] == ["velocity", "pressure"]
        assert result["cell"] == ["cellType"]
        assert result["field"] == []

    def test_list_blocks(self):
        """list_blocks returns block name list."""
        from parapilot.engine.readers import DatasetInfo, list_blocks

        info = DatasetInfo(
            file_path="/fake.vtk",
            reader_type="vtkOpenFOAMReader",
            dataset_type="vtkMultiBlockDataSet",
            num_points=100,
            num_cells=50,
            bounds=(0, 1, 0, 1, 0, 1),
            point_arrays=[],
            cell_arrays=[],
            field_arrays=[],
            num_blocks=2,
            block_names=["internalMesh", "wall"],
            timesteps=[],
        )
        with patch("parapilot.engine.readers.DataReader") as mock_dr:
            inst = MagicMock()
            inst.get_info.return_value = info
            mock_dr.return_value = inst
            result = list_blocks("/fake.vtk")

        assert result == ["internalMesh", "wall"]


class TestPvdParserEdgeCases:
    """Test edge cases in PVD parsing."""

    def test_pvd_dataset_without_file_skipped(self, tmp_path):
        """DataSet element without 'file' attribute is skipped (line 394)."""
        pvd = tmp_path / "test.pvd"
        pvd.write_text("""\
<?xml version="1.0"?>
<VTKFile type="Collection">
  <Collection>
    <DataSet timestep="0.0" file="data_0.vtu"/>
    <DataSet timestep="1.0" />
    <DataSet timestep="2.0" file="data_2.vtu"/>
  </Collection>
</VTKFile>""")
        entries = _parse_pvd(pvd)
        assert len(entries) == 2
        assert entries[0].file == "data_0.vtu"
        assert entries[1].file == "data_2.vtu"


class TestExtractTimestepsWithData:
    """Test _extract_timesteps with actual VTK mocks for TIME_STEPS key."""
    vtk = pytest.importorskip("vtk")

    def test_with_time_steps(self):
        """_extract_timesteps returns times when TIME_STEPS key is present."""
        from parapilot.engine.readers import _extract_timesteps

        exe = MagicMock()
        out_info = MagicMock()
        out_info.Has.return_value = True
        out_info.Length.return_value = 3
        out_info.Get.side_effect = [0.0, 0.5, 1.0]
        exe.GetOutputInformation.return_value = out_info

        reader = MagicMock()
        reader.GetExecutive.return_value = exe
        result = _extract_timesteps(reader)
        assert result == [0.0, 0.5, 1.0]


class TestExtractTimesteps:
    vtk = pytest.importorskip("vtk")

    def test_no_executive(self):
        from unittest.mock import MagicMock

        from parapilot.engine.readers import _extract_timesteps

        reader = MagicMock()
        reader.GetExecutive.return_value = None
        assert _extract_timesteps(reader) == []

    def test_no_output_info(self):
        from unittest.mock import MagicMock

        from parapilot.engine.readers import _extract_timesteps

        exe = MagicMock()
        exe.GetOutputInformation.return_value = None
        reader = MagicMock()
        reader.GetExecutive.return_value = exe
        assert _extract_timesteps(reader) == []
