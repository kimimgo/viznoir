"""ScriptCompiler — compile PipelineDefinition into VTK engine scripts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from viznoir.core.registry import validate_filter_params

if TYPE_CHECKING:
    from viznoir.pipeline.models import PipelineDefinition

__all__ = ["ScriptCompiler"]


class ScriptCompiler:
    """Compile a PipelineDefinition into a Python/VTK script string.

    Generated scripts import from ``viznoir.engine`` and write results
    to ``VIZNOIR_OUTPUT_DIR``.  No Jinja2 or ParaView dependency.
    """

    def compile(self, pipeline: PipelineDefinition) -> str:
        """Convert a PipelineDefinition to a Python/VTK script."""
        lines: list[str] = []
        lines.append(self._header())
        lines.append(self._read_source(pipeline))

        if pipeline.pipeline:
            lines.append(self._apply_filters(pipeline))

        lines.append(self._output(pipeline))
        return "\n".join(lines)

    def compile_inspect(self, source_file: str, reader: str | None = None) -> str:
        """Compile a metadata inspection script."""
        _ = reader  # reader auto-detected inside engine
        return _INSPECT_TEMPLATE.format(source_file=_py_str(source_file))

    # ------------------------------------------------------------------
    # Private — code generation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _header() -> str:
        return _HEADER

    def _read_source(self, pipeline: PipelineDefinition) -> str:
        source = pipeline.source

        source_files: list[str] | None = None
        if source.files:
            source_files = sorted(source.files)
        elif source.file_pattern:
            import glob as _glob

            source_files = sorted(_glob.glob(source.file_pattern))
            if not source_files:
                raise ValueError(f"file_pattern '{source.file_pattern}' matched no files")

        parts: list[str] = []

        if source_files:
            parts.append(f"_source_files = {source_files!r}")
            parts.append(f"dataset = read_dataset({_py_str(source.file)}, source_files=_source_files)")
        else:
            ts = _py_repr(source.timestep)
            blocks = _py_repr(source.blocks)
            parts.append(f"dataset = read_dataset({_py_str(source.file)}, timestep={ts}, blocks={blocks})")

        return "\n".join(parts)

    def _apply_filters(self, pipeline: PipelineDefinition) -> str:
        steps: list[str] = []
        for step in pipeline.pipeline:
            params = validate_filter_params(step.filter, step.params)
            params_str = ", ".join(f"{k}={_py_repr(v)}" for k, v in params.items())
            steps.append(f"dataset = apply_filter(dataset, {_py_str(step.filter)}, {params_str})")
        return "\n".join(steps)

    def _output(self, pipeline: PipelineDefinition) -> str:
        output = pipeline.output
        if output.type == "image":
            return self._gen_render(pipeline)
        if output.type in ("data", "csv"):
            return self._gen_data(pipeline)
        if output.type == "animation":
            return self._gen_animation(pipeline)
        if output.type == "split_animation":
            return self._gen_split_animation(pipeline)
        if output.type == "export":
            return self._gen_export(pipeline)
        if output.type == "multi":
            parts: list[str] = []
            if output.render:
                parts.append(self._gen_render(pipeline))
            if output.data:
                parts.append(self._gen_data(pipeline))
            return "\n".join(parts)
        raise ValueError(f"Unknown output type: {output.type}")

    # --- render ---
    def _gen_render(self, pipeline: PipelineDefinition) -> str:
        r = pipeline.output.render
        if r is None:
            raise ValueError("Render output requires 'render' definition")

        cam = r.camera
        return _RENDER_TEMPLATE.format(
            width=r.resolution[0],
            height=r.resolution[1],
            background=tuple(r.background),
            colormap=r.colormap.lower(),
            array_name=_py_repr(r.field),
            component=-1,
            representation=r.representation.lower(),
            opacity=r.opacity,
            show_scalar_bar=r.scalar_bar,
            scalar_bar_title=_py_repr(r.scalar_bar_config.title if r.scalar_bar_config else None),
            edge_visibility="True" if r.representation.lower() == "surface with edges" else "False",
            point_size=r.point_size,
            line_width=r.line_width,
            log_scale=r.log_scale,
            scalar_range=_py_repr(tuple(r.scalar_range) if r.scalar_range else None),
            camera_preset=_py_repr(cam.preset),
            camera_position=_py_repr(cam.position),
            camera_focal_point=_py_repr(cam.focal_point),
            camera_view_up=_py_repr(cam.view_up),
            camera_zoom=cam.zoom,
            camera_orthographic=cam.orthographic,
            output_filename=r.output_filename,
        )

    # --- data ---
    def _gen_data(self, pipeline: PipelineDefinition) -> str:
        from viznoir.pipeline.models import DataOutputDef

        d = pipeline.output.data or DataOutputDef()
        return _DATA_TEMPLATE.format(
            fields=_py_repr(d.fields),
            include_coordinates=d.include_coordinates,
            statistics_only=d.statistics_only,
            fmt=d.format,
        )

    # --- animation ---
    def _gen_animation(self, pipeline: PipelineDefinition) -> str:
        anim = pipeline.output.animation
        if anim is None:
            raise ValueError("Animation output requires 'animation' definition")

        source = pipeline.source
        source_files: list[str] | None = None
        if source.files:
            source_files = sorted(source.files)
        elif source.file_pattern:
            import glob as _glob

            source_files = sorted(_glob.glob(source.file_pattern))

        r = anim.render
        filter_lines = ""
        if pipeline.pipeline:
            filter_lines = self._apply_filters(pipeline)

        return _ANIMATION_TEMPLATE.format(
            source_file=_py_str(source.file),
            source_files=_py_repr(source_files),
            timestep=_py_repr(source.timestep),
            blocks=_py_repr(source.blocks),
            filter_code=filter_lines,
            width=r.resolution[0],
            height=r.resolution[1],
            background=tuple(r.background),
            colormap=r.colormap.lower(),
            array_name=_py_repr(r.field),
            representation=r.representation.lower(),
            opacity=r.opacity,
            show_scalar_bar=r.scalar_bar,
            log_scale=r.log_scale,
            scalar_range=_py_repr(tuple(r.scalar_range) if r.scalar_range else None),
            camera_preset=_py_repr(r.camera.preset),
            camera_zoom=r.camera.zoom,
            camera_orthographic=r.camera.orthographic,
            fps=anim.fps,
            time_range=_py_repr(anim.time_range),
            speed_factor=anim.speed_factor,
            mode=anim.mode,
            orbit_duration=anim.orbit_duration,
        )

    # --- split animation ---
    def _gen_split_animation(self, pipeline: PipelineDefinition) -> str:
        split_anim = pipeline.output.split_animation
        if split_anim is None:
            raise ValueError("Split animation output requires 'split_animation' definition")

        layout = split_anim.layout
        gap = layout.gap
        total_w, total_h = split_anim.resolution
        cell_w = (total_w - gap * (layout.cols - 1)) // layout.cols
        cell_h = (total_h - gap * (layout.rows - 1)) // layout.rows

        render_panes: list[dict[str, Any]] = []
        stat_fields: set[str] = set()

        for i, pane in enumerate(split_anim.panes):
            if pane.type == "render" and pane.render_pane is not None:
                r = pane.render_pane.render
                filter_steps: list[dict[str, Any]] = []
                for step in pane.render_pane.pipeline:
                    vp = validate_filter_params(step.filter, step.params)
                    filter_steps.append({"filter": step.filter, "params": vp})

                render_panes.append(
                    {
                        "index": i,
                        "width": cell_w,
                        "height": cell_h,
                        "field": r.field,
                        "colormap": r.colormap.lower(),
                        "representation": r.representation.lower(),
                        "scalar_bar": r.scalar_bar,
                        "scalar_range": list(r.scalar_range) if r.scalar_range else None,
                        "opacity": r.opacity,
                        "background": list(r.background),
                        "camera_preset": r.camera.preset or "isometric",
                        "filter_steps": filter_steps,
                    }
                )
            elif pane.type == "graph" and pane.graph_pane is not None:
                for series in pane.graph_pane.series:
                    stat_fields.add(series.field)

        source = pipeline.source
        source_files: list[str] | None = None
        if source.files:
            source_files = sorted(source.files)
        elif source.file_pattern:
            import glob as _glob

            source_files = sorted(_glob.glob(source.file_pattern))

        return _SPLIT_ANIM_TEMPLATE.format(
            source_file=_py_str(source.file),
            source_files=_py_repr(source_files),
            blocks=_py_repr(source.blocks),
            render_panes_json=json.dumps(render_panes),
            stat_fields=_py_repr(sorted(stat_fields)),
            fps=split_anim.fps,
            speed_factor=split_anim.speed_factor,
            time_range=_py_repr(split_anim.time_range),
        )

    # --- export ---
    def _gen_export(self, pipeline: PipelineDefinition) -> str:
        fmt = pipeline.output.export_format
        if fmt is None:
            raise ValueError("Export output requires 'export_format'")
        return _EXPORT_TEMPLATE.format(export_format=_py_str(fmt))


# ======================================================================
# Utility functions
# ======================================================================


def _py_str(s: str) -> str:
    """Return a Python string literal."""
    return repr(s)


def _py_repr(v: Any) -> str:
    """Return a Python repr for embedding in generated code."""
    return repr(v)


# ======================================================================
# Script templates (f-string based, no Jinja2)
# ======================================================================

_HEADER = """\
import os, sys, json
OUTPUT_DIR = os.environ.get("VIZNOIR_OUTPUT_DIR", ".")
DATA_DIR = os.environ.get("VIZNOIR_DATA_DIR", ".")
from viznoir.engine.readers import read_dataset, get_timesteps
from viznoir.engine.filters import apply_filter
from viznoir.engine.renderer import VTKRenderer, RenderConfig, render_to_png
from viznoir.engine.camera import preset_camera, custom_camera, CameraConfig
from viznoir.engine.export import inspect_dataset, extract_stats, extract_data, export_file
from viznoir.engine.colormaps import COLORMAP_REGISTRY
"""

_INSPECT_TEMPLATE = """\
import os, sys, json
OUTPUT_DIR = os.environ.get("VIZNOIR_OUTPUT_DIR", ".")
from viznoir.engine.readers import read_dataset, get_timesteps, list_arrays, list_blocks
from viznoir.engine.export import inspect_dataset

dataset = read_dataset({source_file})
info = inspect_dataset(dataset)
info["timesteps"] = get_timesteps({source_file})
info["arrays"] = list_arrays({source_file})
info["blocks"] = list_blocks({source_file})

result_path = os.path.join(OUTPUT_DIR, "result.json")
with open(result_path, "w") as f:
    json.dump(info, f, default=str)
print(json.dumps(info, default=str))
"""

_RENDER_TEMPLATE = """\
# --- Render ---
_cfg = RenderConfig(
    width={width},
    height={height},
    background={background},
    colormap={colormap!r},
    scalar_range={scalar_range},
    log_scale={log_scale},
    array_name={array_name},
    component={component},
    representation={representation!r},
    opacity={opacity},
    show_scalar_bar={show_scalar_bar},
    scalar_bar_title={scalar_bar_title},
    edge_visibility={edge_visibility},
    point_size={point_size},
    line_width={line_width},
)

_camera_position = {camera_position}
_camera_preset = {camera_preset}
if _camera_position is not None:
    _cam = custom_camera(
        position=_camera_position,
        focal_point={camera_focal_point},
        view_up={camera_view_up},
        zoom={camera_zoom},
        orthographic={camera_orthographic},
    )
elif _camera_preset is not None:
    _cam = preset_camera(_camera_preset, dataset.GetBounds(), zoom={camera_zoom}, orthographic={camera_orthographic})
else:
    _cam = None

_png = render_to_png(dataset, _cfg, _cam)
_out = os.path.join(OUTPUT_DIR, {output_filename!r})
with open(_out, "wb") as f:
    f.write(_png)
"""

_DATA_TEMPLATE = """\
# --- Data extraction ---
if {statistics_only}:
    _result = extract_stats(dataset, fields={fields})
else:
    _result = extract_data(dataset, fields={fields}, include_coords={include_coordinates})

if {fmt!r} == "csv":
    _csv_path = os.path.join(OUTPUT_DIR, "data.csv")
    export_file(dataset, _csv_path, file_format=".csv")
    _result["csv_path"] = _csv_path

_rpath = os.path.join(OUTPUT_DIR, "result.json")
with open(_rpath, "w") as f:
    json.dump(_result, f, default=str)
print(json.dumps(_result, default=str))
"""

_ANIMATION_TEMPLATE = """\
# --- Animation ---
_timesteps = get_timesteps({source_file})
_time_range = {time_range}
if _time_range is not None:
    _timesteps = [t for t in _timesteps if _time_range[0] <= t <= _time_range[1]]

if not _timesteps:
    _timesteps = [None]

_mode = {mode!r}
_fps = {fps}
_speed_factor = {speed_factor}
_orbit_duration = {orbit_duration}

if _mode == "orbit":
    _n_frames = int(_orbit_duration * _fps)
    import math
    for _fi in range(_n_frames):
        _angle = 2 * math.pi * _fi / _n_frames
        _bounds = dataset.GetBounds()
        _cx = (_bounds[0] + _bounds[1]) / 2
        _cy = (_bounds[2] + _bounds[3]) / 2
        _cz = (_bounds[4] + _bounds[5]) / 2
        _diag = ((_bounds[1]-_bounds[0])**2 + (_bounds[3]-_bounds[2])**2 + (_bounds[5]-_bounds[4])**2)**0.5
        _r = _diag * 1.5
        _pos = [_cx + _r * math.cos(_angle), _cy + _r * math.sin(_angle), _cz + _diag * 0.5]
        _cam = custom_camera(position=_pos, focal_point=[_cx, _cy, _cz], view_up=[0, 0, 1])

        _cfg = RenderConfig(
            width={width}, height={height}, background={background},
            colormap={colormap!r}, array_name={array_name},
            representation={representation!r}, opacity={opacity},
            show_scalar_bar={show_scalar_bar}, log_scale={log_scale},
            scalar_range={scalar_range},
        )
        _png = render_to_png(dataset, _cfg, _cam)
        _fname = os.path.join(OUTPUT_DIR, f"frame_{{_fi:06d}}.png")
        with open(_fname, "wb") as f:
            f.write(_png)

    _meta = {{"frame_count": _n_frames, "fps": _fps, "mode": "orbit"}}
else:
    _phys_dur = (_timesteps[-1] - _timesteps[0]) if len(_timesteps) > 1 else 1.0
    _anim_dur = max(_phys_dur / _speed_factor, 1.0 / _fps)
    _target_frames = max(int(_anim_dur * _fps), 1)

    import numpy as _np
    _target_times = _np.linspace(_timesteps[0], _timesteps[-1], _target_frames)
    _ts_arr = _np.array(_timesteps)

    _frame_idx = 0
    _source_files = {source_files}
    for _ti, _tt in enumerate(_target_times):
        _nearest_idx = int(_np.argmin(_np.abs(_ts_arr - _tt)))

        if _source_files is not None:
            dataset = read_dataset(_source_files[min(_nearest_idx, len(_source_files)-1)])
        else:
            dataset = read_dataset({source_file}, timestep=_timesteps[_nearest_idx], blocks={blocks})

        {filter_code}

        _cfg = RenderConfig(
            width={width}, height={height}, background={background},
            colormap={colormap!r}, array_name={array_name},
            representation={representation!r}, opacity={opacity},
            show_scalar_bar={show_scalar_bar}, log_scale={log_scale},
            scalar_range={scalar_range},
        )
        _camera_preset = {camera_preset}
        if _camera_preset is not None:
            _cam = preset_camera(
                _camera_preset, dataset.GetBounds(),
                zoom={camera_zoom}, orthographic={camera_orthographic},
            )
        else:
            _cam = None

        _png = render_to_png(dataset, _cfg, _cam)
        _fname = os.path.join(OUTPUT_DIR, f"frame_{{_frame_idx:06d}}.png")
        with open(_fname, "wb") as f:
            f.write(_png)
        _frame_idx += 1

    _effective_fps = _frame_idx / _anim_dur if _anim_dur > 0 else _fps
    _meta = {{"frame_count": _frame_idx, "fps": _fps, "effective_fps": _effective_fps, "mode": "timesteps"}}

_rpath = os.path.join(OUTPUT_DIR, "result.json")
with open(_rpath, "w") as f:
    json.dump(_meta, f)
print(json.dumps(_meta))
"""

_SPLIT_ANIM_TEMPLATE = """\
# --- Split Animation ---
import json as _json

_timesteps = get_timesteps({source_file})
_time_range = {time_range}
if _time_range is not None:
    _timesteps = [t for t in _timesteps if _time_range[0] <= t <= _time_range[1]]
if not _timesteps:
    _timesteps = [None]

_fps = {fps}
_speed_factor = {speed_factor}
_phys_dur = (_timesteps[-1] - _timesteps[0]) if len(_timesteps) > 1 and _timesteps[0] is not None else 1.0
_anim_dur = max(_phys_dur / _speed_factor, 1.0 / _fps)
_target_frames = max(int(_anim_dur * _fps), 1)

import numpy as _np
if _timesteps[0] is not None:
    _target_times = _np.linspace(_timesteps[0], _timesteps[-1], _target_frames)
    _ts_arr = _np.array(_timesteps)
else:
    _target_times = [None]
    _ts_arr = None

_render_panes = _json.loads({render_panes_json!r})
_stat_fields = {stat_fields}
_source_files = {source_files}
_all_stats = {{}}

for _fi, _tt in enumerate(_target_times):
    if _ts_arr is not None:
        _nearest_idx = int(_np.argmin(_np.abs(_ts_arr - _tt)))
        if _source_files is not None:
            _ds = read_dataset(_source_files[min(_nearest_idx, len(_source_files)-1)])
        else:
            _ds = read_dataset({source_file}, timestep=_timesteps[_nearest_idx], blocks={blocks})
    else:
        _ds = read_dataset({source_file}, blocks={blocks})

    if _stat_fields:
        _st = extract_stats(_ds, _stat_fields)
        _t_val = _tt if _tt is not None else _fi
        _all_stats[str(_t_val)] = _st

    for _pane in _render_panes:
        _p_ds = _ds
        for _fs in _pane.get("filter_steps", []):
            _p_ds = apply_filter(_p_ds, _fs["filter"], **_fs["params"])

        _cfg = RenderConfig(
            width=_pane["width"], height=_pane["height"],
            background=tuple(_pane["background"]),
            colormap=_pane["colormap"],
            array_name=_pane["field"],
            representation=_pane["representation"],
            opacity=_pane["opacity"],
            show_scalar_bar=_pane["scalar_bar"],
            scalar_range=tuple(_pane["scalar_range"]) if _pane.get("scalar_range") else None,
        )
        _cam = preset_camera(_pane["camera_preset"], _p_ds.GetBounds())
        _png = render_to_png(_p_ds, _cfg, _cam)
        _fname = os.path.join(OUTPUT_DIR, f"pane{{_pane['index']}}_frame_{{_fi:06d}}.png")
        with open(_fname, "wb") as f:
            f.write(_png)

_stats_path = os.path.join(OUTPUT_DIR, "stats.json")
with open(_stats_path, "w") as f:
    _json.dump(_all_stats, f, default=str)

_effective_fps = len(list(_target_times)) / _anim_dur if _anim_dur > 0 else _fps
_meta = {{"frame_count": len(list(_target_times)), "effective_fps": _effective_fps}}
_rpath = os.path.join(OUTPUT_DIR, "result.json")
with open(_rpath, "w") as f:
    _json.dump(_meta, f)
print(_json.dumps(_meta))
"""

_EXPORT_TEMPLATE = """\
# --- Export ---
_out_path = os.path.join(OUTPUT_DIR, "exported" + {export_format})
_result = export_file(dataset, _out_path, file_format={export_format})
_rpath = os.path.join(OUTPUT_DIR, "result.json")
with open(_rpath, "w") as f:
    json.dump(_result, f, default=str)
print(json.dumps(_result, default=str))
"""
