"""Tests for physics detection, smart camera, representation, and techniques."""

from __future__ import annotations

import pytest

from viznoir.engine.physics import (
    REPRESENTATION_TYPES,
    SmartCamera,
    SmartDefaults,
    SmartRepresentation,
    VisualizationTechnique,
    analyze_camera,
    detect_physics,
)

# ── detect_physics ───────────────────────────────────────────────────


class TestDetectPhysics:
    def test_pressure_field(self):
        pt = detect_physics("p")
        assert pt.name == "pressure"
        assert pt.colormap == "coolwarm"
        assert pt.diverging is True

    def test_pressure_full_name(self):
        pt = detect_physics("pressure")
        assert pt.name == "pressure"

    def test_pressure_p_rgh(self):
        pt = detect_physics("p_rgh")
        assert pt.name == "pressure"

    def test_velocity_U(self):
        pt = detect_physics("U", num_components=3)
        assert pt.name == "velocity"
        assert pt.colormap == "viridis"
        assert pt.streamlines is True
        assert pt.is_vector is True

    def test_velocity_lowercase(self):
        pt = detect_physics("velocity", num_components=3)
        assert pt.name == "velocity"

    def test_temperature_T(self):
        pt = detect_physics("T")
        assert pt.name == "temperature"
        assert pt.colormap == "inferno"

    def test_temperature_full_name(self):
        pt = detect_physics("temperature")
        assert pt.name == "temperature"

    def test_turbulence_k(self):
        pt = detect_physics("k")
        assert pt.name == "turbulence"
        assert pt.colormap == "plasma"
        assert pt.log_scale is True

    def test_turbulence_epsilon(self):
        pt = detect_physics("epsilon")
        assert pt.name == "turbulence"

    def test_turbulence_omega(self):
        pt = detect_physics("omega")
        assert pt.name == "turbulence"

    def test_stress_sigma(self):
        pt = detect_physics("sigma")
        assert pt.name == "stress"
        assert pt.colormap == "jet"

    def test_displacement_D(self):
        pt = detect_physics("D", num_components=3)
        assert pt.name == "displacement"
        assert pt.warp is True

    def test_vof_alpha(self):
        pt = detect_physics("alpha.water")
        assert pt.name == "vof"
        assert pt.colormap == "blues"

    def test_vof_alpha_simple(self):
        pt = detect_physics("alpha")
        assert pt.name == "vof"

    def test_vorticity(self):
        pt = detect_physics("vorticity", num_components=3)
        assert pt.name == "vorticity"
        assert pt.diverging is True
        assert pt.streamlines is True

    def test_mesh_quality(self):
        pt = detect_physics("quality")
        assert pt.name == "mesh_quality"
        assert pt.colormap == "rdylgn"

    def test_density(self):
        pt = detect_physics("rho")
        assert pt.name == "density"

    def test_wall_shear(self):
        pt = detect_physics("wallShearStress", num_components=3)
        assert pt.name == "wall_shear"
        assert pt.log_scale is True


class TestDetectPhysicsFallback:
    def test_unknown_scalar(self):
        pt = detect_physics("my_custom_field")
        assert pt.name == "unknown_scalar"
        assert pt.category == "scalar"
        assert pt.colormap == "cool to warm"

    def test_unknown_vector(self):
        pt = detect_physics("my_vector_field", num_components=3)
        assert pt.name == "unknown_vector"
        assert pt.category == "vector"
        assert pt.colormap == "viridis"

    def test_diverging_override(self):
        """Unknown field with zero-crossing data → diverging colormap."""
        pt = detect_physics("custom", data_range=(-5.0, 10.0))
        assert pt.colormap == "coolwarm"
        assert pt.diverging is True

    def test_positive_range_no_diverging(self):
        pt = detect_physics("custom", data_range=(0.0, 100.0))
        assert pt.diverging is False


class TestDetectPhysicsDataRange:
    def test_pressure_with_range(self):
        """Pressure is already diverging, range doesn't change it."""
        pt = detect_physics("p", data_range=(0.0, 100.0))
        assert pt.diverging is True  # pressure is inherently diverging

    def test_velocity_zero_crossing(self):
        """Velocity is not diverging but zero-crossing data overrides."""
        pt = detect_physics("U", num_components=3, data_range=(-5.0, 10.0))
        # Velocity: diverging=False in pattern, but data crosses zero → override
        assert pt.colormap == "coolwarm"
        assert pt.diverging is True


class TestDetectPhysicsCaseInsensitive:
    def test_uppercase(self):
        pt = detect_physics("PRESSURE")
        assert pt.name == "pressure"

    def test_mixed_case(self):
        pt = detect_physics("Temperature")
        assert pt.name == "temperature"


# ── analyze_camera (View Frustum Analysis) ────────────────────────────


class TestAnalyzeCameraDegenerate:
    def test_zero_bounds(self):
        cam = analyze_camera((0, 0, 0, 0, 0, 0))
        assert cam.preset == "isometric"
        assert cam.is_2d is False
        assert "degenerate" in cam.reason

    def test_tiny_bounds(self):
        cam = analyze_camera((1e-31, 1e-31, 1e-31, 1e-31, 1e-31, 1e-31))
        assert cam.preset == "isometric"


class TestAnalyzeCamera2D:
    """2D datasets: one axis << 1% of diagonal → view perpendicular to flat axis."""

    def test_flat_z_axis(self):
        """XY plane (z~0) → top view."""
        cam = analyze_camera((0, 10, 0, 10, 0, 0))
        assert cam.is_2d is True
        assert cam.flat_axis == 2
        assert cam.preset == "top"

    def test_flat_x_axis(self):
        """YZ plane (x~0) → right view."""
        cam = analyze_camera((5, 5, 0, 10, 0, 10))
        assert cam.is_2d is True
        assert cam.flat_axis == 0
        assert cam.preset == "right"

    def test_flat_y_axis(self):
        """XZ plane (y~0) → front view."""
        cam = analyze_camera((0, 10, 3, 3, 0, 10))
        assert cam.is_2d is True
        assert cam.flat_axis == 1
        assert cam.preset == "front"

    def test_aspect_ratios_2d(self):
        """Aspect ratios normalized to max dimension."""
        cam = analyze_camera((0, 10, 0, 5, 0, 0))
        assert cam.aspect_ratios[0] == pytest.approx(1.0)  # X is max
        assert cam.aspect_ratios[1] == pytest.approx(0.5)  # Y is half
        assert cam.aspect_ratios[2] == pytest.approx(0.0)  # Z is flat


class TestAnalyzeCamera3D:
    """3D datasets: select view that maximizes visible area."""

    def test_cubic_isometric(self):
        """Near-cubic geometry → isometric."""
        cam = analyze_camera((0, 10, 0, 10, 0, 10))
        assert cam.is_2d is False
        assert cam.flat_axis is None
        assert cam.preset == "isometric"
        assert "near-cubic" in cam.reason

    def test_elongated_x(self):
        """Long in X, thin in Y → view from Y (front) to see XZ face."""
        # Y=5 is >1% of diag (~112) so not 2D, but small enough to be elongated
        cam = analyze_camera((0, 100, 0, 5, 0, 50))
        assert cam.is_2d is False
        assert cam.preset == "front"
        assert "elongated" in cam.reason

    def test_elongated_z(self):
        """Thin in Z → view from Z (top) to see XY face."""
        cam = analyze_camera((0, 50, 0, 50, 0, 2))
        assert cam.is_2d is False
        assert cam.preset == "top"

    def test_elongated_tall(self):
        """Thin in X → view from X (right) to see YZ face."""
        cam = analyze_camera((0, 1, 0, 50, 0, 50))
        assert cam.is_2d is False
        assert cam.preset == "right"


class TestAnalyzeCameraPhysicsOverride:
    """Physics type overrides geometry-based camera selection."""

    def test_pressure_2d_override(self):
        """2D pressure → use physics camera_2d (top), not geometry."""
        physics = detect_physics("p")
        cam = analyze_camera((0, 10, 0, 10, 0, 0), physics=physics)
        assert cam.preset == "top"
        assert cam.is_2d is True
        assert "pressure" in cam.reason

    def test_vof_3d_override(self):
        """3D VOF → use physics camera_3d (front), not geometry."""
        physics = detect_physics("alpha.water")
        cam = analyze_camera((0, 10, 0, 10, 0, 10), physics=physics)
        assert cam.preset == "front"
        assert "vof" in cam.reason

    def test_velocity_2d_override(self):
        """2D velocity → physics says front, even though geometry says top."""
        physics = detect_physics("U", num_components=3)
        cam = analyze_camera((0, 10, 0, 10, 0, 0), physics=physics)
        assert cam.preset == "front"  # velocity camera_2d = front
        assert cam.is_2d is True


# ── REPRESENTATION_TYPES ──────────────────────────────────────────────


class TestRepresentationTypes:
    def test_all_types_present(self):
        expected = {"surface", "surface_with_edges", "wireframe", "points", "point_gaussian"}
        assert set(REPRESENTATION_TYPES.keys()) == expected

    def test_vtk_values(self):
        assert REPRESENTATION_TYPES["surface"]["vtk_value"] == 2
        assert REPRESENTATION_TYPES["wireframe"]["vtk_value"] == 1
        assert REPRESENTATION_TYPES["points"]["vtk_value"] == 0

    def test_each_has_description(self):
        for name, info in REPRESENTATION_TYPES.items():
            assert "description" in info, f"{name} missing description"
            assert "use_when" in info, f"{name} missing use_when"


# ── SmartRepresentation dataclass ─────────────────────────────────────


class TestSmartRepresentationDataclass:
    def test_default_surface(self):
        rep = SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0)
        assert rep.primary == "surface"
        assert rep.edge_visibility is False
        assert rep.opacity == 1.0

    def test_surface_with_edges(self):
        rep = SmartRepresentation("surface", True, 0.05, 1.0, 2.0, 1.0)
        assert rep.edge_visibility is True
        assert rep.edge_opacity == 0.05

    def test_frozen(self):
        rep = SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0)
        with pytest.raises(AttributeError):
            rep.primary = "wireframe"  # type: ignore[misc]


# ── VisualizationTechnique dataclass ──────────────────────────────────


class TestVisualizationTechnique:
    def test_glyph_technique(self):
        t = VisualizationTechnique(
            technique="glyph",
            params={"array_name": "U", "scale_factor": 0.1, "glyph_type": "arrow"},
            reason="Vector field: arrow glyphs",
            priority=2,
        )
        assert t.technique == "glyph"
        assert t.params["glyph_type"] == "arrow"
        assert t.priority == 2

    def test_isosurface_technique(self):
        t = VisualizationTechnique(
            technique="isosurface",
            params={"array_name": "alpha", "value": 0.5},
            reason="VOF free surface",
            priority=1,
        )
        assert t.technique == "isosurface"
        assert t.params["value"] == 0.5

    def test_streamlines_technique(self):
        t = VisualizationTechnique(
            technique="streamlines",
            params={"vectors": "U", "seed_resolution": 20},
            reason="Flow visualization",
            priority=1,
        )
        assert t.technique == "streamlines"

    def test_warp_technique(self):
        t = VisualizationTechnique(
            technique="warp",
            params={"vector": "D", "scale_factor": 10.0},
            reason="Displacement warp",
            priority=1,
        )
        assert t.params["scale_factor"] == 10.0

    def test_contour_lines_technique(self):
        t = VisualizationTechnique(
            technique="contour_lines",
            params={"array_name": "p", "isovalues": [10, 20, 30]},
            reason="2D scalar contours",
            priority=2,
        )
        assert len(t.params["isovalues"]) == 3

    def test_priority_sorting(self):
        """Higher priority (lower number) should sort first."""
        ts = [
            VisualizationTechnique("glyph", {}, "", 2),
            VisualizationTechnique("warp", {}, "", 1),
            VisualizationTechnique("isosurface", {}, "", 3),
        ]
        sorted_ts = sorted(ts, key=lambda t: t.priority)
        assert sorted_ts[0].technique == "warp"
        assert sorted_ts[1].technique == "glyph"
        assert sorted_ts[2].technique == "isosurface"


# ── SmartDefaults dataclass ───────────────────────────────────────────


class TestSmartDefaultsDataclass:
    def test_construction(self):
        sd = SmartDefaults(
            physics=detect_physics("p"),
            camera=SmartCamera("top", "test", 2, (1.0, 1.0, 0.0), True),
            representation=SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0),
            colormap="coolwarm",
            log_scale=False,
            scalar_range=(-100.0, 100.0),
            techniques=[],
        )
        assert sd.physics.name == "pressure"
        assert sd.camera.preset == "top"
        assert sd.colormap == "coolwarm"
        assert sd.scalar_range == (-100.0, 100.0)

    def test_techniques_default_empty(self):
        sd = SmartDefaults(
            physics=detect_physics("T"),
            camera=SmartCamera("isometric", "test", None, (1.0, 1.0, 1.0), False),
            representation=SmartRepresentation("surface", False, 0.0, 1.0, 2.0, 1.0),
            colormap="inferno",
            log_scale=False,
            scalar_range=None,
        )
        assert sd.techniques == []


# ── VTK-based integration tests ─────────────────────────────────────

vtk = pytest.importorskip("vtk")

from viznoir.engine.physics import (  # noqa: E402
    _auto_glyph_scale,
    _auto_seed_line,
    _auto_warp_scale,
    _diagonal,
    _ensure_dataset,
    _find_array,
    _first_array_name,
    _is_2d_dataset,
    _largest_leaf,
    recommend_techniques,
    smart_defaults,
    smart_representation,
)


def _make_3d_grid():
    """Create a 3D test grid with pressure and velocity."""
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

    p = vtk.vtkFloatArray()
    p.SetName("p")
    p.SetNumberOfTuples(4)
    for i in range(4):
        p.SetValue(i, float(i) * 100.0 - 150.0)
    grid.GetPointData().AddArray(p)

    u = vtk.vtkFloatArray()
    u.SetName("U")
    u.SetNumberOfComponents(3)
    u.SetNumberOfTuples(4)
    for i in range(4):
        u.SetTuple3(i, float(i), 0.0, 0.0)
    grid.GetPointData().AddArray(u)

    alpha = vtk.vtkFloatArray()
    alpha.SetName("alpha.water")
    alpha.SetNumberOfTuples(4)
    for i in range(4):
        alpha.SetValue(i, float(i) / 3.0)
    grid.GetPointData().AddArray(alpha)

    return grid


class TestSmartRepresentationVTK:
    def test_small_mesh_shows_edges(self):
        grid = _make_3d_grid()
        rep = smart_representation(grid)
        assert rep.edge_visibility is True

    def test_point_only_data(self):
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        for i in range(100):
            pts.InsertNextPoint(float(i), 0, 0)
        grid.SetPoints(pts)
        rep = smart_representation(grid)
        assert rep.primary == "points"

    def test_empty_dataset(self):
        grid = vtk.vtkUnstructuredGrid()
        rep = smart_representation(grid)
        assert rep.primary == "surface"

    def test_physics_warp_override(self):
        grid = _make_3d_grid()
        physics = detect_physics("displacement", num_components=3)
        rep = smart_representation(grid, physics)
        assert rep.edge_visibility is True


class TestRecommendTechniquesVTK:
    def test_velocity_gets_streamlines(self):
        grid = _make_3d_grid()
        techniques = recommend_techniques(grid, "U")
        names = [t.technique for t in techniques]
        assert "streamlines" in names

    def test_vof_gets_isosurface(self):
        grid = _make_3d_grid()
        techniques = recommend_techniques(grid, "alpha.water")
        names = [t.technique for t in techniques]
        assert "isosurface" in names

    def test_sorted_by_priority(self):
        grid = _make_3d_grid()
        techniques = recommend_techniques(grid, "U")
        priorities = [t.priority for t in techniques]
        assert priorities == sorted(priorities)

    def test_empty_dataset(self):
        grid = vtk.vtkUnstructuredGrid()
        techniques = recommend_techniques(grid, "p")
        assert techniques == []


class TestSmartDefaultsVTK:
    def test_full_defaults(self):
        grid = _make_3d_grid()
        sd = smart_defaults(grid, "p")
        assert isinstance(sd, SmartDefaults)
        assert sd.physics.name == "pressure"
        assert sd.colormap == "coolwarm"
        assert sd.scalar_range is not None

    def test_auto_field_detection(self):
        grid = _make_3d_grid()
        sd = smart_defaults(grid)
        assert sd.physics is not None

    def test_empty_dataset(self):
        grid = vtk.vtkUnstructuredGrid()
        sd = smart_defaults(grid)
        assert sd.physics.name == "unknown_scalar"


class TestInternalHelpersVTK:
    def test_diagonal(self):
        d = _diagonal((0, 3, 0, 4, 0, 0))
        assert d == pytest.approx(5.0)

    def test_is_2d_flat_z(self):
        assert _is_2d_dataset((0, 10, 0, 10, 0, 0)) is True

    def test_is_2d_3d_cube(self):
        assert _is_2d_dataset((0, 1, 0, 1, 0, 1)) is False

    def test_auto_glyph_scale(self):
        grid = _make_3d_grid()
        scale = _auto_glyph_scale(grid)
        assert scale > 0

    def test_auto_seed_line(self):
        p1, p2 = _auto_seed_line((0, 10, 0, 5, 0, 2))
        assert len(p1) == 3
        assert p1 != p2

    def test_auto_warp_scale(self):
        grid = _make_3d_grid()
        scale = _auto_warp_scale(grid, "U")
        assert scale > 0

    def test_auto_warp_missing_field(self):
        grid = _make_3d_grid()
        assert _auto_warp_scale(grid, "missing") == 1.0


class TestAnalyzeCameraLineLike:
    """Cover line 237: 1D line-like geometry (2+ flat axes)."""

    def test_1d_line_like_bounds(self):
        # Flat in Y and Z → line along X
        bounds = (0.0, 10.0, 0.0, 0.0, 0.0, 0.0)
        cam = analyze_camera(bounds)
        assert cam.preset == "front"
        assert "1D" in cam.reason


class TestEnsureDatasetMultiBlock:
    """Cover lines 604-606, 610-625."""

    def test_multiblock_returns_largest_leaf(self):
        mb = vtk.vtkMultiBlockDataSet()
        # Small block
        small = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        small.SetPoints(pts)
        cell_ids = vtk.vtkIdList()
        cell_ids.InsertNextId(0)
        small.InsertNextCell(vtk.VTK_VERTEX, cell_ids)
        mb.SetBlock(0, small)

        # Larger block
        large = _make_3d_grid()
        mb.SetBlock(1, large)

        result = _ensure_dataset(mb)
        assert result.GetNumberOfCells() == large.GetNumberOfCells()

    def test_multiblock_nested(self):
        outer = vtk.vtkMultiBlockDataSet()
        inner = vtk.vtkMultiBlockDataSet()
        grid = _make_3d_grid()
        inner.SetBlock(0, grid)
        outer.SetBlock(0, inner)
        result = _ensure_dataset(outer)
        assert result is grid

    def test_multiblock_with_none_block(self):
        mb = vtk.vtkMultiBlockDataSet()
        mb.SetBlock(0, None)
        grid = _make_3d_grid()
        mb.SetBlock(1, grid)
        result = _largest_leaf(mb)
        assert result is grid

    def test_ensure_dataset_unknown_type(self):
        # Non-DataSet, non-MultiBlock → None
        table = vtk.vtkTable()
        result = _ensure_dataset(table)
        assert result is None


class TestFirstArrayNameCellData:
    """Cover lines 636-638: cell data branch of _first_array_name."""

    def test_cell_data_only(self):
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        for i in range(4):
            pts.InsertNextPoint(i, 0, 0)
        grid.SetPoints(pts)

        cell = vtk.vtkTetra()
        for i in range(4):
            cell.GetPointIds().SetId(i, i)
        grid.InsertNextCell(cell.GetCellType(), cell.GetPointIds())

        arr = vtk.vtkFloatArray()
        arr.SetName("cell_temp")
        arr.SetNumberOfTuples(1)
        arr.SetValue(0, 42.0)
        grid.GetCellData().AddArray(arr)

        name = _first_array_name(grid)
        assert name == "cell_temp"


class TestFindArrayCellData:
    """Cover lines 650-652: cell data branch of _find_array."""

    def test_finds_cell_array(self):
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        for i in range(4):
            pts.InsertNextPoint(i, 0, 0)
        grid.SetPoints(pts)

        cell = vtk.vtkTetra()
        for i in range(4):
            cell.GetPointIds().SetId(i, i)
        grid.InsertNextCell(cell.GetCellType(), cell.GetPointIds())

        arr = vtk.vtkFloatArray()
        arr.SetName("sigma")
        arr.SetNumberOfTuples(1)
        arr.SetValue(0, 99.0)
        grid.GetCellData().AddArray(arr)

        result, assoc = _find_array(grid, "sigma")
        assert result is not None
        assert assoc == "cell"


class TestIs2dDegenerate:
    """Cover line 596: degenerate bounds (diag < 1e-30)."""

    def test_all_zero_bounds(self):
        assert _is_2d_dataset((0, 0, 0, 0, 0, 0)) is False


class TestAutoWarpScaleEdgeCases:
    """Cover lines 696, 701."""

    def test_zero_displacement(self):
        """Zero max displacement → scale = 1.0."""
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        for i in range(4):
            pts.InsertNextPoint(i, 0, 0)
        grid.SetPoints(pts)
        arr = vtk.vtkFloatArray()
        arr.SetName("disp")
        arr.SetNumberOfComponents(3)
        arr.SetNumberOfTuples(4)
        for i in range(4):
            arr.SetTuple3(i, 0.0, 0.0, 0.0)
        grid.GetPointData().AddArray(arr)
        assert _auto_warp_scale(grid, "disp") == 1.0

    def test_zero_diagonal(self):
        """Single point → diag near zero → scale = 1.0."""
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        grid.SetPoints(pts)
        arr = vtk.vtkFloatArray()
        arr.SetName("disp")
        arr.SetNumberOfComponents(3)
        arr.SetNumberOfTuples(1)
        arr.SetTuple3(0, 1.0, 0.0, 0.0)
        grid.GetPointData().AddArray(arr)
        assert _auto_warp_scale(grid, "disp") == 1.0


class TestSmartRepresentationEdgeCases:
    """Cover lines 318, 326, 333, 348."""

    def test_none_dataset_returns_default(self):
        """None from _ensure_dataset → default representation."""
        table = vtk.vtkTable()
        rep = smart_representation(table)
        assert rep.primary == "surface"

    def test_surface_with_edges_physics(self):
        """Physics with surface_with_edges → edges on."""
        from viznoir.engine.physics import PhysicsType

        grid = _make_3d_grid()
        physics = PhysicsType(
            name="stress",
            category="scalar",
            colormap="turbo",
            diverging=False,
            log_scale=False,
            camera_2d="top",
            camera_3d="isometric",
            representation="surface_with_edges",
            warp=False,
            streamlines=False,
        )
        rep = smart_representation(grid, physics)
        assert rep.edge_visibility is True

    def test_large_point_cloud_gaussian(self):
        """Point-only with >50k points → point_gaussian."""
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        for i in range(60000):
            pts.InsertNextPoint(float(i % 100), float(i // 100), 0.0)
        grid.SetPoints(pts)
        rep = smart_representation(grid)
        assert rep.primary == "point_gaussian"

    def test_auto_point_size_single_point(self):
        """Single point → default size 5.0."""
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        grid.SetPoints(pts)
        from viznoir.engine.physics import _auto_point_size

        assert _auto_point_size(grid) == 5.0


class TestSmartDefaultsCrossZero:
    """Cover line 552: zero-crossing override to coolwarm."""

    def test_zero_crossing_non_diverging(self):
        grid = _make_3d_grid()
        # Create a non-diverging field with zero-crossing range
        arr = vtk.vtkFloatArray()
        arr.SetName("custom_field")
        arr.SetNumberOfTuples(4)
        for i in range(4):
            arr.SetValue(i, float(i) - 1.5)  # -1.5, -0.5, 0.5, 1.5
        grid.GetPointData().AddArray(arr)
        sd = smart_defaults(grid, "custom_field")
        # custom_field is unknown → not diverging → zero-crossing → coolwarm
        assert sd.colormap == "coolwarm"

    def test_smart_defaults_none_dataset(self):
        """Cover line 518: non-DataSet → fallback SmartDefaults."""
        table = vtk.vtkTable()
        sd = smart_defaults(table)
        assert sd.physics.name == "unknown_scalar"
        assert sd.camera.preset == "isometric"


class TestRecommendTechniquesNoneDataset:
    """Cover line 388: non-DataSet → empty list."""

    def test_returns_empty_for_table(self):
        table = vtk.vtkTable()
        result = recommend_techniques(table, "p")
        assert result == []


class TestRecommendTechniquesPhysicsOverride:
    """Cover line 388, 432-433: warp technique."""

    def test_displacement_gets_warp(self):
        grid = _make_3d_grid()
        # displacement → warp technique
        u = vtk.vtkFloatArray()
        u.SetName("displacement")
        u.SetNumberOfComponents(3)
        u.SetNumberOfTuples(4)
        for i in range(4):
            u.SetTuple3(i, float(i) * 0.01, 0.0, 0.0)
        grid.GetPointData().AddArray(u)
        techniques = recommend_techniques(grid, "displacement")
        names = [t.technique for t in techniques]
        assert "warp" in names


class TestRecommendTechniques2DContour:
    """Cover lines 471-477: contour lines for 2D scalar."""

    def test_2d_scalar_gets_contour_lines(self):
        # Create 2D grid (flat in Z)
        grid = vtk.vtkUnstructuredGrid()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(0, 0, 0)
        pts.InsertNextPoint(10, 0, 0)
        pts.InsertNextPoint(10, 10, 0)
        pts.InsertNextPoint(0, 10, 0)
        grid.SetPoints(pts)

        cell = vtk.vtkQuad()
        for i in range(4):
            cell.GetPointIds().SetId(i, i)
        grid.InsertNextCell(cell.GetCellType(), cell.GetPointIds())

        arr = vtk.vtkFloatArray()
        arr.SetName("T")
        arr.SetNumberOfTuples(4)
        for i in range(4):
            arr.SetValue(i, float(i) * 100.0)
        grid.GetPointData().AddArray(arr)

        techniques = recommend_techniques(grid, "T")
        names = [t.technique for t in techniques]
        assert "contour_lines" in names
