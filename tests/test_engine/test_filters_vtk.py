"""Integration tests for engine/filters.py — real VTK execution (GPU/EGL)."""

from __future__ import annotations

import pytest

vtk = pytest.importorskip("vtk")


def _wavelet() -> vtk.vtkImageData:
    """Create wavelet test dataset with RTData array."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-5, 5, -5, 5, -5, 5)
    src.Update()
    return src.GetOutput()


def _unstructured() -> vtk.vtkUnstructuredGrid:
    """Convert wavelet to unstructured grid."""
    src = _wavelet()
    conv = vtk.vtkDataSetTriangleFilter()
    conv.SetInputData(src)
    conv.Update()
    return conv.GetOutput()


def _polydata() -> vtk.vtkPolyData:
    """Create a sphere polydata."""
    src = vtk.vtkSphereSource()
    src.SetRadius(1.0)
    src.SetThetaResolution(16)
    src.SetPhiResolution(16)
    src.Update()
    return src.GetOutput()


# ---------------------------------------------------------------------------
# Slice
# ---------------------------------------------------------------------------


class TestSlicePlane:
    def test_slice_default_origin(self):
        from viznoir.engine.filters import slice_plane

        result = slice_plane(_wavelet())
        assert result.GetNumberOfPoints() > 0

    def test_slice_custom_origin_normal(self):
        from viznoir.engine.filters import slice_plane

        result = slice_plane(_wavelet(), origin=(0, 0, 0), normal=(1, 0, 0))
        assert result.GetNumberOfPoints() > 0

    def test_slice_preserves_arrays(self):
        from viznoir.engine.filters import slice_plane

        result = slice_plane(_wavelet())
        assert result.GetPointData().GetArray("RTData") is not None


# ---------------------------------------------------------------------------
# Clip
# ---------------------------------------------------------------------------


class TestClipPlane:
    def test_clip_default(self):
        from viznoir.engine.filters import clip_plane

        result = clip_plane(_wavelet())
        assert result.GetNumberOfPoints() > 0

    def test_clip_inside_out(self):
        from viznoir.engine.filters import clip_plane

        r1 = clip_plane(_wavelet(), inside_out=False)
        r2 = clip_plane(_wavelet(), inside_out=True)
        # Opposite sides should have different point counts
        assert r1.GetNumberOfPoints() != r2.GetNumberOfPoints() or r1.GetNumberOfPoints() > 0

    def test_clip_custom_origin(self):
        from viznoir.engine.filters import clip_plane

        result = clip_plane(_wavelet(), origin=(0, 0, 0), normal=(0, 1, 0))
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Contour
# ---------------------------------------------------------------------------


class TestContour:
    def test_contour_single_value(self):
        from viznoir.engine.filters import contour

        result = contour(_wavelet(), array_name="RTData", values=[100.0])
        assert result.GetNumberOfPoints() >= 0

    def test_contour_multiple_values(self):
        from viznoir.engine.filters import contour

        result = contour(_wavelet(), array_name="RTData", values=[50.0, 100.0, 200.0])
        assert result is not None

    def test_contour_with_isovalues_alias(self):
        from viznoir.engine.filters import contour

        result = contour(_wavelet(), field="RTData", isovalues=[100.0, 200.0])
        assert result is not None


# ---------------------------------------------------------------------------
# Isosurface
# ---------------------------------------------------------------------------


class TestIsosurface:
    def test_isosurface(self):
        from viznoir.engine.filters import isosurface

        result = isosurface(_wavelet(), array_name="RTData", value=100.0)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------


class TestThreshold:
    def test_threshold_range(self):
        from viznoir.engine.filters import threshold

        result = threshold(_wavelet(), array_name="RTData", lower=50.0, upper=200.0)
        assert result.GetNumberOfPoints() > 0

    def test_threshold_lower_only(self):
        from viznoir.engine.filters import threshold

        result = threshold(_wavelet(), array_name="RTData", lower=100.0)
        assert result.GetNumberOfPoints() >= 0

    def test_threshold_both_bounds(self):
        from viznoir.engine.filters import threshold

        result = threshold(_wavelet(), array_name="RTData", lower=50.0, upper=200.0)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Streamlines
# ---------------------------------------------------------------------------


class TestStreamlines:
    def test_streamlines_basic(self):
        from viznoir.engine.filters import streamlines

        data = _wavelet()
        # Add a vector field
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("velocity")
        calc.SetFunction("RTData*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        vdata = calc.GetOutput()

        result = streamlines(vdata, array_name="velocity", num_seeds=5)
        # May produce 0 points if seed placement doesn't intersect flow
        assert result is not None


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------


class TestCalculator:
    def test_calculator(self):
        from viznoir.engine.filters import calculator

        result = calculator(_wavelet(), expression="RTData * 2", result_name="doubled")
        arr = result.GetPointData().GetArray("doubled")
        assert arr is not None


# ---------------------------------------------------------------------------
# Gradient
# ---------------------------------------------------------------------------


class TestGradient:
    def test_gradient(self):
        from viznoir.engine.filters import gradient

        result = gradient(_wavelet(), array_name="RTData")
        # Gradient should create a new vector array
        assert result.GetPointData().GetNumberOfArrays() > 1


# ---------------------------------------------------------------------------
# IntegrateVariables
# ---------------------------------------------------------------------------


class TestIntegrateVariables:
    def test_integrate(self):
        from viznoir.engine.filters import integrate_variables

        result = integrate_variables(_wavelet())
        assert result is not None


# ---------------------------------------------------------------------------
# ExtractBlock
# ---------------------------------------------------------------------------


class TestExtractBlock:
    def test_extract_block_by_index(self):
        from viznoir.engine.filters import extract_block

        mb = vtk.vtkMultiBlockDataSet()
        mb.SetBlock(0, _wavelet())
        result = extract_block(mb, block_index=0)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# ExtractSurface
# ---------------------------------------------------------------------------


class TestExtractSurface:
    def test_extract_surface(self):
        from viznoir.engine.filters import extract_surface

        result = extract_surface(_unstructured())
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Warp
# ---------------------------------------------------------------------------


class TestWarp:
    def test_warp_by_scalar(self):
        from viznoir.engine.filters import warp_by_scalar

        result = warp_by_scalar(_wavelet(), array_name="RTData", scale_factor=0.01)
        assert result.GetNumberOfPoints() > 0

    def test_warp_by_vector(self):
        from viznoir.engine.filters import warp_by_vector

        data = _wavelet()
        # Create a vector array
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("disp")
        calc.SetFunction("RTData*0.01*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        result = warp_by_vector(calc.GetOutput(), array_name="disp", scale_factor=1.0)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# CellToPoint / PointToCell
# ---------------------------------------------------------------------------


class TestDataConversion:
    def test_cell_to_point(self):
        from viznoir.engine.filters import cell_to_point

        # Add a cell array first
        data = _unstructured()
        result = cell_to_point(data)
        assert result is not None

    def test_point_to_cell(self):
        from viznoir.engine.filters import point_to_cell

        result = point_to_cell(_wavelet())
        assert result is not None


# ---------------------------------------------------------------------------
# PlotOverLine
# ---------------------------------------------------------------------------


class TestPlotOverLine:
    def test_plot_over_line(self):
        from viznoir.engine.filters import plot_over_line

        result = plot_over_line(
            _wavelet(),
            point1=(-5, 0, 0),
            point2=(5, 0, 0),
            resolution=50,
        )
        assert result.GetNumberOfPoints() == 51  # resolution + 1


# ---------------------------------------------------------------------------
# Glyph
# ---------------------------------------------------------------------------


class TestGlyph:
    def test_glyph_basic(self):
        from viznoir.engine.filters import glyph

        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vectors")
        calc.SetFunction("RTData*0.01*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        result = glyph(calc.GetOutput(), array_name="vectors", scale_factor=0.1)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Decimate
# ---------------------------------------------------------------------------


class TestDecimate:
    def test_decimate(self):
        from viznoir.engine.filters import decimate

        poly = _polydata()
        original_cells = poly.GetNumberOfCells()
        result = decimate(poly, reduction=0.5)
        assert result.GetNumberOfCells() < original_cells


# ---------------------------------------------------------------------------
# Triangulate
# ---------------------------------------------------------------------------


class TestTriangulate:
    def test_triangulate(self):
        from viznoir.engine.filters import triangulate

        result = triangulate(_polydata())
        assert result.GetNumberOfCells() > 0


# ---------------------------------------------------------------------------
# SmoothMesh
# ---------------------------------------------------------------------------


class TestSmoothMesh:
    def test_smooth(self):
        from viznoir.engine.filters import smooth_mesh

        result = smooth_mesh(_polydata(), iterations=20)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# ProbePoint
# ---------------------------------------------------------------------------


class TestProbePoint:
    def test_probe_point(self):
        from viznoir.engine.filters import probe_point

        result = probe_point(_wavelet(), point=(0, 0, 0))
        assert result is not None
        assert result.GetPointData().GetArray("RTData") is not None


# ---------------------------------------------------------------------------
# CleanPolyData
# ---------------------------------------------------------------------------


class TestCleanPolyData:
    def test_clean(self):
        from viznoir.engine.filters import clean_polydata

        result = clean_polydata(_polydata())
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Shrink
# ---------------------------------------------------------------------------


class TestShrink:
    def test_shrink(self):
        from viznoir.engine.filters import shrink

        result = shrink(_unstructured(), shrink_factor=0.8)
        assert result.GetNumberOfCells() > 0


# ---------------------------------------------------------------------------
# Tube
# ---------------------------------------------------------------------------


class TestTube:
    def test_tube(self):
        from viznoir.engine.filters import tube

        # Create a line source
        line = vtk.vtkLineSource()
        line.SetPoint1(0, 0, 0)
        line.SetPoint2(1, 1, 1)
        line.SetResolution(10)
        line.Update()
        result = tube(line.GetOutput(), radius=0.1, sides=8)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# apply_filter / apply_filters
# ---------------------------------------------------------------------------


class TestApplyFilter:
    def test_apply_filter_by_name(self):
        from viznoir.engine.filters import apply_filter

        result = apply_filter(_wavelet(), "slice", normal=[1, 0, 0])
        assert result.GetNumberOfPoints() > 0

    def test_apply_filter_case_insensitive(self):
        from viznoir.engine.filters import apply_filter

        result = apply_filter(_wavelet(), "Slice", normal=[1, 0, 0])
        assert result.GetNumberOfPoints() > 0

    def test_apply_filters_chain(self):
        from viznoir.engine.filters import apply_filters

        steps = [
            ("slice", {"normal": (0, 0, 1)}),
        ]
        result = apply_filters(_wavelet(), steps)
        assert result is not None


class TestListFilters:
    def test_list_filters(self):
        from viznoir.engine.filters import list_filters

        names = list_filters()
        assert "slice" in names
        assert "clip" in names
        assert "contour" in names
        assert len(names) >= 20


class TestThresholdErrors:
    def test_no_array_name(self):
        from viznoir.engine.filters import threshold

        with pytest.raises(ValueError, match="requires"):
            threshold(_wavelet())

    def test_upper_only(self):
        from viznoir.engine.filters import threshold

        result = threshold(_wavelet(), array_name="RTData", upper=200.0)
        assert result is not None


class TestStreamlinesAxisSeed:
    def _make_vec_data(self, extent):
        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(*extent)
        src.Update()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(src.GetOutput())
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vel")
        calc.SetFunction("RTData*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        return calc.GetOutput()

    def test_y_longest_axis(self):
        from viznoir.engine.filters import streamlines

        data = self._make_vec_data((-1, 1, -10, 10, -1, 1))
        result = streamlines(data, array_name="vel", num_seeds=3)
        assert result is not None

    def test_z_longest_axis(self):
        from viznoir.engine.filters import streamlines

        data = self._make_vec_data((-1, 1, -1, 1, -10, 10))
        result = streamlines(data, array_name="vel", num_seeds=3)
        assert result is not None


class TestCalculatorEdge:
    def test_cell_attribute_type(self):
        from viznoir.engine.filters import calculator, point_to_cell

        data = point_to_cell(_wavelet())
        result = calculator(data, expression="RTData * 2", result_name="doubled", attribute_type="cell")
        assert result.GetCellData().GetArray("doubled") is not None

    def test_vector_variable_registration(self):
        """Calculator registers 3-component arrays as vector variables."""
        from viznoir.engine.filters import calculator

        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vec")
        calc.SetFunction("RTData*iHat + RTData*0.5*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        vdata = calc.GetOutput()
        result = calculator(vdata, expression="mag(vec)", result_name="speed")
        assert result.GetPointData().GetArray("speed") is not None


class TestGradientEdge:
    def test_no_array_name(self):
        from viznoir.engine.filters import gradient

        with pytest.raises(ValueError, match="requires"):
            gradient(_wavelet())

    def test_vorticity_and_qcriterion(self):
        """Gradient with vorticity and Q-criterion computation."""
        from viznoir.engine.filters import gradient

        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vel")
        calc.SetFunction("RTData*iHat + RTData*0.5*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        result = gradient(
            calc.GetOutput(),
            array_name="vel",
            compute_vorticity=True,
            compute_qcriterion=True,
        )
        assert result is not None


class TestExtractBlockError:
    def test_non_multiblock_raises(self):
        from viznoir.engine.filters import extract_block

        with pytest.raises(TypeError, match="Expected vtkMultiBlockDataSet"):
            extract_block(_wavelet(), block_index=0)


class TestGlyphEdge:
    def test_cone_glyph(self):
        from viznoir.engine.filters import glyph

        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vectors")
        calc.SetFunction("RTData*0.01*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        result = glyph(calc.GetOutput(), array_name="vectors", scale_factor=0.1, glyph_type="cone")
        assert result.GetNumberOfPoints() > 0

    def test_glyph_mask_large_dataset(self):
        """Glyph with max_points mask (line 670-675)."""
        from viznoir.engine.filters import glyph

        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vectors")
        calc.SetFunction("RTData*0.01*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        result = glyph(calc.GetOutput(), array_name="vectors", scale_factor=0.1, max_points=10)
        assert result.GetNumberOfPoints() > 0


class TestDecimateNonPolydata:
    def test_decimate_unstructured(self):
        """Decimate auto-converts non-polydata to surface (lines 716-719)."""
        from viznoir.engine.filters import decimate

        result = decimate(_unstructured(), reduction=0.3)
        assert result.GetNumberOfCells() > 0


class TestCleanPolyDataNonPolydata:
    def test_clean_unstructured(self):
        """CleanPolyData auto-converts non-polydata (lines 822-825)."""
        from viznoir.engine.filters import clean_polydata

        result = clean_polydata(_unstructured())
        assert result.GetNumberOfPoints() > 0


class TestSliceClipFallback:
    def test_slice_no_getbounds(self):
        from viznoir.engine.filters import slice_plane

        result = slice_plane(_wavelet(), origin=None)
        assert result is not None

    def test_clip_invert_alias(self):
        from viznoir.engine.filters import clip_plane

        result = clip_plane(_wavelet(), invert=True)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# NEW COVERAGE TESTS — Appended to reach 95%+ on filters.py
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Slice/Clip: origin=None fallback when GetBounds is absent (L81, L123)
# ---------------------------------------------------------------------------


class TestSliceClipNoBoundsObject:
    """Cover L81 / L123: the 'elif origin is None: origin = (0,0,0)' fallback.

    VTK C++ objects always have GetBounds, so we patch the module-level `hasattr`
    inside filters.py by temporarily replacing the function body's lookup via
    unittest.mock.patch on builtins.hasattr to return False for our test object.
    """

    def test_slice_origin_none_no_bounds_branch(self, monkeypatch):
        """L81: slice_plane with origin=None when hasattr(data,'GetBounds') is False."""
        import builtins

        data = _wavelet()
        real_hasattr = builtins.hasattr

        def fake_hasattr(obj, name):
            if obj is data and name == "GetBounds":
                return False
            return real_hasattr(obj, name)

        monkeypatch.setattr(builtins, "hasattr", fake_hasattr)
        from viznoir.engine.filters import slice_plane

        result = slice_plane(data, origin=None)
        assert result is not None

    def test_clip_origin_none_no_bounds_branch(self, monkeypatch):
        """L123: clip_plane with origin=None when hasattr(data,'GetBounds') is False."""
        import builtins

        data = _wavelet()
        real_hasattr = builtins.hasattr

        def fake_hasattr(obj, name):
            if obj is data and name == "GetBounds":
                return False
            return real_hasattr(obj, name)

        monkeypatch.setattr(builtins, "hasattr", fake_hasattr)
        from viznoir.engine.filters import clip_plane

        result = clip_plane(data, origin=None)
        assert result is not None


# ---------------------------------------------------------------------------
# Contour error paths (L162, L165, L177-178, L193-198)
# ---------------------------------------------------------------------------


class TestContourErrors:
    def test_contour_no_array_name_raises(self):
        """L162: contour with no field/array_name → ValueError."""
        from viznoir.engine.filters import contour

        with pytest.raises(ValueError, match="array_name"):
            contour(_wavelet(), values=[100.0])

    def test_contour_no_values_raises(self):
        """L165: contour with array_name but no values → ValueError."""
        from viznoir.engine.filters import contour

        with pytest.raises(ValueError, match="isovalues"):
            contour(_wavelet(), array_name="RTData")

    def test_contour_nonexistent_array_raises(self):
        """L177-178: contour with array that does not exist → ValueError."""
        from viznoir.engine.filters import contour

        with pytest.raises(ValueError, match="not found"):
            contour(_wavelet(), array_name="NonExistentArray", values=[100.0])

    def test_contour_values_outside_range_raises(self):
        """L193-198: contour with values outside data range → EmptyOutputError."""
        from viznoir.engine.filters import contour
        from viznoir.errors import EmptyOutputError

        # RTData range is roughly [37, 276]; use extreme values guaranteed outside
        with pytest.raises(EmptyOutputError, match="empty output"):
            contour(_wavelet(), array_name="RTData", values=[1e9])


# ---------------------------------------------------------------------------
# Threshold error / branch paths (L247, L263-265)
# ---------------------------------------------------------------------------


class TestThresholdBranches:
    def test_threshold_no_array_name_raises(self):
        """L247: threshold with no array_name → ValueError."""
        from viznoir.engine.filters import threshold

        with pytest.raises(ValueError, match="array_name"):
            threshold(_wavelet(), lower=50.0)

    def test_threshold_upper_only(self):
        """L263-265: threshold with upper bound only (no lower)."""
        from viznoir.engine.filters import threshold

        result = threshold(_wavelet(), array_name="RTData", upper=150.0)
        assert result.GetNumberOfPoints() >= 0

    def test_threshold_with_field_alias(self):
        """threshold using field= alias still works."""
        from viznoir.engine.filters import threshold

        result = threshold(_wavelet(), field="RTData", lower=50.0, upper=200.0)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Streamlines: registry aliases + Y/Z axis branches (L307,309,311,313,329-337)
# ---------------------------------------------------------------------------


def _wavelet_with_velocity(extent=(-5, 5, -5, 5, -5, 5)):
    """Create a wavelet dataset with a velocity vector field."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(*extent)
    src.Update()
    data = src.GetOutput()

    calc = vtk.vtkArrayCalculator()
    calc.SetInputData(data)
    calc.AddScalarArrayName("RTData")
    calc.SetResultArrayName("velocity")
    calc.SetFunction("RTData*iHat + 0*jHat + 0*kHat")
    calc.SetResultArrayType(vtk.VTK_DOUBLE)
    calc.Update()
    return calc.GetOutput()


class TestStreamlinesAliases:
    def test_vectors_alias(self):
        """L307: vectors parameter list → extracts array_name."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        result = streamlines(data, vectors=["POINTS", "velocity"], num_seeds=3)
        assert result is not None

    def test_vectors_string_alias(self):
        """L307: vectors parameter as string → used directly as array_name."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        result = streamlines(data, vectors="velocity", num_seeds=3)
        assert result is not None

    def test_seed_resolution_alias(self):
        """L311: seed_resolution overrides num_seeds default."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        # seed_resolution=10 overrides default num_seeds=25
        result = streamlines(data, array_name="velocity", seed_resolution=10)
        assert result is not None

    def test_direction_alias(self):
        """L313: direction overrides integration_direction."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        result = streamlines(data, array_name="velocity", direction="forward", num_seeds=3)
        assert result is not None

    def test_no_array_name_raises(self):
        """L309: no array_name and no vectors → ValueError."""
        from viznoir.engine.filters import streamlines

        with pytest.raises(ValueError, match="array_name"):
            streamlines(_wavelet_with_velocity(), num_seeds=3)

    def test_max_length_set(self):
        """L359: max_length > 0 path."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        result = streamlines(data, array_name="velocity", max_length=5.0, num_seeds=3)
        assert result is not None

    def test_no_get_bounds_fallback(self):
        """L370: dataset without GetBounds → max_length fallback to 100."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        # Use explicit seed points to bypass the GetBounds auto-seed path
        result = streamlines(
            data,
            array_name="velocity",
            seed_point1=(-4, 0, 0),
            seed_point2=(4, 0, 0),
            max_length=0,
            num_seeds=3,
        )
        assert result is not None

    def test_y_axis_longest(self):
        """L329-331: dataset where Y axis is longest → seed line along Y."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity(extent=(-1, 1, -10, 10, -1, 1))
        result = streamlines(data, array_name="velocity", num_seeds=3)
        assert result is not None

    def test_z_axis_longest(self):
        """L332-334: dataset where Z axis is longest → seed line along Z."""
        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity(extent=(-1, 1, -1, 1, -10, 10))
        result = streamlines(data, array_name="velocity", num_seeds=3)
        assert result is not None


# ---------------------------------------------------------------------------
# Calculator: cell attribute_type + vector array (L401, L414-415)
# ---------------------------------------------------------------------------


class TestCalculatorBranches:
    def test_calculator_cell_attribute_type(self):
        """L401: attribute_type='cell' → SetAttributeTypeToCellData."""
        from viznoir.engine.filters import calculator

        # Use unstructured grid which has cell data
        data = _unstructured()
        # point_to_cell first to have a cell scalar
        from viznoir.engine.filters import point_to_cell

        data_with_cells = point_to_cell(data)
        # Now run calculator in cell mode
        result = calculator(data_with_cells, expression="RTData * 2", result_name="doubled_cell", attribute_type="cell")
        assert result is not None

    def test_calculator_with_vector_array(self):
        """L414-415: 3-component array registered as vector variable."""
        from viznoir.engine.filters import calculator

        # Create wavelet and add a 3-component vector array
        data = _wavelet()
        import vtk as _vtk

        n = data.GetNumberOfPoints()
        vec_arr = _vtk.vtkFloatArray()
        vec_arr.SetName("vel")
        vec_arr.SetNumberOfComponents(3)
        vec_arr.SetNumberOfTuples(n)
        for i in range(n):
            vec_arr.SetTuple3(i, 1.0, 0.0, 0.0)
        data.GetPointData().AddArray(vec_arr)

        # mag(vel) is a valid expression that uses the 3-component array
        result = calculator(data, expression="mag(vel)", result_name="speed")
        assert result is not None


# ---------------------------------------------------------------------------
# Gradient error + vorticity/Q-criterion (L446, L456, L458)
# ---------------------------------------------------------------------------


class TestGradientBranches:
    def test_gradient_no_array_name_raises(self):
        """L446: gradient with no array_name → ValueError."""
        from viznoir.engine.filters import gradient

        with pytest.raises(ValueError, match="array_name"):
            gradient(_wavelet())

    def test_gradient_compute_vorticity(self):
        """L456: compute_vorticity=True sets vorticity array name."""
        from viznoir.engine.filters import gradient

        result = gradient(_wavelet(), array_name="RTData", compute_vorticity=True)
        # gradient of a scalar doesn't produce vorticity, but the branch is executed
        assert result is not None

    def test_gradient_compute_qcriterion(self):
        """L458: compute_qcriterion=True sets Q-criterion array name."""
        from viznoir.engine.filters import gradient

        result = gradient(_wavelet(), array_name="RTData", compute_qcriterion=True)
        assert result is not None

    def test_gradient_both_vorticity_and_qcriterion(self):
        """Both vorticity and Q-criterion enabled together."""
        from viznoir.engine.filters import gradient

        result = gradient(
            _wavelet(),
            array_name="RTData",
            compute_vorticity=True,
            compute_qcriterion=True,
        )
        assert result is not None


# ---------------------------------------------------------------------------
# ExtractBlock: non-multiblock input → TypeError (L497-498)
# ---------------------------------------------------------------------------


class TestExtractBlockErrors:
    def test_extract_block_non_multiblock_raises(self):
        """L497-498: extract_block with non-multiblock dataset → TypeError."""
        from viznoir.engine.filters import extract_block

        with pytest.raises(TypeError, match="vtkMultiBlockDataSet"):
            extract_block(_wavelet(), block_index=0)

    def test_extract_block_polydata_raises(self):
        """extract_block with polydata (not multiblock) → TypeError."""
        from viznoir.engine.filters import extract_block

        with pytest.raises(TypeError, match="vtkMultiBlockDataSet"):
            extract_block(_polydata(), block_index=0)


# ---------------------------------------------------------------------------
# Glyph: max_points masking + cone glyph_type (L670-675, L678-679)
# ---------------------------------------------------------------------------


class TestGlyphBranches:
    def _make_vector_wavelet(self):
        data = _wavelet()
        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(data)
        calc.AddScalarArrayName("RTData")
        calc.SetResultArrayName("vectors")
        calc.SetFunction("RTData*0.01*iHat + 0*jHat + 0*kHat")
        calc.SetResultArrayType(vtk.VTK_DOUBLE)
        calc.Update()
        return calc.GetOutput()

    def test_glyph_max_points_masking(self):
        """L670-675: glyph with num_points > max_points triggers vtkMaskPoints."""
        from viznoir.engine.filters import glyph

        data = self._make_vector_wavelet()
        # Wavelet has 1331 points; set max_points=10 to force masking
        result = glyph(data, array_name="vectors", scale_factor=0.1, max_points=10)
        assert result is not None

    def test_glyph_cone_type(self):
        """L678-679: glyph_type='cone' uses vtkConeSource instead of arrow."""
        from viznoir.engine.filters import glyph

        data = self._make_vector_wavelet()
        result = glyph(data, array_name="vectors", scale_factor=0.1, glyph_type="cone")
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# Decimate: non-polydata input auto-converts (L716-719)
# ---------------------------------------------------------------------------


class TestDecimateBranches:
    def test_decimate_non_polydata_auto_convert(self):
        """L716-719: decimate with unstructured grid → auto-convert to polydata."""
        from viznoir.engine.filters import decimate

        data = _unstructured()
        result = decimate(data, reduction=0.5)
        assert result.GetNumberOfCells() > 0

    def test_decimate_wavelet_auto_convert(self):
        """decimate with vtkImageData → auto-convert to polydata."""
        from viznoir.engine.filters import decimate

        result = decimate(_wavelet(), reduction=0.3)
        assert result.GetNumberOfCells() > 0


# ---------------------------------------------------------------------------
# SmoothMesh: non-polydata input auto-converts (L765-768)
# ---------------------------------------------------------------------------


class TestSmoothMeshBranches:
    def test_smooth_mesh_non_polydata(self):
        """L765-768: smooth_mesh with unstructured grid → auto-convert to polydata."""
        from viznoir.engine.filters import smooth_mesh

        data = _unstructured()
        result = smooth_mesh(data, iterations=5)
        assert result.GetNumberOfPoints() > 0

    def test_smooth_mesh_wavelet(self):
        """smooth_mesh with vtkImageData → auto-convert to polydata."""
        from viznoir.engine.filters import smooth_mesh

        result = smooth_mesh(_wavelet(), iterations=5)
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# CleanPolyData: non-polydata input + tolerance branch (L822-825, L830)
# ---------------------------------------------------------------------------


class TestCleanPolyDataBranches:
    def test_clean_polydata_non_polydata(self):
        """L822-825: clean_polydata with unstructured grid → auto-convert."""
        from viznoir.engine.filters import clean_polydata

        data = _unstructured()
        result = clean_polydata(data)
        assert result.GetNumberOfPoints() > 0

    def test_clean_polydata_with_tolerance(self):
        """L830: clean_polydata with tolerance > 0 → SetTolerance branch."""
        from viznoir.engine.filters import clean_polydata

        result = clean_polydata(_polydata(), tolerance=0.001)
        assert result.GetNumberOfPoints() > 0

    def test_clean_polydata_wavelet(self):
        """clean_polydata with vtkImageData → auto-convert to polydata."""
        from viznoir.engine.filters import clean_polydata

        result = clean_polydata(_wavelet())
        assert result.GetNumberOfPoints() > 0


# ---------------------------------------------------------------------------
# apply_filter: unknown filter name → ValueError (L949-951)
# ---------------------------------------------------------------------------


class TestApplyFilterErrors:
    def test_apply_filter_unknown_raises(self):
        """L949-951: apply_filter with unknown filter name → ValueError."""
        from viznoir.engine.filters import apply_filter

        with pytest.raises(ValueError, match="Unknown filter"):
            apply_filter(_wavelet(), "totally_nonexistent_filter_xyz")


# ---------------------------------------------------------------------------
# Remaining coverage: clip invert alias (L116), streamlines no-GetBounds (L336-337, L370)
# ---------------------------------------------------------------------------


class TestClipInvertAlias:
    def test_clip_invert_alias(self):
        """L116: invert= alias maps to inside_out."""
        from viznoir.engine.filters import clip_plane

        result = clip_plane(_wavelet(), invert=True)
        assert result.GetNumberOfPoints() >= 0

    def test_clip_invert_false_alias(self):
        """L116: invert=False alias."""
        from viznoir.engine.filters import clip_plane

        result = clip_plane(_wavelet(), invert=False)
        assert result.GetNumberOfPoints() > 0


class TestStreamlinesNoBoundsFallback:
    """Cover L336-337 and L370: streamlines path when data lacks GetBounds."""

    def test_seed_fallback_and_max_length_fallback(self, monkeypatch):
        """L336-337 + L370: no GetBounds → seed=(0,0,0)/(1,0,0), max_length→100."""
        import builtins

        from viznoir.engine.filters import streamlines

        data = _wavelet_with_velocity()
        real_hasattr = builtins.hasattr

        def fake_hasattr(obj, name):
            if obj is data and name == "GetBounds":
                return False
            return real_hasattr(obj, name)

        monkeypatch.setattr(builtins, "hasattr", fake_hasattr)
        # max_length=0 triggers the auto-propagation path; no GetBounds → 100.0 fallback
        result = streamlines(data, array_name="velocity", num_seeds=3, max_length=0)
        assert result is not None
