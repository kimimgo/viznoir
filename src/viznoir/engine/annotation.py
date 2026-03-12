"""VTK-native 3D scene annotations — rendered inside the VTK pipeline.

Unlike ``overlay.py`` (Pillow 2D post-render), this module adds annotations
**directly to the VTK renderer**. They participate in the 3D scene:

- Leader lines connect labels to 3D attachment points
- Labels survive camera rotation (they are VTK actors)
- Arrows show physical direction in 3D space

Design principles (from user feedback):

1. **Max 2–3 captions per scene** — more causes overlap and clutter.
2. **Use Border(False)** — the default VTK border box is too large and looks
   like an empty rectangle. Tight background-only styling is cleaner.
3. **Spread attachment points** to opposite quadrants of the render.
4. **For HUD info** (title, stats), use 2D labels at normalized display
   coordinates — they never overlap with 3D data.
5. **CaptionActor2D** for 3D-attached labels with leader lines.
6. **TextActor** for fixed-position 2D overlays.
7. **3D arrows** for showing physical direction (flow, force, gradient).

Usage::

    from viznoir.engine.annotation import add_caption, add_label, add_arrow

    # 3D label with leader line to a point in the dataset
    add_caption(renderer, point=(1.0, 2.0, 3.0), text="PEAK T=1800K",
                color=(1.0, 0.35, 0.3))

    # Fixed 2D overlay (title)
    add_label(renderer, text="Combustion Analysis", x=0.03, y=0.93)

    # Directional arrow showing flow or force
    add_arrow(renderer, start=(0, 0, 0), end=(1, 0, 0),
              color=(0.47, 0.75, 1.0))
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import vtk

__all__ = [
    "add_caption",
    "add_label",
    "add_arrow",
    "clear_annotations",
    "ANNOTATION_COLORS",
]

# ---------------------------------------------------------------------------
# Named colors for consistent annotation styling
# ---------------------------------------------------------------------------

ANNOTATION_COLORS: dict[str, tuple[float, float, float]] = {
    "red": (1.0, 0.35, 0.3),
    "orange": (0.94, 0.53, 0.24),
    "cyan": (0.47, 0.75, 1.0),
    "pink": (0.97, 0.47, 0.73),
    "green": (0.25, 0.73, 0.31),
    "yellow": (1.0, 0.85, 0.3),
    "white": (1.0, 1.0, 1.0),
    "muted": (0.55, 0.58, 0.63),
}

# Background for label boxes — dark, semi-transparent
_BG_COLOR = (0.05, 0.06, 0.08)
_BG_OPACITY = 0.75

# Track annotation actors so we can clear them
_annotation_actors: dict[int, list] = {}  # renderer id -> [actors]


def add_caption(
    renderer: vtk.vtkRenderer,
    point: tuple[float, float, float],
    text: str,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    fontsize: int = 13,
    *,
    border: bool = False,
    leader: bool = True,
) -> vtk.vtkCaptionActor2D:
    """Add a 3D-attached label with leader line to a point in the scene.

    The label text is positioned automatically by VTK based on the 3D
    attachment point. A thin leader line connects the text to the point.

    Args:
        renderer: VTK renderer to add the annotation to.
        point: 3D coordinates (x, y, z) of the attachment point.
        text: Label text (supports multi-line with ``\\n``).
        color: RGB color tuple, each component in [0, 1].
        fontsize: Font size in pixels.
        border: Whether to show the VTK border box. Default False
            because the default box is too large and distracting.
        leader: Whether to show the leader line from text to point.

    Returns:
        The created vtkCaptionActor2D (for later removal or modification).
    """
    import vtk as _vtk

    caption = _vtk.vtkCaptionActor2D()
    caption.SetAttachmentPoint(*point)
    caption.SetCaption(text)
    caption.GetTextActor().SetTextScaleModeToNone()

    tp = caption.GetCaptionTextProperty()
    tp.SetFontSize(fontsize)
    tp.SetColor(*color)
    tp.BoldOn()
    tp.SetFontFamilyToCourier()
    tp.SetBackgroundColor(*_BG_COLOR)
    tp.SetBackgroundOpacity(_BG_OPACITY)

    caption.SetBorder(border)
    caption.SetPadding(2)
    caption.SetLeader(leader)
    caption.GetProperty().SetColor(*color)
    caption.GetProperty().SetLineWidth(1.5)

    renderer.AddViewProp(caption)
    _track(renderer, caption)
    return caption


def add_label(
    renderer: vtk.vtkRenderer,
    text: str,
    x: float = 0.03,
    y: float = 0.93,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    fontsize: int = 16,
    *,
    bold: bool = True,
) -> vtk.vtkTextActor:
    """Add a fixed 2D text overlay at normalized display coordinates.

    Unlike ``add_caption``, this label stays fixed on screen regardless
    of camera movement. Use for titles, stats, and HUD information.

    Coordinates: (0, 0) = bottom-left, (1, 1) = top-right.

    Args:
        renderer: VTK renderer.
        text: Label text.
        x: Horizontal position in normalized display [0, 1].
        y: Vertical position in normalized display [0, 1].
        color: RGB color tuple.
        fontsize: Font size in pixels.
        bold: Whether to render bold text.

    Returns:
        The created vtkTextActor (for dynamic text updates via ``.SetInput()``).
    """
    import vtk as _vtk

    actor = _vtk.vtkTextActor()
    actor.SetInput(text)

    tp = actor.GetTextProperty()
    tp.SetFontSize(fontsize)
    tp.SetColor(*color)
    tp.SetFontFamilyToCourier()
    tp.SetBackgroundColor(*_BG_COLOR)
    tp.SetBackgroundOpacity(_BG_OPACITY)
    if bold:
        tp.BoldOn()

    actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
    actor.GetPositionCoordinate().SetValue(x, y)

    renderer.AddViewProp(actor)
    _track(renderer, actor)
    return actor


def add_arrow(
    renderer: vtk.vtkRenderer,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    color: tuple[float, float, float] = (0.47, 0.75, 1.0),
    shaft_radius: float = 0.02,
    tip_radius: float = 0.06,
    tip_length: float = 0.2,
) -> vtk.vtkActor:
    """Add a 3D directional arrow showing a physical vector (flow, force, gradient).

    The arrow is oriented from ``start`` to ``end`` in world coordinates.
    Arrow length equals the distance between start and end.

    Args:
        renderer: VTK renderer.
        start: Arrow base coordinates (x, y, z).
        end: Arrow tip coordinates (x, y, z).
        color: RGB color tuple.
        shaft_radius: Arrow shaft radius (fraction of length).
        tip_radius: Arrow tip cone radius.
        tip_length: Arrow tip length (fraction of total).

    Returns:
        The created vtkActor.
    """
    import vtk as _vtk

    arrow_src = _vtk.vtkArrowSource()
    arrow_src.SetShaftRadius(shaft_radius)
    arrow_src.SetTipRadius(tip_radius)
    arrow_src.SetTipLength(tip_length)
    arrow_src.Update()

    s = np.asarray(start, dtype=np.float64)
    e = np.asarray(end, dtype=np.float64)
    direction = e - s
    length = float(np.linalg.norm(direction))
    if length < 1e-10:
        # Degenerate arrow — add invisible actor to keep API consistent
        actor = _vtk.vtkActor()
        actor.SetVisibility(False)
        renderer.AddActor(actor)
        _track(renderer, actor)
        return actor

    direction = direction / length

    # Build rotation matrix: arrow default is +X, rotate to `direction`
    arbitrary = np.array([0.0, 0.0, 1.0]) if abs(direction[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    cross1 = np.cross(direction, arbitrary)
    cross1 = cross1 / float(np.linalg.norm(cross1))
    cross2 = np.cross(cross1, direction)

    matrix = _vtk.vtkMatrix4x4()
    for i in range(3):
        matrix.SetElement(i, 0, direction[i] * length)
        matrix.SetElement(i, 1, cross1[i] * length)
        matrix.SetElement(i, 2, cross2[i] * length)
        matrix.SetElement(i, 3, s[i])

    transform = _vtk.vtkTransform()
    transform.SetMatrix(matrix)

    tf = _vtk.vtkTransformPolyDataFilter()
    tf.SetInputConnection(arrow_src.GetOutputPort())
    tf.SetTransform(transform)
    tf.Update()

    mapper = _vtk.vtkPolyDataMapper()
    mapper.SetInputData(tf.GetOutput())

    actor = _vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetAmbient(0.3)
    actor.GetProperty().SetDiffuse(0.7)

    renderer.AddActor(actor)
    _track(renderer, actor)
    return actor


def clear_annotations(renderer: vtk.vtkRenderer) -> int:
    """Remove all annotation actors added by this module.

    Returns:
        Number of actors removed.
    """
    key = id(renderer)
    actors = _annotation_actors.pop(key, [])
    for actor in actors:
        renderer.RemoveViewProp(actor)
    return len(actors)


# ---------------------------------------------------------------------------
# Internal tracking
# ---------------------------------------------------------------------------


def _track(renderer: vtk.vtkRenderer, actor: object) -> None:
    key = id(renderer)
    if key not in _annotation_actors:
        _annotation_actors[key] = []
    _annotation_actors[key].append(actor)
