"""ScriptCompiler — compile PipelineDefinition into pvpython scripts via Jinja2 templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader

from parapilot.core.registry import get_reader, validate_filter_params

if TYPE_CHECKING:
    from parapilot.pipeline.models import PipelineDefinition

TEMPLATES_DIR = Path(__file__).parent.parent / "pipeline" / "templates"


class ScriptCompiler:
    """Compile a PipelineDefinition into a pvpython script string."""

    def __init__(self) -> None:
        import base64

        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["b64encode"] = lambda s: base64.b64encode(s.encode()).decode()

    def compile(self, pipeline: PipelineDefinition) -> str:
        """Convert a PipelineDefinition to a complete pvpython script."""
        parts: list[str] = []

        # 1. Base: imports + reader
        parts.append(self._compile_base(pipeline))

        # 2. Filter chain
        if pipeline.pipeline:
            parts.append(self._compile_filters(pipeline))

        # 3. Output
        parts.append(self._compile_output(pipeline))

        return "\n".join(parts)

    def compile_inspect(self, source_file: str, reader: str | None = None) -> str:
        """Compile a metadata inspection script (no pipeline, no output spec needed)."""
        if reader is None:
            reader = get_reader(source_file)

        template = self.env.get_template("base.py.j2")
        base = template.render(
            source_file=source_file,
            reader=reader,
            timestep=None,
            blocks=None,
        )

        inspect_template = self.env.get_template("inspect.py.j2")
        inspect_code = inspect_template.render(source_file=source_file)

        return base + "\n" + inspect_code

    def _compile_base(self, pipeline: PipelineDefinition) -> str:
        """Render the base template (imports, reader, timestep selection)."""
        source = pipeline.source
        reader = get_reader(source.file)

        # Resolve file series: explicit list or glob pattern
        source_files: list[str] | None = None
        if source.files:
            source_files = sorted(source.files)
        elif source.file_pattern:
            import glob as _glob

            source_files = sorted(_glob.glob(source.file_pattern))
            if not source_files:
                raise ValueError(
                    f"file_pattern '{source.file_pattern}' matched no files"
                )

        template = self.env.get_template("base.py.j2")
        return template.render(
            source_file=source.file,
            source_files=source_files,
            reader=reader,
            timestep=source.timestep,
            blocks=source.blocks,
            mesh_regions=source.blocks,
        )

    def _compile_filters(self, pipeline: PipelineDefinition) -> str:
        """Render the filter chain template."""
        filter_steps: list[dict[str, Any]] = []

        for step in pipeline.pipeline:
            validated_params = validate_filter_params(step.filter, step.params)
            filter_steps.append({
                "filter": step.filter,
                "params": validated_params,
                "name": step.name,
            })

        template = self.env.get_template("filters.py.j2")
        return template.render(filter_steps=filter_steps)

    def _compile_output(self, pipeline: PipelineDefinition) -> str:
        """Render the appropriate output template."""
        output = pipeline.output

        if output.type == "image":
            return self._compile_render(pipeline)
        elif output.type in ("data", "csv"):
            return self._compile_data(pipeline)
        elif output.type == "animation":
            return self._compile_animation(pipeline)
        elif output.type == "split_animation":
            return self._compile_split_animation(pipeline)
        elif output.type == "export":
            return self._compile_export(pipeline)
        elif output.type == "multi":
            # Multi: render + data
            parts = []
            if output.render:
                parts.append(self._compile_render(pipeline))
            if output.data:
                parts.append(self._compile_data(pipeline))
            return "\n".join(parts)
        else:
            raise ValueError(f"Unknown output type: {output.type}")

    def _compile_render(self, pipeline: PipelineDefinition) -> str:
        """Render the render output template."""
        render = pipeline.output.render
        if render is None:
            raise ValueError("Render output requires 'render' definition")

        template = self.env.get_template("render.py.j2")
        return template.render(
            field=render.field,
            association=render.association,
            colormap=render.colormap,
            representation=render.representation,
            scalar_bar=render.scalar_bar,
            scalar_bar_config=render.scalar_bar_config,
            scalar_range=render.scalar_range,
            log_scale=render.log_scale,
            above_range_color=render.above_range_color,
            below_range_color=render.below_range_color,
            camera_preset=render.camera.preset,
            camera_position=render.camera.position,
            camera_focal_point=render.camera.focal_point,
            camera_view_up=render.camera.view_up,
            zoom=render.camera.zoom,
            orthographic=render.camera.orthographic,
            resolution=list(render.resolution),
            background=list(render.background),
            transparent=render.transparent,
            opacity=render.opacity,
            point_size=render.point_size,
            line_width=render.line_width,
            specular=render.specular,
            specular_power=render.specular_power,
            output_filename=render.output_filename,
        )

    def _compile_data(self, pipeline: PipelineDefinition) -> str:
        """Render the data extraction template."""
        data_def = pipeline.output.data
        if data_def is None:
            # Create default data output
            from parapilot.pipeline.models import DataOutputDef
            data_def = DataOutputDef()

        template = self.env.get_template("data.py.j2")
        return template.render(
            fields=data_def.fields,
            format=data_def.format,
            include_coordinates=data_def.include_coordinates,
            statistics_only=data_def.statistics_only,
        )

    def _compile_animation(self, pipeline: PipelineDefinition) -> str:
        """Render the animation output template."""
        anim = pipeline.output.animation
        if anim is None:
            raise ValueError("Animation output requires 'animation' definition")

        # Resolve source_files for per-file loading (Mesa-safe fallback)
        source = pipeline.source
        source_files: list[str] | None = None
        if source.files:
            source_files = sorted(source.files)
        elif source.file_pattern:
            import glob as _glob

            source_files = sorted(_glob.glob(source.file_pattern))

        reader_type = get_reader(source.file)

        template = self.env.get_template("animate.py.j2")
        return template.render(
            field=anim.render.field,
            association=anim.render.association,
            colormap=anim.render.colormap,
            representation=anim.render.representation,
            scalar_bar=anim.render.scalar_bar,
            scalar_range=anim.render.scalar_range,
            opacity=anim.render.opacity,
            point_size=anim.render.point_size,
            camera_preset=anim.render.camera.preset,
            resolution=list(anim.render.resolution),
            background=list(anim.render.background),
            fps=anim.fps,
            time_range=anim.time_range,
            speed_factor=anim.speed_factor,
            mode=anim.mode,
            orbit_duration=anim.orbit_duration,
            source_files=source_files,
            reader_type=reader_type,
        )

    def _compile_split_animation(self, pipeline: PipelineDefinition) -> str:
        """Render the split animation template (multi-view + stats)."""
        split_anim = pipeline.output.split_animation
        if split_anim is None:
            raise ValueError("Split animation output requires 'split_animation' definition")

        layout = split_anim.layout
        gap = layout.gap
        total_w, total_h = split_anim.resolution
        cell_w = (total_w - gap * (layout.cols - 1)) // layout.cols
        cell_h = (total_h - gap * (layout.rows - 1)) // layout.rows

        # Build render pane data for template
        render_panes: list[dict[str, Any]] = []
        stat_fields: set[str] = set()

        for i, pane in enumerate(split_anim.panes):
            if pane.type == "render" and pane.render_pane is not None:
                r = pane.render_pane.render
                # Compile per-pane filter steps
                filter_steps: list[dict[str, Any]] = []
                for step in pane.render_pane.pipeline:
                    validated_params = validate_filter_params(step.filter, step.params)
                    filter_steps.append({
                        "filter": step.filter,
                        "assignments": self._filter_assignments(step.filter, validated_params),
                    })

                render_panes.append({
                    "index": i,
                    "width": cell_w,
                    "height": cell_h,
                    "field": r.field,
                    "association": r.association,
                    "colormap": r.colormap,
                    "representation": r.representation,
                    "scalar_bar": r.scalar_bar,
                    "scalar_range": r.scalar_range,
                    "opacity": r.opacity,
                    "point_size": r.point_size,
                    "background": list(r.background),
                    "camera_preset": r.camera.preset or "isometric",
                    "filter_steps": filter_steps,
                })
            elif pane.type == "graph" and pane.graph_pane is not None:
                for series in pane.graph_pane.series:
                    stat_fields.add(series.field)

        # Resolve source_files for per-file loading (Mesa-safe fallback)
        source = pipeline.source
        source_files: list[str] | None = None
        if source.files:
            source_files = sorted(source.files)
        elif source.file_pattern:
            import glob as _glob

            source_files = sorted(_glob.glob(source.file_pattern))

        reader_type = get_reader(source.file)

        template = self.env.get_template("split_animate.py.j2")
        return template.render(
            render_panes=render_panes,
            stat_fields=sorted(stat_fields),
            fps=split_anim.fps,
            speed_factor=split_anim.speed_factor,
            time_range=split_anim.time_range,
            source_files=source_files,
            reader_type=reader_type,
        )

    @staticmethod
    def _filter_assignments(filter_name: str, params: dict[str, Any]) -> dict[str, str]:
        """Convert filter params to pvpython property assignments for simple filters."""
        assignments: dict[str, str] = {}
        if filter_name == "Slice":
            assignments["SliceType"] = '"Plane"'
            assignments["SliceType.Origin"] = str(params["origin"])
            assignments["SliceType.Normal"] = str(params["normal"])
        elif filter_name == "Clip":
            assignments["ClipType"] = '"Plane"'
            assignments["ClipType.Origin"] = str(params["origin"])
            assignments["ClipType.Normal"] = str(params["normal"])
            assignments["Invert"] = str(int(params.get("invert", False)))
        elif filter_name == "Threshold":
            assoc = params.get("association", "POINTS")
            assignments["Scalars"] = f'["{assoc}", "{params["field"]}"]'
            assignments["LowerThreshold"] = str(params["lower"])
            assignments["UpperThreshold"] = str(params["upper"])
            assignments["ThresholdMethod"] = f'"{params["method"]}"'
        elif filter_name == "Calculator":
            assignments["Function"] = f'"{params["expression"]}"'
            assignments["ResultArrayName"] = f'"{params["result_name"]}"'
        return assignments

    def _compile_export(self, pipeline: PipelineDefinition) -> str:
        """Render the export output template."""
        fmt = pipeline.output.export_format
        if fmt is None:
            raise ValueError("Export output requires 'export_format'")

        template = self.env.get_template("export.py.j2")
        return template.render(export_format=fmt)
