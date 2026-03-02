"""Pydantic models for the Pipeline DSL."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceDef(BaseModel):
    """Data source definition.

    Supports three modes:
        - file: Single file path (existing behavior)
        - files: Explicit list of files (e.g., VTK time series)
        - file_pattern: Glob pattern (e.g., "PartFluid_*.vtk")

    When files or file_pattern is provided, a multi-file reader is used
    (e.g., LegacyVTKReader with FileNames=[...]).
    """

    file: str  # Single file or first file for format detection
    files: list[str] | None = None  # Explicit file list (VTK series)
    file_pattern: str | None = None  # Glob pattern (expanded at compile time)
    timestep: float | str | None = None  # None=first, "latest", or float
    blocks: list[str] | None = None  # Multiblock selection


class FilterStep(BaseModel):
    """Single filter in the pipeline chain."""

    filter: str  # FilterRegistry key
    params: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None  # Optional reference name


class CameraDef(BaseModel):
    """Camera configuration."""

    preset: str | None = "isometric"  # isometric/top/front/right/left/back
    position: list[float] | None = None
    focal_point: list[float] | None = None
    view_up: list[float] | None = None
    zoom: float = 1.5  # Default auto-zoom to fill viewport (Dolly factor)
    orthographic: bool = False  # True=parallel projection, False=perspective


class ScalarBarDef(BaseModel):
    """Scalar bar (color legend) configuration."""

    title: str | None = None  # Override auto-detected title
    component_title: str | None = None  # Unit label, e.g. "[K]", "[m/s]"
    orientation: Literal["Vertical", "Horizontal"] = "Vertical"
    position: list[float] | None = None  # [x, y] normalized (0-1)
    length: float = 0.33
    thickness: int = 20
    label_format: str | None = None  # e.g. "%-#6.1e", "%.1f"
    title_font_size: int = 24
    label_font_size: int = 18


class RenderDef(BaseModel):
    """Rendering configuration."""

    field: str
    association: Literal["POINTS", "CELLS"] = "POINTS"
    colormap: str = "Cool to Warm"
    representation: str = "Surface"  # Surface, Wireframe, Point Gaussian
    scalar_bar: bool = True
    scalar_bar_config: ScalarBarDef | None = None  # Detailed scalar bar settings
    scalar_range: list[float] | None = None  # [min, max], None=auto
    log_scale: bool = False  # Log-scale colormap
    above_range_color: list[float] | None = None  # [R,G,B] for values above scalar_range
    below_range_color: list[float] | None = None  # [R,G,B] for values below scalar_range
    camera: CameraDef = Field(default_factory=CameraDef)
    resolution: list[int] = Field(default=[1920, 1080])
    background: list[float] = Field(default=[1.0, 1.0, 1.0])
    transparent: bool = False
    opacity: float = 1.0
    point_size: float = 1.0  # Scale factor for Point Gaussian (1.0 = auto-estimated particle spacing)
    line_width: float = 1.0  # For Wireframe representation
    specular: float = 0.0  # Specular highlight intensity (0-1)
    specular_power: float = 100.0  # Specular tightness (higher=tighter)
    output_filename: str = "render.png"  # Output filename (e.g., "snapshot_press.png")


class DataOutputDef(BaseModel):
    """Data extraction configuration."""

    fields: list[str] | None = None  # None = all fields
    format: Literal["json", "csv"] = "json"
    include_coordinates: bool = False
    statistics_only: bool = False  # True = min/max/mean/std only


class GraphSeriesDef(BaseModel):
    """Single data series in a graph pane."""

    field: str
    stat: Literal["min", "max", "mean"] = "max"
    label: str | None = None
    color: str | None = None


class GraphPaneDef(BaseModel):
    """Graph pane configuration (time-series plot)."""

    series: list[GraphSeriesDef]
    title: str | None = None
    y_label: str | None = None
    y_range: list[float] | None = None


class RenderPaneDef(BaseModel):
    """3D render pane configuration."""

    render: RenderDef
    title: str | None = None
    pipeline: list[FilterStep] = Field(default_factory=list)


class PaneDef(BaseModel):
    """Single pane in a split-pane layout."""

    type: Literal["render", "graph"]
    row: int = 0
    col: int = 0
    render_pane: RenderPaneDef | None = None
    graph_pane: GraphPaneDef | None = None


class LayoutDef(BaseModel):
    """Grid layout configuration for split-pane animations."""

    rows: int = 1
    cols: int = 2
    gap: int = 4


class SplitAnimationDef(BaseModel):
    """Split-pane synchronized animation configuration."""

    panes: list[PaneDef]
    layout: LayoutDef = Field(default_factory=LayoutDef)
    fps: int = 24
    time_range: list[float] | None = None
    speed_factor: float = 1.0
    resolution: list[int] = Field(default=[1920, 1080])
    gif: bool = True
    gif_loop: int = 0


class AnimationDef(BaseModel):
    """Animation configuration.

    Time mapping (timesteps mode):
        physics_duration = time_range span (or all timesteps)
        animation_duration = physics_duration / speed_factor
        total_frames = animation_duration * fps
        → timesteps are sampled to match target frame count

    speed_factor examples:
        1.0 = real-time (physics 1s → video 1s)
        5.0 = 5x fast-forward
        0.2 = 5x slow-motion
    """

    render: RenderDef
    fps: int = 24
    time_range: list[float] | None = None  # [start, end], None=all
    speed_factor: float = 1.0  # physics_time / video_time ratio
    mode: Literal["timesteps", "orbit"] = "timesteps"
    orbit_axis: list[float] = Field(default=[0, 0, 1])
    orbit_duration: float = 10.0  # orbit video length in seconds
    output_format: Literal["frames", "mp4", "webm", "gif"] = "frames"
    video_quality: int = 23  # CRF value (lower=better, 18-28 typical)
    text_overlay: str | None = None  # ffmpeg drawtext overlay


class OutputDef(BaseModel):
    """Output specification."""

    type: Literal["image", "data", "csv", "animation", "export", "multi", "split_animation"]
    render: RenderDef | None = None
    data: DataOutputDef | None = None
    animation: AnimationDef | None = None
    split_animation: SplitAnimationDef | None = None
    export_format: str | None = None  # vtk, stl, ply, csv


class PipelineDefinition(BaseModel):
    """Complete pipeline definition — the core DSL for Layer 2."""

    source: SourceDef
    pipeline: list[FilterStep] = Field(default_factory=list)
    output: OutputDef
