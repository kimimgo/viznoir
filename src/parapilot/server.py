"""parapilot FastMCP Server — entry point with all tool registrations."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from parapilot.config import PVConfig
from parapilot.core.runner import VTKRunner
from parapilot.logging import get_logger

logger = get_logger("server")

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
        "- cinematic_render: Publication/cinema-quality rendering with auto-framing, "
        "3-point lighting, SSAO, FXAA, PBR materials\n"
        "- compare: Side-by-side or diff comparison of two simulation results\n"
        "- execute_pipeline: Full pipeline DSL for advanced operations\n\n"
        "Resources: parapilot://formats, parapilot://filters, parapilot://colormaps, parapilot://cameras, "
        "parapilot://case-presets, parapilot://pipelines/cfd, parapilot://pipelines/fea, parapilot://pipelines/split-animate"
    ),
)

# Shared instances (created once, reused across requests)
_config = PVConfig()
_runner = VTKRunner(config=_config)


def _validate_file_path(file_path: str) -> str:
    """Validate file_path is within the configured data_dir (path traversal prevention).

    When PARAPILOT_DATA_DIR is not set (local install), any path is allowed.
    When set (Docker), access is restricted to that directory.
    """
    import difflib

    resolved = Path(file_path).resolve()
    if _config.data_dir is not None:
        data_dir = _config.data_dir.resolve()
        if not str(resolved).startswith(str(data_dir) + "/") and resolved != data_dir:
            raise ValueError(
                f"Access denied: '{file_path}' is outside allowed data directory '{data_dir}'"
            )
    if not resolved.exists():
        hint = ""
        parent = resolved.parent
        if parent.is_dir():
            siblings = [f.name for f in parent.iterdir() if f.is_file()]
            close = difflib.get_close_matches(resolved.name, siblings, n=3)
            if close:
                hint = f" Did you mean: {', '.join(close)}?"
        logger.warning("File not found: '%s'.%s", file_path, hint)
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
    logger.debug("tool.inspect_data: start file=%s", file_path)
    t0 = time.monotonic()
    from parapilot.tools.inspect import inspect_data_impl

    result = await inspect_data_impl(file_path, _runner)
    logger.debug("tool.inspect_data: done in %.2fs", time.monotonic() - t0)
    return result


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
    logger.debug("tool.render: start file=%s field=%s", file_path, field_name)
    t0 = time.monotonic()
    from parapilot.tools.render import render_impl

    result = await render_impl(
        file_path, field_name, _runner,
        association=association, colormap=colormap, camera=camera,
        scalar_range=scalar_range, width=width, height=height,
        timestep=timestep, blocks=blocks,
        output_filename=output_filename,
    )
    logger.debug("tool.render: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.slice: start file=%s field=%s", file_path, field_name)
    t0 = time.monotonic()
    from parapilot.tools.filters import slice_impl

    result = await slice_impl(
        file_path, field_name, _runner,
        origin=origin, normal=normal, colormap=colormap,
        camera=camera, width=width, height=height, timestep=timestep,
    )
    logger.debug("tool.slice: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.contour: start file=%s field=%s isovalues=%s", file_path, field_name, isovalues)
    t0 = time.monotonic()
    from parapilot.tools.filters import contour_impl

    result = await contour_impl(
        file_path, field_name, isovalues, _runner,
        colormap=colormap, camera=camera, width=width, height=height,
        timestep=timestep,
    )
    logger.debug("tool.contour: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.clip: start file=%s field=%s", file_path, field_name)
    t0 = time.monotonic()
    from parapilot.tools.filters import clip_impl

    result = await clip_impl(
        file_path, field_name, _runner,
        origin=origin, normal=normal, invert=invert,
        colormap=colormap, camera=camera, width=width, height=height,
        timestep=timestep,
    )
    logger.debug("tool.clip: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.streamlines: start file=%s vector_field=%s", file_path, vector_field)
    t0 = time.monotonic()
    from parapilot.tools.filters import streamlines_impl

    result = await streamlines_impl(
        file_path, vector_field, _runner,
        seed_point1=seed_point1, seed_point2=seed_point2,
        seed_resolution=seed_resolution, max_length=max_length,
        colormap=colormap, camera=camera, width=width, height=height,
        timestep=timestep,
    )
    logger.debug("tool.streamlines: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.plot_over_line: start file=%s field=%s", file_path, field_name)
    t0 = time.monotonic()
    from parapilot.tools.extract import plot_over_line_impl

    result = await plot_over_line_impl(
        file_path, field_name, point1, point2, _runner,
        resolution=resolution, timestep=timestep,
    )
    logger.debug("tool.plot_over_line: done in %.2fs", time.monotonic() - t0)
    return result


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
    logger.debug("tool.extract_stats: start file=%s fields=%s", file_path, fields)
    t0 = time.monotonic()
    from parapilot.tools.extract import extract_stats_impl

    result = await extract_stats_impl(
        file_path, fields, _runner,
        timestep=timestep, blocks=blocks,
    )
    logger.debug("tool.extract_stats: done in %.2fs", time.monotonic() - t0)
    return result


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
    logger.debug("tool.integrate_surface: start file=%s field=%s boundary=%s", file_path, field_name, boundary)
    t0 = time.monotonic()
    from parapilot.tools.extract import integrate_surface_impl

    result = await integrate_surface_impl(
        file_path, field_name, _runner,
        boundary=boundary, timestep=timestep,
    )
    logger.debug("tool.integrate_surface: done in %.2fs", time.monotonic() - t0)
    return result


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
    logger.debug("tool.animate: start file=%s field=%s mode=%s", file_path, field_name, mode)
    t0 = time.monotonic()
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
    logger.debug("tool.animate: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.split_animate: start file=%s panes=%d", file_path, len(panes))
    t0 = time.monotonic()
    from parapilot.tools.split_animate import split_animate_impl

    result = await split_animate_impl(
        file_path, panes, _runner,
        layout=layout, fps=fps, time_range=time_range,
        speed_factor=speed_factor, resolution=resolution, gif=gif,
    )
    logger.debug("tool.split_animate: done in %.2fs", time.monotonic() - t0)
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
    logger.debug("tool.pv_isosurface: start bi4_dir=%s", bi4_dir)
    t0 = time.monotonic()
    from parapilot.tools.isosurface import pv_isosurface_impl

    result = await pv_isosurface_impl(
        bi4_dir, output_dir,
        vars=vars, only_type=only_type,
        docker_image=docker_image,
    )
    logger.debug("tool.pv_isosurface: done in %.2fs", time.monotonic() - t0)
    return result


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
    logger.debug("tool.execute_pipeline: start")
    t0 = time.monotonic()
    from parapilot.tools.pipeline import execute_pipeline_impl

    result = await execute_pipeline_impl(pipeline, _runner)
    logger.debug("tool.execute_pipeline: done in %.2fs type=%s", time.monotonic() - t0, result.output_type)

    if result.output_type == "image" and result.image_bytes:
        return Image(data=result.image_bytes, format="png")

    return result.json_data or {"status": "completed", "type": result.output_type}


# ---------------------------------------------------------------------------
# Layer 1: Cinematic Rendering
# ---------------------------------------------------------------------------


@mcp.tool()
async def cinematic_render(
    file_path: str,
    field_name: str | None = None,
    colormap: str = "Cool to Warm",
    quality: Literal["draft", "standard", "cinematic", "ultra", "publication"] = "standard",
    lighting: str | None = "cinematic",
    background: str | None = "dark_gradient",
    azimuth: float | None = None,
    elevation: float | None = None,
    fill_ratio: float = 0.75,
    metallic: float = 0.0,
    roughness: float = 0.5,
    ground_plane: bool = False,
    ssao: bool = True,
    fxaa: bool = True,
    width: int | None = None,
    height: int | None = None,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    output_filename: str = "cinematic.png",
) -> Image:
    """Cinematic-quality rendering with auto-framing, 3-point lighting, SSAO, and PBR.

    Produces publication/presentation-quality images with:
    - PCA-based auto-camera: analyzes object shape and picks optimal viewing angle
    - 3-point cinematic lighting (key + fill + rim)
    - SSAO (Screen-Space Ambient Occlusion) for contact shadows
    - FXAA anti-aliasing
    - Gradient backgrounds
    - PBR material support (metallic/roughness)

    Quality presets:
    - draft: 960x540, no post-processing (fast preview)
    - standard: 1920x1080, SSAO + FXAA
    - cinematic: 1920x1080, all effects + ground plane
    - ultra: 3840x2160, all effects + ground plane
    - publication: 2400x1800, clean lighting, white background

    Args:
        file_path: Path to simulation file
        field_name: Field to visualize (None for auto-detect)
        colormap: Color map preset (e.g., "Cool to Warm", "Viridis")
        quality: Rendering quality preset
        lighting: Lighting preset (cinematic, dramatic, studio, publication, outdoor, None)
        background: Background preset (dark_gradient, light_gradient, blue_gradient, publication, None)
        azimuth: Camera azimuth in degrees (None for auto from shape analysis)
        elevation: Camera elevation in degrees (None for auto from shape analysis)
        fill_ratio: How much of viewport the object fills (0.0-1.0, default 0.75)
        metallic: PBR metallic factor (0.0-1.0)
        roughness: PBR roughness factor (0.0-1.0)
        ground_plane: Add a semi-transparent ground plane for shadow catching
        ssao: Enable Screen-Space Ambient Occlusion
        fxaa: Enable Fast Approximate Anti-Aliasing
        width: Override image width (None uses quality preset)
        height: Override image height (None uses quality preset)
        scalar_range: [min, max] for color scale, None for auto
        timestep: Specific timestep, "latest", or None for first
        output_filename: Output PNG filename
    """
    file_path = _validate_file_path(file_path)
    logger.debug("tool.cinematic_render: start file=%s quality=%s", file_path, quality)
    t0 = time.monotonic()
    from parapilot.tools.cinematic import cinematic_render_impl

    png_bytes = await cinematic_render_impl(
        file_path, _runner,
        field_name=field_name, colormap=colormap, quality=quality,
        lighting=lighting, background=background,
        azimuth=azimuth, elevation=elevation, fill_ratio=fill_ratio,
        metallic=metallic, roughness=roughness, ground_plane=ground_plane,
        ssao=ssao, fxaa=fxaa, width=width, height=height,
        scalar_range=scalar_range, timestep=timestep,
        output_filename=output_filename,
    )
    logger.debug("tool.cinematic_render: done in %.2fs", time.monotonic() - t0)
    if png_bytes:
        return Image(data=png_bytes, format="png")
    raise RuntimeError("Cinematic rendering failed: no image produced")


@mcp.tool()
async def compare(
    file_a: str,
    file_b: str,
    field_name: str | None = None,
    mode: Literal["side_by_side", "diff"] = "side_by_side",
    colormap: str = "Cool to Warm",
    quality: Literal["draft", "standard", "cinematic"] = "standard",
    width: int = 1920,
    height: int = 1080,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    label_a: str = "A",
    label_b: str = "B",
    output_filename: str = "compare.png",
) -> Image:
    """Compare two simulation results side-by-side or as a difference map.

    Renders both datasets with identical camera, colormap, and scalar range for
    direct visual comparison. Essential for design comparison, mesh convergence
    studies, and solver validation.

    Modes:
    - side_by_side: Two panels with shared colorbar and consistent framing
    - diff: Absolute field difference map (|A - B|) rendered on dataset A's mesh

    Args:
        file_a: Path to first simulation file
        file_b: Path to second simulation file
        field_name: Field to compare (None for auto-detect)
        mode: Comparison mode — "side_by_side" or "diff"
        colormap: Color map preset for both panels
        quality: Rendering quality (draft/standard/cinematic)
        width: Total image width (each panel gets half)
        height: Image height
        scalar_range: Shared [min, max] for consistent coloring (None for auto)
        timestep: Specific timestep, "latest", or None for first
        label_a: Label for first panel (displayed top-left)
        label_b: Label for second panel (displayed top-left)
        output_filename: Output PNG filename
    """
    file_a = _validate_file_path(file_a)
    file_b = _validate_file_path(file_b)
    logger.debug("tool.compare: start a=%s b=%s mode=%s", file_a, file_b, mode)
    t0 = time.monotonic()
    from parapilot.tools.compare import compare_impl

    png_bytes = await compare_impl(
        file_a, file_b, _runner,
        field_name=field_name, mode=mode, colormap=colormap,
        quality=quality, width=width, height=height,
        scalar_range=scalar_range, timestep=timestep,
        label_a=label_a, label_b=label_b,
        output_filename=output_filename,
    )
    logger.debug("tool.compare: done in %.2fs", time.monotonic() - t0)
    if png_bytes:
        return Image(data=png_bytes, format="png")
    raise RuntimeError("Compare failed: no image produced")


# ---------------------------------------------------------------------------
# batch_render — render multiple fields in one call
# ---------------------------------------------------------------------------


@mcp.tool()
async def batch_render(
    file_path: str,
    fields: list[str],
    colormap: str = "Cool to Warm",
    camera: str = "isometric",
    width: int = 1920,
    height: int = 1080,
    timestep: float | str | None = None,
    quality: str = "standard",
) -> dict[str, Any]:
    """Render multiple fields from the same dataset in one call.

    Returns a dict with images list, each containing field name and base64 PNG.
    Useful for comparing pressure, velocity, temperature, etc. side-by-side.
    """
    t0 = time.monotonic()
    logger.info("tool.batch_render: file=%s fields=%s", file_path, fields)
    _validate_file_path(file_path)
    from parapilot.tools.batch import batch_render_impl

    result = await batch_render_impl(
        file_path=file_path,
        fields=fields,
        runner=_runner,
        colormap=colormap,
        camera=camera,
        width=width,
        height=height,
        timestep=timestep,
        quality=quality,
    )
    logger.debug("tool.batch_render: done in %.2fs, %d images", time.monotonic() - t0, result["count"])
    return result


# ---------------------------------------------------------------------------
# preview_3d — interactive 3D viewer export
# ---------------------------------------------------------------------------


@mcp.tool()
async def preview_3d(
    file_path: str,
    field_name: str | None = None,
    timestep: float | str | None = None,
    output_filename: str = "preview.glb",
) -> dict[str, Any]:
    """Export dataset to glTF/glB for interactive 3D viewing in a browser.

    Returns the exported file path and a viewer URL hint.
    Requires VTK >= 9.4 with vtkGLTFExporter support.
    """
    t0 = time.monotonic()
    logger.info("tool.preview_3d: file=%s", file_path)
    _validate_file_path(file_path)
    from parapilot.tools.preview3d import preview_3d_impl

    result = await preview_3d_impl(
        file_path=file_path,
        runner=_runner,
        field_name=field_name,
        timestep=timestep,
        output_filename=output_filename,
    )
    logger.debug("tool.preview_3d: done in %.2fs", time.monotonic() - t0)
    return result


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
    """Run the MCP server.

    Supports ``--transport`` CLI argument:
        stdio (default) — standard I/O for local MCP clients
        sse — Server-Sent Events over HTTP (remote access)
        streamable-http — StreamableHTTP transport (FastMCP 2.0+)
    """
    import argparse
    import asyncio

    from parapilot.core.runner import VTKRunner

    parser = argparse.ArgumentParser(description="parapilot MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP transports (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for HTTP transports (default: 8000)"
    )
    args = parser.parse_args()

    # Protect MCP JSON-RPC stream from VTK binary stdout pollution
    if args.transport == "stdio":
        _protect_stdout()

    # Clean up any orphaned parapilot_* Docker containers from previous crashes
    try:
        loop = asyncio.new_event_loop()
        removed = loop.run_until_complete(
            VTKRunner.cleanup_orphaned_containers()
        )
        loop.close()
        if removed:
            logger.info("cleaned up %d orphaned container(s)", removed)
    except RuntimeError:
        # No event loop available yet — skip cleanup
        pass

    _register_resources()
    _register_prompts()

    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
