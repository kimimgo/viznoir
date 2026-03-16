"""Orchestrator — auto_postprocess meta-tool and tool dispatch."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from viznoir.tools.batch import batch_render_impl
from viznoir.tools.cinematic import cinematic_render_impl
from viznoir.tools.compare import compare_impl
from viznoir.tools.filters import clip_impl, contour_impl, slice_impl, streamlines_impl
from viznoir.tools.render import render_impl
from viznoir.tools.volume import volume_render_impl

# Map tool names → impl functions.
# Only image-producing tools are included (orchestrator generates visualizations).
TOOL_DISPATCH: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {
    "render": render_impl,
    "cinematic_render": cinematic_render_impl,
    "slice": slice_impl,
    "contour": contour_impl,
    "clip": clip_impl,
    "streamlines": streamlines_impl,
    "compare": compare_impl,
    "batch_render": batch_render_impl,
    "volume_render": volume_render_impl,
}
