"""validate_render tool — physics-check a render spec before (or after) rendering.

Runs the guard validator (``viznoir.guard``) against a render's choices
(colormap, scalar range, camera, isosurface) given the *actual* field
statistics of the dataset, returning pass/warn/fail verdicts plus fix
suggestions. This is the anti-hallucination gate exposed over MCP (#59).
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

import numpy as np
from vtk.util.numpy_support import vtk_to_numpy

from viznoir.engine.readers import read_dataset
from viznoir.errors import FieldNotFoundError
from viznoir.guard import GuardContext, validate

_ISO_FILTERS = {"contour", "isosurface", "iso"}


def _field_stats(dataset: Any, field_name: str) -> tuple[float, float, bool, str]:
    """Return (min, max, is_magnitude, association) for ``field_name``.

    Vector fields are reduced to their magnitude. Raises FieldNotFoundError if
    the field is absent from both point and cell data.
    """
    arr = dataset.GetPointData().GetArray(field_name)
    association = "POINTS"
    if arr is None:
        arr = dataset.GetCellData().GetArray(field_name)
        association = "CELLS"
    if arr is None:
        raise FieldNotFoundError(f"field '{field_name}' not found in point or cell data")

    data = vtk_to_numpy(arr)
    is_magnitude = arr.GetNumberOfComponents() > 1
    scalar = np.linalg.norm(data, axis=1) if is_magnitude else data
    return float(np.min(scalar)), float(np.max(scalar)), is_magnitude, association


def build_guard_context(
    dataset: Any,
    field_name: str,
    *,
    colormap: str | None = None,
    scalar_range: list[float] | None = None,
    filter_type: str | None = None,
    isovalue: float | None = None,
    camera_position: list[float] | None = None,
) -> GuardContext:
    """Assemble a GuardContext from a dataset's field statistics + render choices.

    For isosurface filters the cell count is estimated statically: an isovalue
    outside the data range yields an empty surface (the most common mistake).
    """
    fmin, fmax, is_magnitude, _assoc = _field_stats(dataset, field_name)

    iso_count: int | None = None
    if filter_type is not None and filter_type.lower() in _ISO_FILTERS and isovalue is not None:
        # outside the data range -> the contour is empty; inside -> non-empty.
        iso_count = 0 if (isovalue < fmin or isovalue > fmax) else 1

    return GuardContext(
        field_name=field_name,
        field_min=fmin,
        field_max=fmax,
        is_magnitude=is_magnitude,
        colormap=colormap,
        scalar_range=(scalar_range[0], scalar_range[1]) if scalar_range else None,
        camera_position=tuple(camera_position) if camera_position else None,  # type: ignore[arg-type]
        data_bounds=tuple(dataset.GetBounds()),  # type: ignore[arg-type]
        filter_type=filter_type,
        isosurface_cell_count=iso_count,
    )


async def validate_render_impl(
    file_path: str,
    field_name: str,
    *,
    association: Literal["POINTS", "CELLS"] = "POINTS",
    colormap: str = "Cool to Warm",
    scalar_range: list[float] | None = None,
    filter_type: str | None = None,
    isovalue: float | None = None,
    camera_position: list[float] | None = None,
) -> dict[str, Any]:
    """Validate a render spec against the dataset's physics. Returns a verdict report."""

    def _run() -> dict[str, Any]:
        dataset = read_dataset(file_path)
        fmin, fmax, is_magnitude, assoc = _field_stats(dataset, field_name)
        ctx = build_guard_context(
            dataset,
            field_name,
            colormap=colormap,
            scalar_range=scalar_range,
            filter_type=filter_type,
            isovalue=isovalue,
            camera_position=camera_position,
        )
        report = validate(ctx)
        warnings = [r for r in report.results if r.status.value in ("warn", "fail")]
        return {
            "verdict": report.verdict.value,
            "results": [r.to_dict() for r in report.results],
            "field": {
                "name": field_name,
                "min": fmin,
                "max": fmax,
                "is_magnitude": is_magnitude,
                "association": assoc,
            },
            "summary": (
                f"{report.verdict.value.upper()}: "
                + (
                    "; ".join(f"{w.rule} ({w.status.value})" for w in warnings)
                    if warnings
                    else "render choices are physically consistent"
                )
            ),
        }

    return await asyncio.get_event_loop().run_in_executor(None, _run)
