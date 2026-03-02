"""parapilot FastMCP Server — entry point with all tool registrations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from parapilot.config import PVConfig
from parapilot.core.runner import ParaViewRunner

mcp = FastMCP(
    "parapilot",
    instructions=(
        "ParaView MCP Server for AI-powered simulation post-processing. "
        "Supports CFD, FEA, and general CAE visualization "
        "through a pipeline-based architecture.\n\n"
        "Workflow: inspect_data → render/slice/contour → extract_stats/plot_over_line → "
        "animate/split_animate.\n\n"
        "Key tools:\n"
        "- inspect_data: Explore file metadata (fields, timesteps, bounds)\n"
        "- render/slice/contour/clip: Single-view visualization → PNG\n"
        "- streamlines: Flow visualization for vector fields\n"
        "- extract_stats/plot_over_line/integrate_surface: Data extraction\n"
        "- animate: Single-field time series or orbit animation\n"
        "- split_animate: Multi-pane synchronized animation (2-4 panes, "
        "3D render + time-series graphs in a grid layout → GIF)\n"
        "- execute_pipeline: Full pipeline DSL for advanced operations\n\n"
        "Resources: parapilot://formats, parapilot://filters, parapilot://colormaps, parapilot://cameras, "
        "parapilot://case-presets, parapilot://pipelines/cfd, parapilot://pipelines/fea, parapilot://pipelines/split-animate"
    ),
)

# Shared instances (created once, reused across requests)
_config = PVConfig()
_runner = ParaViewRunner(config=_config)


def _validate_file_path(file_path: str) -> str:
    """Validate file_path is within the configured data_dir (path traversal prevention)."""
    resolved = Path(file_path).resolve()
    data_dir = _config.data_dir.resolve()
    if not str(resolved).startswith(str(data_dir) + "/") and resolved != data_dir:
        raise ValueError(
            f"Access denied: '{file_path}' is outside allowed data directory '{data_dir}'"
        )
    return str(resolved)


# ---------------------------------------------------------------------------
# Layer 3: Convenience Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def inspect_data(file_path: str) -> dict[str, Any]:
    """Inspect a simulation file and return metadata.

    Returns bounds, point/cell arrays with ranges, timestep info, and multiblock structure.
    Use this first to understand what data is available before rendering or extracting.

    Args:
        file_path: Path to the simulation file (e.g., /data/cavity.foam, /data/beam.vtu)
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.inspect import inspect_data_impl

    return await inspect_data_impl(file_path, _runner)


@mcp.tool()
async def render(
    file_path: str,
    field_name: str,
    association: Literal["POINTS", "CELLS"] = "POINTS",
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    scalar_range: list[float] | None = None,
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
    blocks: list[str] | None = None,
    output_filename: str = "render.png",
) -> Image:
    """Render a field visualization and return a PNG screenshot.

    Args:
        file_path: Path to simulation file
        field_name: Name of the field to visualize (e.g., "p", "U", "T")
        association: "POINTS" or "CELLS"
        colormap: Color map preset (e.g., "Cool to Warm", "Viridis", "Jet")
        camera: Camera preset — isometric, top, front, right, left, back
        scalar_range: [min, max] for color scale, None for auto
        width: Image width in pixels
        height: Image height in pixels
        timestep: Specific timestep, "latest", or None for first
        blocks: Multiblock region names to include
        output_filename: Output PNG filename (e.g., "snapshot_press.png")
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.render import render_impl

    result = await render_impl(
        file_path, field_name, _runner,
        association=association, colormap=colormap, camera=camera,
        scalar_range=scalar_range, width=width, height=height,
        timestep=timestep, blocks=blocks,
        output_filename=output_filename,
    )
    if result.image_bytes:
        return Image(data=result.image_bytes, format="png")
    raise RuntimeError("Rendering failed: no image produced")


@mcp.tool()
async def slice(
    file_path: str,
    field_name: str,
    origin: list[float] | None = None,
    normal: list[float] | None = None,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
) -> Image:
    """Create a slice (cut plane) visualization.

    Args:
        file_path: Path to simulation file
        field_name: Field to visualize on the slice
        origin: Slice plane origin [x, y, z]
        normal: Slice plane normal [nx, ny, nz]
        colormap: Color map preset
        camera: Camera preset
        width: Image width
        height: Image height
        timestep: Timestep selection
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.filters import slice_impl

    result = await slice_impl(
        file_path, field_name, _runner,
        origin=origin, normal=normal, colormap=colormap,
        camera=camera, width=width, height=height, timestep=timestep,
    )
    if result.image_bytes:
        return Image(data=result.image_bytes, format="png")
    raise RuntimeError("Slice rendering failed: no image produced")


@mcp.tool()
async def contour(
    file_path: str,
    field_name: str,
    isovalues: list[float],
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
) -> Image:
    """Create an iso-surface (contour) visualization.

    Args:
        file_path: Path to simulation file
        field_name: Field for iso-surface extraction
        isovalues: List of iso-values to extract
        colormap: Color map preset
        camera: Camera preset
        width: Image width
        height: Image height
        timestep: Timestep selection
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.filters import contour_impl

    result = await contour_impl(
        file_path, field_name, isovalues, _runner,
        colormap=colormap, camera=camera, width=width, height=height,
        timestep=timestep,
    )
    if result.image_bytes:
        return Image(data=result.image_bytes, format="png")
    raise RuntimeError("Contour rendering failed: no image produced")


@mcp.tool()
async def clip(
    file_path: str,
    field_name: str,
    origin: list[float] | None = None,
    normal: list[float] | None = None,
    invert: bool = False,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
) -> Image:
    """Create a clipped visualization.

    Args:
        file_path: Path to simulation file
        field_name: Field to visualize
        origin: Clip plane origin [x, y, z]
        normal: Clip plane normal [nx, ny, nz]
        invert: If True, keep the other side
        colormap: Color map preset
        camera: Camera preset
        width: Image width
        height: Image height
        timestep: Timestep selection
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.filters import clip_impl

    result = await clip_impl(
        file_path, field_name, _runner,
        origin=origin, normal=normal, invert=invert,
        colormap=colormap, camera=camera, width=width, height=height,
        timestep=timestep,
    )
    if result.image_bytes:
        return Image(data=result.image_bytes, format="png")
    raise RuntimeError("Clip rendering failed: no image produced")


@mcp.tool()
async def streamlines(
    file_path: str,
    vector_field: str,
    seed_point1: list[float] | None = None,
    seed_point2: list[float] | None = None,
    seed_resolution: int = 20,
    max_length: float = 1.0,
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
) -> Image:
    """Create a streamline visualization for vector fields.

    Args:
        file_path: Path to simulation file
        vector_field: Name of the vector field (e.g., "U")
        seed_point1: Start of seed line [x, y, z]
        seed_point2: End of seed line [x, y, z]
        seed_resolution: Number of seed points
        max_length: Maximum streamline length
        colormap: Color map preset
        camera: Camera preset
        width: Image width
        height: Image height
        timestep: Timestep selection
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.filters import streamlines_impl

    result = await streamlines_impl(
        file_path, vector_field, _runner,
        seed_point1=seed_point1, seed_point2=seed_point2,
        seed_resolution=seed_resolution, max_length=max_length,
        colormap=colormap, camera=camera, width=width, height=height,
        timestep=timestep,
    )
    if result.image_bytes:
        return Image(data=result.image_bytes, format="png")
    raise RuntimeError("Streamline rendering failed: no image produced")


@mcp.tool()
async def plot_over_line(
    file_path: str,
    field_name: str,
    point1: list[float],
    point2: list[float],
    resolution: int = 100,
    timestep: float | str | None = None,
) -> dict[str, Any]:
    """Sample field values along a line between two points.

    Returns coordinate arrays and field values for plotting.

    Args:
        file_path: Path to simulation file
        field_name: Field to sample
        point1: Start point [x, y, z]
        point2: End point [x, y, z]
        resolution: Number of sample points
        timestep: Timestep selection
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.extract import plot_over_line_impl

    return await plot_over_line_impl(
        file_path, field_name, point1, point2, _runner,
        resolution=resolution, timestep=timestep,
    )


@mcp.tool()
async def extract_stats(
    file_path: str,
    fields: list[str],
    timestep: float | str | None = None,
    blocks: list[str] | None = None,
) -> dict[str, Any]:
    """Extract statistical summary (min/max/mean/std) for fields.

    Args:
        file_path: Path to simulation file
        fields: List of field names to analyze
        timestep: Timestep selection
        blocks: Multiblock region names
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.extract import extract_stats_impl

    return await extract_stats_impl(
        file_path, fields, _runner,
        timestep=timestep, blocks=blocks,
    )


@mcp.tool()
async def integrate_surface(
    file_path: str,
    field_name: str,
    boundary: str | None = None,
    timestep: float | str | None = None,
) -> dict[str, Any]:
    """Integrate a field over a surface to compute forces, areas, or fluxes.

    Args:
        file_path: Path to simulation file
        field_name: Field to integrate (e.g., "p", "wallShearStress")
        boundary: Boundary/block name to extract (e.g., "wall", "inlet")
        timestep: Timestep selection
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.extract import integrate_surface_impl

    return await integrate_surface_impl(
        file_path, field_name, _runner,
        boundary=boundary, timestep=timestep,
    )


@mcp.tool()
async def animate(
    file_path: str,
    field_name: str,
    mode: Literal["timesteps", "orbit"] = "timesteps",
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    fps: int = 24,
    time_range: list[float] | None = None,
    speed_factor: float = 1.0,
    orbit_duration: float = 10.0,
    width: int = 1920,
    height: int = 1080,
    files: list[str] | None = None,
    file_pattern: str | None = None,
    output_format: Literal["frames", "mp4", "webm", "gif"] = "frames",
    video_quality: int = 23,
    text_overlay: str | None = None,
) -> dict[str, Any]:
    """Create an animation from time series data or camera orbit.

    Time mapping (timesteps mode):
        speed_factor=1.0: real-time (physics 1s = video 1s)
        speed_factor=5.0: 5x fast-forward
        speed_factor=0.2: 5x slow-motion (physics 1s = video 5s)

    For VTK file series (e.g., PartFluid_0000.vtk through PartFluid_0100.vtk),
    use 'files' with an explicit list or 'file_pattern' with a glob pattern.

    Args:
        file_path: Path to simulation file (or first file in series)
        field_name: Field to visualize
        mode: "timesteps" for time series, "orbit" for camera rotation
        colormap: Color map preset
        camera: Camera preset (used for initial view in orbit mode)
        fps: Frames per second (15-60)
        time_range: [start, end] physics time range, None for all
        speed_factor: Playback speed multiplier (1.0=real-time)
        orbit_duration: Orbit video length in seconds (orbit mode only)
        width: Frame width
        height: Frame height
        files: Explicit list of file paths for VTK time series
        file_pattern: Glob pattern for file series (e.g., "/data/PartFluid_*.vtk")
        output_format: Output format — "frames" (PNG only), "mp4", "webm", or "gif"
        video_quality: Video CRF quality (lower=better, 18-28 typical, default 23)
        text_overlay: Text to overlay on video frames (e.g., case name)
    """
    file_path = _validate_file_path(file_path)
    if files:
        files = [_validate_file_path(f) for f in files]
    from parapilot.tools.animate import animate_impl

    result = await animate_impl(
        file_path, field_name, _runner,
        mode=mode, colormap=colormap, camera=camera,
        fps=fps, time_range=time_range, speed_factor=speed_factor,
        orbit_duration=orbit_duration, width=width, height=height,
        files=files, file_pattern=file_pattern,
        output_format=output_format, video_quality=video_quality,
        text_overlay=text_overlay,
    )
    return result.json_data or {"error": "Animation failed"}


@mcp.tool()
async def split_animate(
    file_path: str,
    panes: list[dict[str, Any]],
    layout: dict[str, Any] | None = None,
    fps: int = 24,
    time_range: list[float] | None = None,
    speed_factor: float = 1.0,
    resolution: list[int] | None = None,
    gif: bool = True,
) -> dict[str, Any] | Image:
    """Create a split-pane synchronized animation with multiple views.

    Render 2-4 panes in a grid layout, combining 3D visualizations with
    time-series graphs. All panes are timestep-synchronized and output
    as a single GIF or PNG sequence.

    Pane types:
        - "render": 3D visualization with field coloring, camera, and filters
        - "graph": Time-series plot (requires optional 'composite' dependencies)

    Example panes:
        [
            {"type": "render", "row": 0, "col": 0,
             "render_pane": {"render": {"field": "alpha.water"}, "title": "Water"}},
            {"type": "render", "row": 0, "col": 1,
             "render_pane": {"render": {"field": "p_rgh", "colormap": "Viridis"}}},
            {"type": "graph", "row": 1, "col": 0,
             "graph_pane": {"series": [{"field": "alpha.water", "stat": "mean"}],
                           "title": "Water Fraction"}}
        ]

    Args:
        file_path: Path to simulation file (PVD, foam, etc.)
        panes: List of pane definitions (render or graph)
        layout: Grid layout {"rows": 2, "cols": 2, "gap": 4}
        fps: Frames per second (15-60)
        time_range: [start, end] physics time range
        speed_factor: Playback speed (1.0=real-time, 5.0=5x fast-forward)
        resolution: Total output [width, height] in pixels
        gif: Generate animated GIF (True) or PNG sequence only (False)
    """
    file_path = _validate_file_path(file_path)
    from parapilot.tools.split_animate import split_animate_impl

    result = await split_animate_impl(
        file_path, panes, _runner,
        layout=layout, fps=fps, time_range=time_range,
        speed_factor=speed_factor, resolution=resolution, gif=gif,
    )
    if gif and result.image_bytes:
        return Image(data=result.image_bytes, format="gif")
    return result.json_data or {"error": "Split animation failed"}


@mcp.tool()
async def pv_isosurface(
    bi4_dir: str,
    output_dir: str,
    vars: str = "+vel,+press,+rhop",
    only_type: str = "+fluid",
    docker_image: str = "dsph-agent:latest",
) -> dict[str, Any]:
    """Run DualSPHysics IsoSurface to generate VTK surface mesh files.

    Converts bi4 particle data into VTK surface meshes (iso-surfaces).
    The output files can then be used with animate() or render() via
    SourceDef(files=[...]) for visualization.

    Args:
        bi4_dir: Directory containing bi4 data files
        output_dir: Directory for output VTK surface mesh files
        vars: Variable selection (e.g., "+vel,+press,+rhop")
        only_type: Particle type filter (e.g., "+fluid")
        docker_image: Docker image with IsoSurface tool
    """
    from parapilot.tools.isosurface import pv_isosurface_impl

    return await pv_isosurface_impl(
        bi4_dir, output_dir,
        vars=vars, only_type=only_type,
        docker_image=docker_image,
    )


# ---------------------------------------------------------------------------
# Layer 2: Direct Pipeline Access
# ---------------------------------------------------------------------------


@mcp.tool()
async def execute_pipeline(
    pipeline: dict[str, Any],
) -> dict[str, Any] | Image:
    """Execute a custom pipeline definition (advanced).

    Accepts a full PipelineDefinition JSON for maximum flexibility.
    This is the primary interface for CFD/FEA/CAE specialist agents.

    The pipeline JSON structure:
    {
        "source": {"file": "/data/file.foam", "timestep": "latest"},
        "pipeline": [
            {"filter": "Slice", "params": {"origin": [0,0,0], "normal": [1,0,0]}},
            {"filter": "Calculator", "params": {"expression": "mag(U)", "result_name": "Umag"}}
        ],
        "output": {
            "type": "image",
            "render": {"field": "Umag", "colormap": "Viridis"}
        }
    }

    Available filters: Slice, Clip, Contour, Threshold, StreamTracer, Calculator,
    Gradient, IntegrateVariables, GenerateSurfaceNormals, ExtractBlock, ExtractSurface,
    WarpByVector, WarpByScalar, CellDatatoPointData, PlotOverLine, Glyph,
    ProgrammableFilter, Decimate, Triangulate.

    Output types: image, data, csv, animation, export, multi.

    Args:
        pipeline: Complete PipelineDefinition as JSON dict
    """
    if "source" in pipeline and "file" in pipeline["source"]:
        pipeline["source"]["file"] = _validate_file_path(pipeline["source"]["file"])
    from parapilot.tools.pipeline import execute_pipeline_impl

    result = await execute_pipeline_impl(pipeline, _runner)

    if result.output_type == "image" and result.image_bytes:
        return Image(data=result.image_bytes, format="png")

    return result.json_data or {"status": "completed", "type": result.output_type}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def _register_resources() -> None:
    """Register MCP resources (called at import time)."""
    from parapilot.resources.catalog import register_resources

    register_resources(mcp)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def _register_prompts() -> None:
    """Register MCP prompts (called at import time)."""
    from parapilot.prompts.guides import register_prompts

    register_prompts(mcp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _protect_stdout() -> None:
    """Protect MCP stdio from VTK/ParaView binary pollution.

    ParaView/VTK C code may write ~20MB of binary garbage ("String token
    collision") directly to fd 1 (stdout) during module initialization.
    Since MCP uses stdin/stdout for JSON-RPC, this corrupts the stream.

    Strategy:
        1. Save the real stdout fd via os.dup(1)
        2. Redirect fd 1 → /dev/null (VTK C writes go here)
        3. Replace sys.stdout with a clean wrapper on the saved fd
           (FastMCP writes JSON-RPC via sys.stdout.buffer)
    """
    import io
    import os
    import sys

    sys.stdout.flush()

    saved_fd = os.dup(1)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 1)
    os.close(devnull_fd)

    raw = io.FileIO(saved_fd, "w", closefd=True)
    buffered = io.BufferedWriter(raw)
    sys.stdout = io.TextIOWrapper(buffered, encoding="utf-8", line_buffering=True)


def main() -> None:
    """Run the MCP server."""
    import asyncio
    import sys

    from parapilot.core.runner import ParaViewRunner

    # Protect MCP JSON-RPC stream from VTK binary stdout pollution
    _protect_stdout()

    # Clean up any orphaned parapilot_* Docker containers from previous crashes
    try:
        removed = asyncio.get_event_loop().run_until_complete(
            ParaViewRunner.cleanup_orphaned_containers()
        )
        if removed:
            print(f"parapilot: cleaned up {removed} orphaned container(s)", file=sys.stderr)
    except RuntimeError:
        # No event loop available yet — skip cleanup
        pass

    _register_resources()
    _register_prompts()
    mcp.run()


if __name__ == "__main__":
    main()
