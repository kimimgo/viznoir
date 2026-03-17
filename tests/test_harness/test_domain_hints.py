"""Tests for mechanical domain detection from file metadata."""

from __future__ import annotations

from viznoir.harness.domain_hints import detect_domain


class TestDetectDomain:
    """Test domain detection from inspect_data metadata."""

    def test_foam_file_is_cfd(self):
        meta = {"file_path": "/data/case.foam", "arrays": {"p": {}, "U": {}}}
        assert detect_domain(meta) == "cfd"

    def test_cas_file_is_cfd(self):
        meta = {"file_path": "/data/case.cas", "arrays": {"Pressure": {}}}
        assert detect_domain(meta) == "cfd"

    def test_displacement_field_is_fea(self):
        meta = {"file_path": "/data/result.vtu", "arrays": {"displacement": {}, "von_mises_stress": {}}}
        assert detect_domain(meta) == "fea"

    def test_stress_only_is_fea(self):
        meta = {"file_path": "/data/result.vtu", "arrays": {"stress": {}}}
        assert detect_domain(meta) == "fea"

    def test_bi4_file_is_sph(self):
        meta = {"file_path": "/data/Part0001.bi4", "arrays": {"Velocity": {}, "Type": {}}}
        assert detect_domain(meta) == "sph"

    def test_type_and_velocity_is_sph(self):
        meta = {"file_path": "/data/particles.vtk", "arrays": {"Type": {}, "Velocity": {}}}
        assert detect_domain(meta) == "sph"

    def test_generic_fallback(self):
        meta = {"file_path": "/data/unknown.vti", "arrays": {"density": {}}}
        assert detect_domain(meta) == "generic"

    def test_empty_arrays_is_generic(self):
        meta = {"file_path": "/data/mesh.stl", "arrays": {}}
        assert detect_domain(meta) == "generic"

    def test_missing_arrays_key_is_generic(self):
        meta = {"file_path": "/data/mesh.stl"}
        assert detect_domain(meta) == "generic"

    def test_cfd_fields_override_generic_extension(self):
        """VTU with p and U fields is CFD, not generic."""
        meta = {"file_path": "/data/internal.vtu", "arrays": {"p": {}, "U": {}, "k": {}}}
        assert detect_domain(meta) == "cfd"

    def test_cgns_is_cfd(self):
        meta = {"file_path": "/data/flow.cgns", "arrays": {"Pressure": {}}}
        assert detect_domain(meta) == "cfd"
