"""Tests for engine/export.py — data inspection, stats, and file export."""

from __future__ import annotations

import pytest

from viznoir.engine.export import (
    _WRITER_MAP,
    export_gltf,
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


# ---------------------------------------------------------------------------
# export_gltf
# ---------------------------------------------------------------------------

vtk = pytest.importorskip("vtk")


class TestExportGltf:
    def test_export_gltf_is_importable(self):
        """Test that export_gltf function is available."""
        from viznoir.engine.export import export_gltf as fn
        assert callable(fn)

    def test_export_gltf_in_all(self):
        """Test that export_gltf is in __all__."""
        from viznoir.engine.export import __all__ as all_names
        assert "export_gltf" in all_names

    @pytest.mark.skipif(
        not hasattr(vtk, "vtkGLTFExporter"),
        reason="vtkGLTFExporter not available in this VTK build",
    )
    def test_export_creates_file(self, tmp_path):
        """Test that export_gltf creates a file when vtkGLTFExporter is available."""
        sphere = vtk.vtkSphereSource()
        sphere.Update()
        data = sphere.GetOutput()

        out = tmp_path / "test.glb"
        result = export_gltf(data, out, binary=True)

        assert result["path"] == str(out.resolve())
        assert result["format"] == ".glb"
        assert out.exists()
        assert result["size_bytes"] > 0

    @pytest.mark.skipif(
        not hasattr(vtk, "vtkGLTFExporter"),
        reason="vtkGLTFExporter not available in this VTK build",
    )
    def test_export_gltf_format(self, tmp_path):
        """Test that format field matches file extension."""
        sphere = vtk.vtkSphereSource()
        sphere.Update()

        gltf_out = tmp_path / "test.gltf"
        result = export_gltf(sphere.GetOutput(), gltf_out, binary=False)
        assert result["format"] == ".gltf"
