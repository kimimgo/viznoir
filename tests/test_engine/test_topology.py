"""Tests for engine/topology.py — L2 field topology extraction."""

from __future__ import annotations

import json

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk


def _make_cavity_2d(n: int = 20):
    """Create a synthetic 2D lid-driven cavity velocity field.

    Top wall moves right (Ux=1), creates a clockwise primary vortex.
    Uses n+1 x n+1 x 2 grid (thin 3D slab) for VTK gradient compatibility.
    """
    grid = vtk.vtkImageData()
    grid.SetDimensions(n + 1, n + 1, 2)
    grid.SetOrigin(0, 0, 0)
    grid.SetSpacing(1.0 / n, 1.0 / n, 1.0 / n)

    n_pts = grid.GetNumberOfPoints()
    vel = np.zeros((n_pts, 3), dtype=np.float64)
    for i in range(n_pts):
        x, y, _ = grid.GetPoint(i)
        vel[i, 0] = np.sin(np.pi * x) * np.cos(np.pi * y) * 0.5
        vel[i, 1] = -np.cos(np.pi * x) * np.sin(np.pi * y) * 0.5
        vel[i, 2] = 0.0

    vtk_vel = numpy_to_vtk(vel)
    vtk_vel.SetName("U")
    vtk_vel.SetNumberOfComponents(3)
    grid.GetPointData().AddArray(vtk_vel)
    grid.GetPointData().SetActiveVectors("U")

    # Add pressure field (Bernoulli-like)
    pressure = np.zeros(n_pts, dtype=np.float64)
    for i in range(n_pts):
        x, y, _ = grid.GetPoint(i)
        pressure[i] = -0.5 * (vel[i, 0] ** 2 + vel[i, 1] ** 2)
    vtk_p = numpy_to_vtk(pressure)
    vtk_p.SetName("p")
    grid.GetPointData().AddArray(vtk_p)

    return grid


def _make_empty_grid():
    """Create a minimal grid with zero velocity."""
    grid = vtk.vtkImageData()
    grid.SetDimensions(3, 3, 2)
    grid.SetSpacing(0.1, 0.1, 0.1)
    n_pts = grid.GetNumberOfPoints()
    vel = numpy_to_vtk(np.zeros((n_pts, 3), dtype=np.float64))
    vel.SetName("U")
    vel.SetNumberOfComponents(3)
    grid.GetPointData().AddArray(vel)
    return grid


class TestVortexDetection:
    def test_detects_primary_vortex(self):
        from viznoir.engine.topology import detect_vortices

        ds = _make_cavity_2d(30)
        vortices = detect_vortices(ds, "U")
        assert len(vortices) >= 1
        primary = max(vortices, key=lambda v: v.strength)
        assert 0.1 < primary.center[0] < 0.9
        assert 0.1 < primary.center[1] < 0.9

    def test_vortex_has_rotation(self):
        from viznoir.engine.topology import detect_vortices

        ds = _make_cavity_2d(30)
        vortices = detect_vortices(ds, "U")
        assert len(vortices) >= 1
        assert vortices[0].rotation in ("clockwise", "counter-clockwise")

    def test_vortex_has_positive_strength(self):
        from viznoir.engine.topology import detect_vortices

        ds = _make_cavity_2d(30)
        vortices = detect_vortices(ds, "U")
        for v in vortices:
            assert v.strength > 0

    def test_zero_velocity_returns_empty(self):
        from viznoir.engine.topology import detect_vortices

        grid = _make_empty_grid()
        vortices = detect_vortices(grid, "U")
        assert vortices == []

    def test_scalar_field_returns_empty(self):
        from viznoir.engine.topology import detect_vortices

        ds = _make_cavity_2d(20)
        vortices = detect_vortices(ds, "p")
        assert vortices == []


class TestCriticalPoints:
    def test_finds_stagnation_points(self):
        from viznoir.engine.topology import detect_critical_points

        ds = _make_cavity_2d(30)
        cps = detect_critical_points(ds, "U")
        assert len(cps) >= 1
        for cp in cps:
            assert cp.velocity_magnitude < 0.1

    def test_critical_point_has_position(self):
        from viznoir.engine.topology import detect_critical_points

        ds = _make_cavity_2d(30)
        cps = detect_critical_points(ds, "U")
        if cps:
            assert len(cps[0].position) >= 2

    def test_critical_point_types(self):
        from viznoir.engine.topology import detect_critical_points

        ds = _make_cavity_2d(30)
        cps = detect_critical_points(ds, "U")
        valid_types = {"stagnation", "separation", "reattachment"}
        for cp in cps:
            assert cp.type in valid_types

    def test_scalar_critical_points(self):
        from viznoir.engine.topology import detect_critical_points

        ds = _make_cavity_2d(20)
        cps = detect_critical_points(ds, "p", epsilon=0.05)
        # Scalar fields: gradient near zero = critical point
        for cp in cps:
            assert len(cp.position) >= 2


class TestCenterlineProfiles:
    def test_auto_probes_return_profiles(self):
        from viznoir.engine.topology import extract_centerline_profiles

        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["U", "p"], num_lines=2)
        assert len(profiles) >= 2

    def test_profile_has_field_data(self):
        from viznoir.engine.topology import extract_centerline_profiles

        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["U"], num_lines=1)
        assert len(profiles) >= 1
        p = profiles[0]
        assert p.num_points > 0
        assert len(p.fields) > 0

    def test_profile_start_end(self):
        from viznoir.engine.topology import extract_centerline_profiles

        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["p"], num_lines=1)
        p = profiles[0]
        assert len(p.start) == 3
        assert len(p.end) == 3
        assert p.start != p.end

    def test_profile_field_values_length(self):
        from viznoir.engine.topology import extract_centerline_profiles

        ds = _make_cavity_2d(30)
        profiles = extract_centerline_profiles(ds, ["p"], num_lines=1)
        p = profiles[0]
        for values in p.fields.values():
            assert len(values) == p.num_points


class TestGradientAnalysis:
    def test_gradient_stats_keys(self):
        from viznoir.engine.topology import compute_gradient_stats

        ds = _make_cavity_2d(30)
        stats = compute_gradient_stats(ds, "p")
        assert "mean_magnitude" in stats
        assert "max_magnitude" in stats
        assert stats["max_magnitude"] >= stats["mean_magnitude"]

    def test_gradient_has_dominant_direction(self):
        from viznoir.engine.topology import compute_gradient_stats

        ds = _make_cavity_2d(30)
        stats = compute_gradient_stats(ds, "p")
        assert "dominant_direction" in stats
        assert len(stats["dominant_direction"]) == 3


class TestFieldTopologyFull:
    def test_analyze_velocity_field(self):
        from viznoir.engine.topology import analyze_field_topology

        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "U")
        assert topo.field_name == "U"
        assert len(topo.vortices) >= 1
        assert topo.field_range["min"] is not None
        assert len(topo.centerline_profiles) >= 1

    def test_analyze_scalar_field(self):
        from viznoir.engine.topology import analyze_field_topology

        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "p")
        assert topo.field_name == "p"
        assert topo.vortices == []  # No vortex detection for scalars
        assert topo.gradient_stats is not None

    def test_field_range_stats(self):
        from viznoir.engine.topology import analyze_field_topology

        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "p")
        fr = topo.field_range
        assert "min" in fr
        assert "max" in fr
        assert "mean" in fr
        assert "std" in fr
        assert fr["min"] <= fr["mean"] <= fr["max"]

    def test_to_dict_json_serializable(self):
        from viznoir.engine.topology import analyze_field_topology

        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "U")
        d = topo.to_dict()
        # Must be JSON-serializable (no numpy types)
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["field_name"] == "U"
        assert len(parsed["vortices"]) >= 1

    def test_to_dict_structure(self):
        from viznoir.engine.topology import analyze_field_topology

        ds = _make_cavity_2d(30)
        topo = analyze_field_topology(ds, "U")
        d = topo.to_dict()
        assert "field_name" in d
        assert "field_range" in d
        assert "vortices" in d
        assert "critical_points" in d
        assert "centerline_profiles" in d
        assert "gradient_stats" in d
