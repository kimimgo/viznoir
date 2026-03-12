"""Tests for engine/annotation.py — VTK-native 3D scene annotations."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from viznoir.engine.annotation import (
    ANNOTATION_COLORS,
    _annotation_actors,
    _track,
    add_arrow,
    add_caption,
    add_label,
    clear_annotations,
)


# ---------------------------------------------------------------------------
# ANNOTATION_COLORS
# ---------------------------------------------------------------------------


class TestAnnotationColors:
    def test_has_expected_keys(self):
        expected = {"red", "orange", "cyan", "pink", "green", "yellow", "white", "muted"}
        assert expected == set(ANNOTATION_COLORS.keys())

    def test_all_values_are_rgb_tuples(self):
        for name, color in ANNOTATION_COLORS.items():
            assert len(color) == 3, f"{name} should be 3-tuple"
            for c in color:
                assert 0.0 <= c <= 1.0, f"{name} component {c} out of [0,1]"


# ---------------------------------------------------------------------------
# add_caption (mock VTK)
# ---------------------------------------------------------------------------


class TestAddCaption:
    @patch("viznoir.engine.annotation.vtk", create=True)
    def test_creates_caption_actor(self, mock_vtk_module):
        import vtk as _vtk

        mock_vtk_module.vtkCaptionActor2D = _vtk.vtkCaptionActor2D

        renderer = MagicMock()
        renderer_id = id(renderer)

        # Clean state
        _annotation_actors.pop(renderer_id, None)

        actor = add_caption(renderer, point=(1.0, 2.0, 3.0), text="TEST")

        assert isinstance(actor, _vtk.vtkCaptionActor2D)
        renderer.AddViewProp.assert_called_once_with(actor)

        # Verify tracked
        assert renderer_id in _annotation_actors
        assert actor in _annotation_actors[renderer_id]

        # Cleanup
        _annotation_actors.pop(renderer_id, None)

    def test_default_border_is_false(self):
        import vtk as _vtk

        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_caption(renderer, point=(0, 0, 0), text="TEST")
        # Border is set to False by default
        assert actor.GetBorder() is False or actor.GetBorder() == 0

        _annotation_actors.pop(renderer_id, None)

    def test_leader_enabled_by_default(self):
        import vtk as _vtk

        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_caption(renderer, point=(0, 0, 0), text="TEST", leader=True)
        assert actor.GetLeader()

        _annotation_actors.pop(renderer_id, None)

    def test_custom_color(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        color = (1.0, 0.0, 0.0)
        actor = add_caption(renderer, point=(0, 0, 0), text="RED", color=color)
        tp = actor.GetCaptionTextProperty()
        actual = tp.GetColor()
        assert actual == pytest.approx(color, abs=0.01)

        _annotation_actors.pop(renderer_id, None)


# ---------------------------------------------------------------------------
# add_label (mock VTK)
# ---------------------------------------------------------------------------


class TestAddLabel:
    def test_creates_text_actor(self):
        import vtk as _vtk

        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_label(renderer, text="TITLE", x=0.5, y=0.9)

        assert isinstance(actor, _vtk.vtkTextActor)
        renderer.AddViewProp.assert_called_once_with(actor)

        _annotation_actors.pop(renderer_id, None)

    def test_normalized_display_coordinates(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_label(renderer, text="TEST", x=0.1, y=0.8)
        coord = actor.GetPositionCoordinate()
        # Coordinate system should be set to NormalizedDisplay
        assert coord.GetCoordinateSystem() == 1  # VTK NormalizedDisplay

        _annotation_actors.pop(renderer_id, None)

    def test_bold_on_by_default(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_label(renderer, text="BOLD")
        tp = actor.GetTextProperty()
        assert tp.GetBold()

        _annotation_actors.pop(renderer_id, None)

    def test_bold_off(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_label(renderer, text="THIN", bold=False)
        tp = actor.GetTextProperty()
        assert not tp.GetBold()

        _annotation_actors.pop(renderer_id, None)


# ---------------------------------------------------------------------------
# add_arrow
# ---------------------------------------------------------------------------


class TestAddArrow:
    def test_creates_actor(self):
        import vtk as _vtk

        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_arrow(renderer, start=(0, 0, 0), end=(1, 0, 0))

        assert isinstance(actor, _vtk.vtkActor)
        renderer.AddActor.assert_called_once()

        _annotation_actors.pop(renderer_id, None)

    def test_degenerate_arrow_invisible(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_arrow(renderer, start=(0, 0, 0), end=(0, 0, 0))
        # Degenerate (zero-length) arrow should be invisible
        assert not actor.GetVisibility()

        _annotation_actors.pop(renderer_id, None)

    def test_arrow_direction_x(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_arrow(renderer, start=(0, 0, 0), end=(5, 0, 0))
        # Arrow should be visible
        assert actor.GetVisibility()

        _annotation_actors.pop(renderer_id, None)

    def test_arrow_direction_diagonal(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = add_arrow(renderer, start=(1, 1, 1), end=(4, 5, 6))
        assert actor.GetVisibility()

        _annotation_actors.pop(renderer_id, None)

    def test_custom_color(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        color = (1.0, 0.0, 0.5)
        actor = add_arrow(renderer, start=(0, 0, 0), end=(1, 0, 0), color=color)
        actual = actor.GetProperty().GetColor()
        assert actual == pytest.approx(color, abs=0.01)

        _annotation_actors.pop(renderer_id, None)


# ---------------------------------------------------------------------------
# clear_annotations
# ---------------------------------------------------------------------------


class TestClearAnnotations:
    def test_clear_empty(self):
        renderer = MagicMock()
        _annotation_actors.pop(id(renderer), None)
        count = clear_annotations(renderer)
        assert count == 0

    def test_clear_removes_tracked_actors(self):
        renderer = MagicMock()
        renderer_id = id(renderer)

        # Add some actors
        actors = [MagicMock(), MagicMock(), MagicMock()]
        _annotation_actors[renderer_id] = actors.copy()

        count = clear_annotations(renderer)

        assert count == 3
        for actor in actors:
            renderer.RemoveViewProp.assert_any_call(actor)
        assert renderer_id not in _annotation_actors

    def test_clear_idempotent(self):
        renderer = MagicMock()
        _annotation_actors[id(renderer)] = [MagicMock()]

        clear_annotations(renderer)
        count = clear_annotations(renderer)
        assert count == 0


# ---------------------------------------------------------------------------
# _track
# ---------------------------------------------------------------------------


class TestTrack:
    def test_creates_new_list(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors.pop(renderer_id, None)

        actor = MagicMock()
        _track(renderer, actor)

        assert _annotation_actors[renderer_id] == [actor]
        _annotation_actors.pop(renderer_id, None)

    def test_appends_to_existing(self):
        renderer = MagicMock()
        renderer_id = id(renderer)
        _annotation_actors[renderer_id] = [MagicMock()]

        actor2 = MagicMock()
        _track(renderer, actor2)

        assert len(_annotation_actors[renderer_id]) == 2
        assert _annotation_actors[renderer_id][-1] is actor2
        _annotation_actors.pop(renderer_id, None)
