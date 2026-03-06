"""Tests for tools/compare.py — compare tool implementation (mock-based, no GPU)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import vtk


@pytest.mark.asyncio
class TestCompareImplMocked:
    """Tests for compare_impl async function (mocked VTK rendering)."""

    async def test_side_by_side_default(self):
        """Test default side-by-side comparison."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG_single"
            mock_compose.return_value = b"\x89PNG_combined"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            result = await compare_impl(
                file_a="/data/case_a.vtk",
                file_b="/data/case_b.vtk",
                runner=runner,
            )

            assert result == b"\x89PNG_combined"
            assert mock_read.call_count == 2
            assert mock_cine.call_count == 2
            mock_compose.assert_called_once()

    async def test_side_by_side_with_field(self):
        """Test side-by-side with field name triggers shared range computation."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose, \
             patch("parapilot.engine.renderer._resolve_renderable") as mock_rr, \
             patch("parapilot.engine.renderer._resolve_array") as mock_ra, \
             patch("parapilot.engine.renderer._get_scalar_range") as mock_sr:

            data_a = MagicMock()
            data_b = MagicMock()
            mock_read.side_effect = [data_a, data_b]
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG_combined"
            mock_rr.side_effect = [data_a, data_b]
            mock_ra.side_effect = [("pressure", "point"), ("pressure", "point")]
            mock_sr.side_effect = [(0.0, 50.0), (10.0, 100.0)]

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            result = await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                field_name="pressure",
            )

            assert result == b"\x89PNG_combined"
            # Verify shared range was computed: min(0,10)=0, max(50,100)=100
            config = mock_cine.call_args_list[0][0][1]
            assert config.render.scalar_range == (0.0, 100.0)

    async def test_diff_mode(self):
        """Test diff comparison mode."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_diff") as mock_diff:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_diff.return_value = b"\x89PNG_diff"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            result = await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                mode="diff",
                field_name="velocity",
            )

            assert result == b"\x89PNG_diff"
            mock_diff.assert_called_once()

    async def test_latest_timestep(self):
        """Test timestep='latest' resolves correctly."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.readers.get_timesteps") as mock_ts, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_ts.return_value = [0.0, 1.0, 2.0]
            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                timestep="latest",
            )

            mock_ts.assert_called_once_with("/data/a.vtk")
            # Both reads should use timestep=2.0
            for call in mock_read.call_args_list:
                assert call[1]["timestep"] == 2.0 or call[0] == ("/data/a.vtk",) or call[0] == ("/data/b.vtk",)

    async def test_custom_labels(self):
        """Test that custom labels are passed to compose."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                label_a="Coarse",
                label_b="Fine",
            )

            args = mock_compose.call_args[0]
            assert args[2] == "Coarse"
            assert args[3] == "Fine"

    async def test_custom_dimensions(self):
        """Test custom width/height affect render config."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                width=1600,
                height=900,
            )

            config = mock_cine.call_args_list[0][0][1]
            assert config.render.width == 800  # half of 1600
            assert config.render.height == 900

    async def test_explicit_scalar_range(self):
        """Test that explicit scalar_range skips auto-computation."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                field_name="pressure",
                scalar_range=[0.0, 200.0],
            )

            config = mock_cine.call_args_list[0][0][1]
            assert config.render.scalar_range == (0.0, 200.0)

    async def test_unknown_mode_falls_back_to_side_by_side(self):
        """Test that unknown mode falls back to side_by_side."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                mode="unknown_mode",
            )

            mock_compose.assert_called_once()

    async def test_string_timestep(self):
        """Test string timestep is converted to float."""
        with patch("parapilot.engine.readers.read_dataset") as mock_read, \
             patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine, \
             patch("parapilot.tools.compare._compose_side_by_side") as mock_compose:

            mock_read.return_value = MagicMock()
            mock_cine.return_value = b"\x89PNG"
            mock_compose.return_value = b"\x89PNG"

            from parapilot.tools.compare import compare_impl
            runner = MagicMock()

            await compare_impl(
                file_a="/data/a.vtk",
                file_b="/data/b.vtk",
                runner=runner,
                timestep="3.14",
            )

            # Both reads should use timestep=3.14
            for call in mock_read.call_args_list:
                assert call[1].get("timestep") == 3.14 or call == mock_read.call_args_list[0]


def _make_grid_with_array(name: str = "pressure", n_points: int = 4) -> vtk.vtkUnstructuredGrid:
    """Create a simple grid with a point array for diff testing."""
    grid = vtk.vtkUnstructuredGrid()
    pts = vtk.vtkPoints()
    for i in range(n_points):
        pts.InsertNextPoint(float(i), 0, 0)
    grid.SetPoints(pts)

    arr = vtk.vtkFloatArray()
    arr.SetName(name)
    arr.SetNumberOfTuples(n_points)
    for i in range(n_points):
        arr.SetValue(i, float(i) * 10.0)
    grid.GetPointData().AddArray(arr)
    return grid


class TestComposeDiff:
    """Tests for _compose_diff function (VTK data, mocked rendering)."""

    def test_diff_basic(self):
        """Test basic diff computation between two datasets."""
        from parapilot.engine.renderer import RenderConfig
        from parapilot.engine.renderer_cine import CinematicConfig
        from parapilot.tools.compare import _compose_diff

        data_a = _make_grid_with_array("pressure", 4)
        data_b = _make_grid_with_array("pressure", 4)

        # Modify data_b values
        arr_b = data_b.GetPointData().GetArray("pressure")
        for i in range(4):
            arr_b.SetValue(i, float(i) * 10.0 + 5.0)

        rc = RenderConfig(width=200, height=150, colormap="plasma")
        config = CinematicConfig(render=rc, quality="draft")

        with patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine:
            mock_cine.return_value = b"\x89PNG_diff"
            result = _compose_diff(data_a, data_b, "pressure", config)

        assert result == b"\x89PNG_diff"
        mock_cine.assert_called_once()
        # Verify the diff dataset has the diff array
        diff_data = mock_cine.call_args[0][0]
        diff_arr = diff_data.GetPointData().GetArray("diff_pressure")
        assert diff_arr is not None
        # All diffs should be 5.0
        for i in range(4):
            assert abs(diff_arr.GetValue(i) - 5.0) < 0.01

    def test_diff_none_renderable_a(self):
        """Test diff with None renderable falls back to rendering data_b."""
        from parapilot.engine.renderer import RenderConfig
        from parapilot.engine.renderer_cine import CinematicConfig
        from parapilot.tools.compare import _compose_diff

        empty = vtk.vtkUnstructuredGrid()  # no points → _resolve_renderable returns None
        data_b = _make_grid_with_array("pressure", 4)

        rc = RenderConfig(width=200, height=150)
        config = CinematicConfig(render=rc, quality="draft")

        with patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine:
            mock_cine.return_value = b"\x89PNG"
            result = _compose_diff(empty, data_b, "pressure", config)

        assert result == b"\x89PNG"

    def test_diff_missing_array(self):
        """Test diff when field doesn't exist falls back to rendering."""
        from parapilot.engine.renderer import RenderConfig
        from parapilot.engine.renderer_cine import CinematicConfig
        from parapilot.tools.compare import _compose_diff

        data_a = _make_grid_with_array("pressure", 4)
        data_b = _make_grid_with_array("pressure", 4)

        rc = RenderConfig(width=200, height=150)
        config = CinematicConfig(render=rc, quality="draft")

        with patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine:
            mock_cine.return_value = b"\x89PNG"
            result = _compose_diff(data_a, data_b, "nonexistent", config)

        assert result == b"\x89PNG"

    def test_diff_size_mismatch(self):
        """Test diff handles datasets with different point counts."""
        from parapilot.engine.renderer import RenderConfig
        from parapilot.engine.renderer_cine import CinematicConfig
        from parapilot.tools.compare import _compose_diff

        data_a = _make_grid_with_array("pressure", 4)
        data_b = _make_grid_with_array("pressure", 6)

        rc = RenderConfig(width=200, height=150)
        config = CinematicConfig(render=rc, quality="draft")

        with patch("parapilot.engine.renderer_cine.cinematic_render") as mock_cine:
            mock_cine.return_value = b"\x89PNG"
            result = _compose_diff(data_a, data_b, "pressure", config)

        assert result == b"\x89PNG"
        # diff should use min_len = 4
        diff_data = mock_cine.call_args[0][0]
        diff_arr = diff_data.GetPointData().GetArray("diff_pressure")
        assert diff_arr is not None
