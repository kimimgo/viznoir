"""Tests for engine/readers.py using actual VTK data (no mocks)."""

from __future__ import annotations

import pytest
import vtk

from viznoir.engine.readers import (
    DataReader,
    DatasetInfo,
    _extract_info,
    _first_leaf,
    _get_array_names,
    _get_block_names,
    get_timesteps,
    list_arrays,
    list_blocks,
    read_dataset,
)


@pytest.fixture
def vtu_file(tmp_path):
    """Create a minimal VTU file with point and cell data."""
    grid = vtk.vtkUnstructuredGrid()
    pts = vtk.vtkPoints()
    pts.InsertNextPoint(0, 0, 0)
    pts.InsertNextPoint(1, 0, 0)
    pts.InsertNextPoint(0, 1, 0)
    pts.InsertNextPoint(0, 0, 1)
    grid.SetPoints(pts)

    cell = vtk.vtkTetra()
    for i in range(4):
        cell.GetPointIds().SetId(i, i)
    grid.InsertNextCell(cell.GetCellType(), cell.GetPointIds())

    # Add point data
    pressure = vtk.vtkFloatArray()
    pressure.SetName("pressure")
    pressure.SetNumberOfTuples(4)
    for i in range(4):
        pressure.SetValue(i, float(i) * 10.0)
    grid.GetPointData().AddArray(pressure)

    # Add cell data
    region = vtk.vtkIntArray()
    region.SetName("region")
    region.SetNumberOfTuples(1)
    region.SetValue(0, 42)
    grid.GetCellData().AddArray(region)

    # Write
    out = tmp_path / "test.vtu"
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(str(out))
    writer.SetInputData(grid)
    writer.Write()
    return out


@pytest.fixture
def vtp_file(tmp_path):
    """Create a minimal VTP polydata file."""
    sphere = vtk.vtkSphereSource()
    sphere.SetThetaResolution(8)
    sphere.SetPhiResolution(6)
    sphere.Update()

    out = tmp_path / "sphere.vtp"
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(str(out))
    writer.SetInputData(sphere.GetOutput())
    writer.Write()
    return out


class TestReadDataset:
    def test_read_vtu(self, vtu_file):
        data = read_dataset(str(vtu_file))
        assert data is not None
        assert data.GetNumberOfPoints() == 4
        assert data.GetNumberOfCells() == 1

    def test_read_vtp(self, vtp_file):
        data = read_dataset(str(vtp_file))
        assert data is not None
        assert data.GetNumberOfPoints() > 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_dataset("/nonexistent/data.vtu")


class TestGetTimesteps:
    def test_static_file_no_timesteps(self, vtu_file):
        steps = get_timesteps(str(vtu_file))
        assert steps == []


class TestListArrays:
    def test_list_arrays_vtu(self, vtu_file):
        arrays = list_arrays(str(vtu_file))
        assert "point" in arrays
        assert "cell" in arrays
        assert "field" in arrays
        assert "pressure" in arrays["point"]
        assert "region" in arrays["cell"]

    def test_list_arrays_vtp(self, vtp_file):
        arrays = list_arrays(str(vtp_file))
        assert isinstance(arrays["point"], list)


class TestListBlocks:
    def test_non_multiblock(self, vtu_file):
        blocks = list_blocks(str(vtu_file))
        assert blocks == []


class TestDataReader:
    def test_read_returns_dataset(self, vtu_file):
        reader = DataReader(vtu_file)
        data = reader.read()
        assert data is not None

    def test_get_info_returns_datasetinfo(self, vtu_file):
        reader = DataReader(vtu_file)
        info = reader.get_info()
        assert isinstance(info, DatasetInfo)
        assert info.num_points == 4
        assert info.num_cells == 1
        assert "pressure" in info.point_arrays
        assert "region" in info.cell_arrays

    def test_path_property(self, vtu_file):
        reader = DataReader(vtu_file)
        assert reader.path == vtu_file.resolve()


class TestHelpers:
    def test_get_array_names_none(self):
        result = _get_array_names(None)
        assert result == []

    def test_get_array_names_real(self):
        grid = vtk.vtkUnstructuredGrid()
        arr = vtk.vtkFloatArray()
        arr.SetName("test_arr")
        grid.GetPointData().AddArray(arr)
        names = _get_array_names(grid.GetPointData())
        assert "test_arr" in names

    def test_first_leaf_empty(self):
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetNumberOfBlocks(0)
        assert _first_leaf(mb) is None

    def test_first_leaf_with_data(self):
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetNumberOfBlocks(2)
        mb.SetBlock(0, None)
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        grid.SetPoints(pts)
        mb.SetBlock(1, grid)
        leaf = _first_leaf(mb)
        assert leaf is not None
        assert leaf.GetNumberOfPoints() == 1

    def test_get_block_names(self):
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetNumberOfBlocks(2)
        mb.GetMetaData(0).Set(mb.NAME(), "mesh_a")
        mb.GetMetaData(1).Set(mb.NAME(), "mesh_b")
        names = _get_block_names(mb)
        assert names == ["mesh_a", "mesh_b"]

    def test_extract_info(self):
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(1, 1, 1)
        grid.SetPoints(pts)

        info = _extract_info(grid, "/test.vtu", "vtkXMLUnstructuredGridReader", [])
        assert info.num_points == 2
        assert info.file_path == "/test.vtu"
        assert info.timesteps == []
