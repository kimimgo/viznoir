"""Tests for FilterRegistry and FormatRegistry."""

from __future__ import annotations

import pytest

from viznoir.core.registry import (
    FILTER_REGISTRY,
    FORMAT_REGISTRY,
    get_filter,
    get_reader,
    validate_filter_params,
)


class TestFormatRegistry:
    def test_known_formats(self):
        assert get_reader("/data/case.foam") == "vtkOpenFOAMReader"
        assert get_reader("/data/mesh.vtk") == "vtkGenericDataObjectReader"
        assert get_reader("/data/result.vtu") == "vtkXMLUnstructuredGridReader"
        assert get_reader("/data/surface.stl") == "vtkSTLReader"

    def test_case_insensitive_extension(self):
        assert get_reader("/data/FILE.VTK") == "vtkGenericDataObjectReader"

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            get_reader("/data/file.xyz")

    def test_compound_extension_vtm_series(self):
        assert get_reader("/data/case.vtm.series") == "vtkXMLMultiBlockDataReader"

    def test_compound_extension_vtu_series(self):
        assert get_reader("/data/output.vtu.series") == "vtkXMLUnstructuredGridReader"

    def test_compound_extension_vtp_series(self):
        assert get_reader("/data/surface.vtp.series") == "vtkXMLPolyDataReader"

    def test_compound_fallback_to_single(self):
        """If compound doesn't match, fall back to single suffix."""
        assert get_reader("/data/mesh.vtk") == "vtkGenericDataObjectReader"

    def test_all_formats_have_values(self):
        for ext, reader in FORMAT_REGISTRY.items():
            assert ext.startswith(".")
            assert len(reader) > 0


class TestFilterRegistry:
    def test_known_filters(self):
        assert "Slice" in FILTER_REGISTRY
        assert "Calculator" in FILTER_REGISTRY
        assert "IntegrateVariables" in FILTER_REGISTRY

    def test_get_filter_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown filter"):
            get_filter("NonExistentFilter")

    def test_get_filter_returns_schema(self):
        schema = get_filter("Slice")
        assert "vtk_class" in schema
        assert "params" in schema
        assert schema["vtk_class"] == "vtkCutter"

    def test_get_filter_case_insensitive_fallback(self):
        """get_filter with lowercase name falls back to case-insensitive match."""
        schema = get_filter("slice")
        assert schema["vtk_class"] == "vtkCutter"

    def test_validate_params_defaults(self):
        result = validate_filter_params("Slice", {"origin": [0, 0, 0]})
        assert result["origin"] == [0, 0, 0]
        assert result["normal"] == [0, 0, 1]  # default

    def test_validate_params_missing_required(self):
        with pytest.raises(ValueError, match="requires parameter"):
            validate_filter_params("Contour", {})

    def test_validate_paramless_filter(self):
        result = validate_filter_params("IntegrateVariables", {})
        assert result == {}

    def test_validate_calculator_params(self):
        result = validate_filter_params(
            "Calculator",
            {
                "expression": "mag(U)",
                "result_name": "Umag",
            },
        )
        assert result["expression"] == "mag(U)"
        assert result["result_name"] == "Umag"
        assert result["association"] == "POINTS"  # default
