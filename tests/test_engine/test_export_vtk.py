"""Integration tests for engine/export.py — real VTK execution."""

from __future__ import annotations

import pytest

vtk = pytest.importorskip("vtk")


def _wavelet() -> vtk.vtkImageData:
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
    src.Update()
    return src.GetOutput()


def _sphere() -> vtk.vtkPolyData:
    src = vtk.vtkSphereSource()
    src.SetRadius(1.0)
    src.Update()
    return src.GetOutput()


def _multiblock() -> vtk.vtkMultiBlockDataSet:
    mb = vtk.vtkMultiBlockDataSet()
    mb.SetBlock(0, _wavelet())
    mb.GetMetaData(0).Set(vtk.vtkCompositeDataSet.NAME(), "wavelet")
    mb.SetBlock(1, _sphere())
    mb.GetMetaData(1).Set(vtk.vtkCompositeDataSet.NAME(), "sphere")
    return mb


# ---------------------------------------------------------------------------
# inspect_dataset
# ---------------------------------------------------------------------------


class TestInspectDataset:
    def test_inspect_imagedata(self):
        from viznoir.engine.export import inspect_dataset

        info = inspect_dataset(_wavelet())
        assert "ImageData" in info["type"]
        assert info["num_points"] > 0
        assert info["num_cells"] > 0
        assert len(info["bounds"]) == 6
        assert len(info["point_arrays"]) > 0
        assert info["point_arrays"][0]["name"] == "RTData"

    def test_inspect_polydata(self):
        from viznoir.engine.export import inspect_dataset

        info = inspect_dataset(_sphere())
        assert "PolyData" in info["type"]
        assert info["num_points"] > 0

    def test_inspect_multiblock(self):
        from viznoir.engine.export import inspect_dataset

        info = inspect_dataset(_multiblock())
        assert info["multiblock"] is not None
        assert len(info["multiblock"]) == 2
        assert info["multiblock"][0]["name"] == "wavelet"
        assert info["multiblock"][1]["name"] == "sphere"

    def test_inspect_multiblock_nested(self):
        from viznoir.engine.export import inspect_dataset

        outer = vtk.vtkMultiBlockDataSet()
        inner = vtk.vtkMultiBlockDataSet()
        inner.SetBlock(0, _wavelet())
        outer.SetBlock(0, inner)
        info = inspect_dataset(outer)
        assert info["multiblock"][0].get("children") is not None

    def test_inspect_multiblock_with_none_block(self):
        from viznoir.engine.export import inspect_dataset

        mb = vtk.vtkMultiBlockDataSet()
        mb.SetBlock(0, None)
        mb.SetBlock(1, _wavelet())
        info = inspect_dataset(mb)
        assert info["multiblock"][0]["num_points"] == 0
        assert info["multiblock"][0]["type"] == "None"


# ---------------------------------------------------------------------------
# extract_stats
# ---------------------------------------------------------------------------


class TestExtractStats:
    def test_stats_scalar(self):
        from viznoir.engine.export import extract_stats

        stats = extract_stats(_wavelet(), fields=["RTData"])
        assert "RTData" in stats
        s = stats["RTData"]
        assert s["min"] < s["max"]
        assert s["association"] == "point"
        assert s["components"] == 1

    def test_stats_all_fields(self):
        from viznoir.engine.export import extract_stats

        stats = extract_stats(_wavelet())
        assert "RTData" in stats

    def test_stats_vector(self):
        """Test vector field stats with per-component + magnitude."""
        from viznoir.engine.export import extract_stats

        # Create dataset with vector field
        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("velocity")
        calc.SetFunction("RTData*iHat + RTData*0.5*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()

        stats = extract_stats(calc.GetOutput(), fields=["velocity"])
        assert "velocity" in stats
        s = stats["velocity"]
        assert s["components"] == 3
        assert isinstance(s["min"], list)
        assert "magnitude" in s

    def test_stats_multiblock(self):
        from viznoir.engine.export import extract_stats

        stats = extract_stats(_multiblock())
        # Should extract from first leaf block
        assert "RTData" in stats

    def test_stats_nonexistent_field(self):
        from viznoir.engine.export import extract_stats

        stats = extract_stats(_wavelet(), fields=["nonexistent"])
        assert "nonexistent" not in stats


# ---------------------------------------------------------------------------
# extract_data
# ---------------------------------------------------------------------------


class TestExtractData:
    def test_extract_basic(self):
        from viznoir.engine.export import extract_data

        data = extract_data(_wavelet(), fields=["RTData"])
        assert "RTData" in data
        assert isinstance(data["RTData"], list)
        assert len(data["RTData"]) > 0

    def test_extract_with_coords(self):
        from viznoir.engine.export import extract_data

        data = extract_data(_wavelet(), fields=["RTData"], include_coords=True)
        assert "x" in data
        assert "y" in data
        assert "z" in data
        assert len(data["x"]) == len(data["RTData"])

    def test_extract_all_fields(self):
        from viznoir.engine.export import extract_data

        data = extract_data(_wavelet())
        assert "RTData" in data

    def test_extract_multiblock(self):
        from viznoir.engine.export import extract_data

        data = extract_data(_multiblock())
        assert "RTData" in data


# ---------------------------------------------------------------------------
# export_file
# ---------------------------------------------------------------------------


class TestExportFile:
    def test_export_vtu(self, tmp_path):
        from viznoir.engine.export import export_file

        out = tmp_path / "test.vtu"
        # Need unstructured grid
        conv = vtk.vtkDataSetTriangleFilter()
        conv.SetInputData(_wavelet())
        conv.Update()
        result = export_file(conv.GetOutput(), out)
        assert result["format"] == ".vtu"
        assert result["size_bytes"] > 0
        assert out.exists()

    def test_export_vtp(self, tmp_path):
        from viznoir.engine.export import export_file

        out = tmp_path / "test.vtp"
        result = export_file(_sphere(), out)
        assert result["format"] == ".vtp"
        assert out.exists()

    def test_export_stl(self, tmp_path):
        from viznoir.engine.export import export_file

        out = tmp_path / "test.stl"
        result = export_file(_sphere(), out)
        assert result["format"] == ".stl"
        assert out.exists()

    def test_export_csv(self, tmp_path):
        from viznoir.engine.export import export_file

        out = tmp_path / "test.csv"
        result = export_file(_wavelet(), out)
        assert result["format"] == ".csv"
        assert out.exists()
        content = out.read_text()
        assert "RTData" in content

    def test_export_unsupported_format(self, tmp_path):
        from viznoir.engine.export import export_file

        with pytest.raises(ValueError, match="Unsupported export format"):
            export_file(_wavelet(), tmp_path / "test.xyz")

    def test_export_vtk_generic(self, tmp_path):
        from viznoir.engine.export import export_file

        out = tmp_path / "test.vtk"
        result = export_file(_wavelet(), out)
        assert result["format"] == ".vtk"
        assert out.exists()

    def test_export_stl_auto_convert(self, tmp_path):
        """STL export auto-converts non-polydata to polydata."""
        from viznoir.engine.export import export_file

        out = tmp_path / "converted.stl"
        result = export_file(_wavelet(), out)
        assert result["format"] == ".stl"
        assert out.exists()


# ---------------------------------------------------------------------------
# get_leaf_block
# ---------------------------------------------------------------------------


class TestGetLeafBlock:
    def test_leaf_from_multiblock(self):
        from viznoir.engine.export import get_leaf_block

        leaf = get_leaf_block(_multiblock())
        assert leaf is not None
        assert leaf.GetNumberOfPoints() > 0

    def test_leaf_from_dataset(self):
        from viznoir.engine.export import get_leaf_block

        leaf = get_leaf_block(_wavelet())
        assert leaf is _wavelet() or leaf is not None

    def test_leaf_empty_multiblock(self):
        from viznoir.engine.export import get_leaf_block

        mb = vtk.vtkMultiBlockDataSet()
        leaf = get_leaf_block(mb)
        assert leaf is None


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


class TestExportCsvVector:
    def test_csv_with_vector_field(self, tmp_path):
        """CSV export with multi-component vector field (lines 333-339)."""
        from viznoir.engine.export import export_file

        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("velocity")
        calc.SetFunction("RTData*iHat + RTData*0.5*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()

        out = tmp_path / "vec.csv"
        result = export_file(calc.GetOutput(), out)
        assert result["format"] == ".csv"
        content = out.read_text()
        assert "velocity_0" in content
        assert "velocity_1" in content
        assert "velocity_2" in content


class TestExportCellData:
    def test_stats_cell_data(self):
        """extract_stats with cell-associated data (lines 475-477)."""
        from viznoir.engine.export import extract_stats
        from viznoir.engine.filters import point_to_cell

        data = point_to_cell(_wavelet())
        stats = extract_stats(data, fields=["RTData"])
        assert "RTData" in stats
        assert stats["RTData"]["association"] == "cell"

    def test_extract_cell_data(self):
        """extract_data with cell-associated data (lines 475-477)."""
        from viznoir.engine.export import extract_data
        from viznoir.engine.filters import point_to_cell

        data = point_to_cell(_wavelet())
        result = extract_data(data, fields=["RTData"])
        assert "RTData" in result
        assert len(result["RTData"]) > 0


class TestEnsureDatasetNonDataset:
    def test_non_dataset_returns_none(self):
        """_ensure_dataset with non-dataset returns None (line 421)."""
        from viznoir.engine.export import _ensure_dataset

        result = _ensure_dataset("not a dataset")
        assert result is None


# ---------------------------------------------------------------------------
# _array_info_list edge cases (L73, 79, 82)
# ---------------------------------------------------------------------------


class TestArrayInfoList:
    """Tests for _array_info_list edge cases via inspect_dataset."""

    def test_array_info_none_attrs(self):
        """L73: _array_info_list with None attrs returns empty list."""
        from viznoir.engine.export import _array_info_list

        result = _array_info_list(None)
        assert result == []

    def test_array_info_none_array_name(self):
        """L79: Arrays with None name are skipped."""
        # Create a vtkFieldData with an array that has no name
        import vtk as _vtk

        from viznoir.engine.export import _array_info_list

        fd = _vtk.vtkFieldData()
        arr = _vtk.vtkFloatArray()
        arr.SetName("")  # empty name → GetArrayName returns ""
        arr.InsertNextValue(1.0)
        fd.AddArray(arr)

        # Manually force None name scenario: add array with SetArrayName(i, None) is not possible,
        # so instead test with empty dataset attrs where GetArrayName returns None
        # We test by mocking the attrs object
        class _FakeAttrs:
            def GetNumberOfArrays(self):
                return 1

            def GetArrayName(self, i):
                return None  # L79: name is None

            def GetArray(self, i):
                return None

        result = _array_info_list(_FakeAttrs())
        assert result == []

    def test_array_info_none_array(self):
        """L82: Arrays where GetArray returns None are skipped."""
        from viznoir.engine.export import _array_info_list

        class _FakeAttrs:
            def GetNumberOfArrays(self):
                return 1

            def GetArrayName(self, i):
                return "SomeArray"

            def GetArray(self, i):
                return None  # L82: arr is None

        result = _array_info_list(_FakeAttrs())
        assert result == []


# ---------------------------------------------------------------------------
# extract_stats with empty dataset (L147)
# ---------------------------------------------------------------------------


class TestExtractStatsEmpty:
    def test_stats_empty_unstructured_grid(self):
        """L147: _ensure_dataset returns None for non-vtkDataSet type → returns {}."""
        # vtkUnstructuredGrid IS a vtkDataSet, but has no points
        # To hit L147 we need a non-dataset non-multiblock type
        # Use a plain vtkDataObject (not a dataset)
        import vtk as _vtk

        from viznoir.engine.export import extract_stats

        obj = _vtk.vtkDataObject()  # Not vtkDataSet, not vtkMultiBlockDataSet → _ensure_dataset returns None
        result = extract_stats(obj)
        assert result == {}


# ---------------------------------------------------------------------------
# extract_data with empty dataset (L214)
# ---------------------------------------------------------------------------


class TestExtractDataEmpty:
    def test_extract_data_empty_object(self):
        """L214: _ensure_dataset returns None → returns {}."""
        import vtk as _vtk

        from viznoir.engine.export import extract_data

        obj = _vtk.vtkDataObject()
        result = extract_data(obj)
        assert result == {}


# ---------------------------------------------------------------------------
# export_file with empty dataset for CSV (L231)
# ---------------------------------------------------------------------------


class TestExportFileEmpty:
    def test_export_csv_empty_dataset(self, tmp_path):
        """L231: export CSV with empty vtkDataObject raises ValueError."""
        import vtk as _vtk

        from viznoir.engine.export import export_file

        obj = _vtk.vtkDataObject()
        out = tmp_path / "empty.csv"
        with pytest.raises(ValueError, match="Cannot export empty dataset to CSV"):
            export_file(obj, out)


# ---------------------------------------------------------------------------
# writer_class is None (L286-287)
# ---------------------------------------------------------------------------


class TestWriterClassNone:
    def test_writer_class_not_available(self, tmp_path, monkeypatch):
        """L286-287: writer_class is None (VTK class missing) raises RuntimeError."""
        import vtk as _vtk

        from viznoir.engine import export as export_mod

        # Patch vtk module used inside export_file to not have vtkGenericDataObjectWriter
        original_getattr = getattr

        def patched_getattr(obj, name, *args):
            if name == "vtkGenericDataObjectWriter":
                return None
            return original_getattr(obj, name, *args)

        # Monkeypatch the vtk module attribute access in the export module scope
        monkeypatch.setattr(_vtk, "vtkGenericDataObjectWriter", None, raising=False)
        out = tmp_path / "test.vtk"
        with pytest.raises(RuntimeError, match="not available"):
            export_mod.export_file(_wavelet(), out)


# ---------------------------------------------------------------------------
# export_csv with empty columns (L312-313) and no data (L326-327)
# ---------------------------------------------------------------------------


class TestExportCsvEdgeCases:
    def test_csv_no_data_points(self, tmp_path):
        """L326-327: dataset with no point data → ValueError 'No data to export'."""
        import vtk as _vtk

        from viznoir.engine.export import _export_csv

        # Create an empty polydata with points but no arrays, no coordinates
        # To hit "n == 0" we need data with no arrays and no coords
        # Use UnstructuredGrid with 0 points → extract_data returns {} → n == 0
        empty = _vtk.vtkUnstructuredGrid()  # 0 points, no arrays
        # _ensure_dataset returns empty (it IS a vtkDataSet), fields=[]
        # extract_data returns {} (no arrays, no coords) → n=0
        out = tmp_path / "nodata.csv"
        with pytest.raises(ValueError, match="No data to export"):
            _export_csv(empty, out)

    def test_csv_vector_field_multicomponent(self, tmp_path):
        """L333, 336-339: CSV with multi-component vector field expands to key_0, key_1, key_2."""
        import vtk as _vtk

        from viznoir.engine.export import export_file

        # Create wavelet with vector array via vtkArrayCalculator
        data = _wavelet()
        calc = _vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("velocity")
        calc.SetFunction("RTData*iHat + RTData*0.5*jHat + 0*kHat")
        calc.SetResultArrayType(_vtk.VTK_DOUBLE)
        calc.Update()

        out = tmp_path / "vector.csv"
        result = export_file(calc.GetOutput(), out)
        assert result["format"] == ".csv"
        assert result["size_bytes"] > 0

        content = out.read_text()
        # Vector components should be expanded to velocity_0, velocity_1, velocity_2
        assert "velocity_0" in content
        assert "velocity_1" in content
        assert "velocity_2" in content


# ---------------------------------------------------------------------------
# _ensure_dataset returns None for non-dataset (L421)
# ---------------------------------------------------------------------------


class TestEnsureDataset:
    def test_ensure_dataset_non_dataset(self):
        """L421: vtkDataObject that is not vtkDataSet or vtkMultiBlockDataSet → None."""
        import vtk as _vtk

        from viznoir.engine.export import _ensure_dataset

        obj = _vtk.vtkDataObject()
        result = _ensure_dataset(obj)
        assert result is None


# ---------------------------------------------------------------------------
# _all_array_names with cell data (L448-451)
# ---------------------------------------------------------------------------


class TestAllArrayNames:
    def test_all_array_names_cell_data(self):
        """L448-451: _all_array_names includes cell data arrays."""
        from viznoir.engine.export import _all_array_names
        from viznoir.engine.filters import point_to_cell

        # point_to_cell converts point arrays to cell arrays
        data = point_to_cell(_wavelet())
        names = _all_array_names(data)
        # RTData should appear (now as cell array)
        assert "RTData" in names

    def test_all_array_names_both_point_and_cell(self):
        """Cell array not in point arrays gets added."""
        import vtk as _vtk

        from viznoir.engine.export import _all_array_names

        sphere = _sphere()
        # Add a cell array
        cell_arr = _vtk.vtkFloatArray()
        cell_arr.SetName("CellField")
        cell_arr.SetNumberOfTuples(sphere.GetNumberOfCells())
        cell_arr.Fill(1.0)
        sphere.GetCellData().AddArray(cell_arr)

        names = _all_array_names(sphere)
        assert "CellField" in names


# ---------------------------------------------------------------------------
# _get_numpy_array from cell data (L475-477)
# ---------------------------------------------------------------------------


class TestGetNumpyArray:
    def test_get_numpy_array_cell_data(self):
        """L475-477: _get_numpy_array falls through to cell data."""
        from viznoir.engine.export import _get_numpy_array
        from viznoir.engine.filters import point_to_cell

        data = point_to_cell(_wavelet())
        arr, assoc = _get_numpy_array(data, "RTData")
        assert arr is not None
        assert assoc == "cell"


# ---------------------------------------------------------------------------
# _get_coordinates (L488)
# ---------------------------------------------------------------------------


class TestGetCoordinates:
    def test_get_coordinates_returns_nx3(self):
        """L488: _get_coordinates returns Nx3 numpy array."""
        from viznoir.engine.export import _get_coordinates

        coords = _get_coordinates(_sphere())
        assert coords is not None
        assert coords.ndim == 2
        assert coords.shape[1] == 3

    def test_get_coordinates_no_points(self):
        """_get_coordinates returns None for dataset with no points."""
        import vtk as _vtk

        from viznoir.engine.export import _get_coordinates

        empty = _vtk.vtkPolyData()
        result = _get_coordinates(empty)
        assert result is None


# ---------------------------------------------------------------------------
# export_gltf with vtkGLTFExporter not available (L515-516)
# ---------------------------------------------------------------------------


class TestExportGltf:
    def test_export_gltf_not_available(self, tmp_path, monkeypatch):
        """L515-516: vtkGLTFExporter not available raises RuntimeError."""
        import vtk as _vtk

        from viznoir.engine import export as export_mod

        # Remove vtkGLTFExporter from vtk module
        monkeypatch.delattr(_vtk, "vtkGLTFExporter", raising=False)
        out = tmp_path / "test.glb"
        with pytest.raises(RuntimeError, match="vtkGLTFExporter not available"):
            export_mod.export_gltf(_sphere(), out)

    def test_export_gltf_available(self, tmp_path):
        """export_gltf succeeds when vtkGLTFExporter is available."""
        import vtk as _vtk

        if not hasattr(_vtk, "vtkGLTFExporter"):
            pytest.skip("vtkGLTFExporter not available")
        from viznoir.engine.export import export_gltf

        out = tmp_path / "test.glb"
        result = export_gltf(_sphere(), out)
        assert result["format"] in (".glb", ".gltf")
        assert result["size_bytes"] > 0


# ---------------------------------------------------------------------------
# extract_data: nonexistent field → np_arr is None → continue (L231)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# get_leaf_block with non-dataset non-multiblock (L378)
# ---------------------------------------------------------------------------


class TestGetLeafBlockNonDataset:
    def test_leaf_block_plain_dataobject(self):
        """L378: get_leaf_block returns None for non-dataset non-multiblock."""
        import vtk as _vtk

        from viznoir.engine.export import get_leaf_block

        obj = _vtk.vtkDataObject()
        result = get_leaf_block(obj)
        assert result is None


# ---------------------------------------------------------------------------
# supported_export_formats (L555)
# ---------------------------------------------------------------------------


class TestSupportedExportFormats:
    def test_supported_formats_returns_sorted_list(self):
        """L555: supported_export_formats returns sorted list of extensions."""
        from viznoir.engine.export import supported_export_formats

        formats = supported_export_formats()
        assert isinstance(formats, list)
        assert ".csv" in formats
        assert ".stl" in formats
        assert formats == sorted(formats)


class TestExtractDataNonexistentField:
    def test_extract_data_skips_missing_field(self):
        """L231: fields with no array → skipped, not included in result."""
        from viznoir.engine.export import extract_data

        result = extract_data(_wavelet(), fields=["nonexistent_field"])
        assert "nonexistent_field" not in result
        assert result == {}


# ---------------------------------------------------------------------------
# _export_csv: values length mismatch → L333 continue branch
# ---------------------------------------------------------------------------


class TestExportCsvLengthMismatch:
    def test_csv_skips_mismatched_length_column(self, tmp_path):
        """L333: _export_csv skips columns whose len != n (not isinstance list or len mismatch).
        Achieved by injecting a fake extract_data result."""

        from viznoir.engine import export as export_mod

        # We monkeypatch extract_data to return a dict with a mismatched-length entry
        original_extract_data = export_mod.extract_data

        def _fake_extract_data(ds, fields, include_coords=False):
            # Return one valid scalar column and one that has wrong length
            n = ds.GetNumberOfPoints()
            result = {"RTData": [1.0] * n, "bad_col": [0.0] * (n + 5)}
            return result

        export_mod.extract_data = _fake_extract_data
        try:
            out = tmp_path / "mismatch.csv"
            result = export_mod.export_file(_wavelet(), out)
            assert result["format"] == ".csv"
            content = out.read_text()
            # bad_col should be skipped (length mismatch), RTData should be present
            assert "RTData" in content
            assert "bad_col" not in content
        finally:
            export_mod.extract_data = original_extract_data
