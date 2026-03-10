"""Tests for ScriptCompiler — Pipeline JSON → VTK engine script verification."""

from __future__ import annotations

import pytest

from viznoir.core.compiler import ScriptCompiler
from viznoir.pipeline.models import (
    AnimationDef,
    CameraDef,
    DataOutputDef,
    FilterStep,
    GraphPaneDef,
    GraphSeriesDef,
    LayoutDef,
    OutputDef,
    PaneDef,
    PipelineDefinition,
    RenderDef,
    RenderPaneDef,
    ScalarBarDef,
    SourceDef,
    SplitAnimationDef,
)


@pytest.fixture
def compiler():
    return ScriptCompiler()


# ── Helper ───────────────────────────────────────────────────────────
def _compile_render(compiler, file="/data/case.vtk", field="p", **render_kw):
    pipeline = PipelineDefinition(
        source=SourceDef(file=file),
        pipeline=[],
        output=OutputDef(type="image", render=RenderDef(field=field, **render_kw)),
    )
    return compiler.compile(pipeline)


# ── Base (imports + reader) ──────────────────────────────────────────
class TestCompilerBase:
    def test_vtk_engine_imports(self, compiler):
        script = _compile_render(compiler)
        assert "from viznoir.engine.readers import read_dataset" in script
        assert "from viznoir.engine.renderer import" in script
        assert "from viznoir.engine.filters import apply_filter" in script

    def test_no_paraview_imports(self, compiler):
        script = _compile_render(compiler)
        assert "paraview" not in script
        assert "pvpython" not in script

    def test_read_dataset_call(self, compiler):
        script = _compile_render(compiler)
        assert "read_dataset('/data/case.vtk'" in script

    def test_openfoam_reader(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/cavity.foam", timestep="latest"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "read_dataset('/data/cavity.foam'" in script
        assert "timestep='latest'" in script

    def test_blocks_param(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.foam", blocks=["internalMesh"]),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="U")),
        )
        script = compiler.compile(pipeline)
        assert "blocks=['internalMesh']" in script

    def test_output_dir_env(self, compiler):
        script = _compile_render(compiler)
        assert 'OUTPUT_DIR = os.environ.get("VIZNOIR_OUTPUT_DIR"' in script


# ── Filters ──────────────────────────────────────────────────────────
class TestCompilerFilters:
    def test_slice_filter(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Slice", params={"origin": [0.05, 0, 0], "normal": [1, 0, 0]}),
            ],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter(dataset, 'Slice'" in script
        assert "origin=[0.05, 0, 0]" in script
        assert "normal=[1, 0, 0]" in script

    def test_calculator_filter(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Calculator", params={"expression": "mag(U)", "result_name": "Umag"}),
            ],
            output=OutputDef(type="image", render=RenderDef(field="Umag")),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter(dataset, 'Calculator'" in script
        assert "expression='mag(U)'" in script
        assert "result_name='Umag'" in script

    def test_filter_chain(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Slice", params={"origin": [0, 0, 0], "normal": [0, 0, 1]}),
                FilterStep(filter="Calculator", params={"expression": "mag(U)", "result_name": "Umag"}),
            ],
            output=OutputDef(type="image", render=RenderDef(field="Umag")),
        )
        script = compiler.compile(pipeline)
        # Each filter reassigns dataset
        assert script.count("dataset = apply_filter(dataset,") == 2

    def test_integrate_variables(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="IntegrateVariables")],
            output=OutputDef(type="data", data=DataOutputDef(fields=["p"])),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter(dataset, 'IntegrateVariables'" in script

    def test_threshold_filter(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Threshold", params={"field": "p", "lower": 0.0, "upper": 100.0}),
            ],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter(dataset, 'Threshold'" in script
        assert "field='p'" in script

    def test_contour_filter(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Contour", params={"field": "p", "isovalues": [0.5, 1.0]}),
            ],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter(dataset, 'Contour'" in script
        assert "isovalues=[0.5, 1.0]" in script

    def test_clip_filter(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Clip", params={"origin": [0, 0, 0], "normal": [1, 0, 0], "invert": True}),
            ],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter(dataset, 'Clip'" in script
        assert "invert=True" in script

    def test_unknown_filter_raises(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="NoSuchFilter", params={})],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        with pytest.raises(KeyError, match="NoSuchFilter"):
            compiler.compile(pipeline)


# ── Render output ────────────────────────────────────────────────────
class TestCompilerRender:
    def test_render_config(self, compiler):
        script = _compile_render(compiler, field="pressure")
        assert "RenderConfig(" in script
        assert "array_name='pressure'" in script
        assert "render_to_png(dataset," in script

    def test_resolution(self, compiler):
        script = _compile_render(compiler, field="p", resolution=[800, 600])
        assert "width=800" in script
        assert "height=600" in script

    def test_colormap(self, compiler):
        script = _compile_render(compiler, field="p", colormap="Viridis")
        assert "colormap='viridis'" in script

    def test_log_scale(self, compiler):
        script = _compile_render(compiler, field="p", log_scale=True)
        assert "log_scale=True" in script

    def test_scalar_range(self, compiler):
        script = _compile_render(compiler, field="p", scalar_range=[100.0, 200.0])
        assert "scalar_range=(100.0, 200.0)" in script

    def test_opacity(self, compiler):
        script = _compile_render(compiler, field="p", opacity=0.5)
        assert "opacity=0.5" in script

    def test_wireframe_representation(self, compiler):
        script = _compile_render(compiler, field="p", representation="wireframe")
        assert "representation='wireframe'" in script

    def test_scalar_bar_enabled(self, compiler):
        script = _compile_render(compiler, field="p", scalar_bar=True)
        assert "show_scalar_bar=True" in script

    def test_scalar_bar_disabled(self, compiler):
        script = _compile_render(compiler, field="p", scalar_bar=False)
        assert "show_scalar_bar=False" in script

    def test_background_color(self, compiler):
        script = _compile_render(compiler, field="p", background=[0.1, 0.2, 0.3])
        assert "background=(0.1, 0.2, 0.3)" in script

    def test_output_filename(self, compiler):
        script = _compile_render(compiler, field="p", output_filename="my_render.png")
        assert "my_render.png" in script

    def test_scalar_bar_title(self, compiler):
        script = _compile_render(
            compiler,
            field="p",
            scalar_bar_config=ScalarBarDef(title="Pressure [Pa]"),
        )
        assert "scalar_bar_title='Pressure [Pa]'" in script

    def test_png_write(self, compiler):
        script = _compile_render(compiler)
        assert 'with open(_out, "wb") as f:' in script
        assert "f.write(_png)" in script


# ── Camera ───────────────────────────────────────────────────────────
class TestCompilerCamera:
    def test_camera_preset(self, compiler):
        script = _compile_render(compiler, field="p", camera=CameraDef(preset="top"))
        assert "_camera_preset = 'top'" in script
        assert "preset_camera(_camera_preset" in script

    def test_camera_custom_position(self, compiler):
        script = _compile_render(
            compiler,
            field="p",
            camera=CameraDef(
                preset=None,
                position=[1.0, 2.0, 3.0],
                focal_point=[0.0, 0.0, 0.0],
                view_up=[0.0, 1.0, 0.0],
            ),
        )
        assert "custom_camera(" in script
        assert "_camera_position = [1.0, 2.0, 3.0]" in script
        assert "position=_camera_position" in script
        assert "focal_point=[0.0, 0.0, 0.0]" in script

    def test_camera_zoom(self, compiler):
        script = _compile_render(compiler, field="p", camera=CameraDef(zoom=2.5))
        assert "zoom=2.5" in script

    def test_camera_orthographic(self, compiler):
        script = _compile_render(compiler, field="p", camera=CameraDef(orthographic=True))
        assert "orthographic=True" in script


# ── Data output ──────────────────────────────────────────────────────
class TestCompilerData:
    def test_data_output(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="data", data=DataOutputDef(fields=["p", "U"], statistics_only=True)),
        )
        script = compiler.compile(pipeline)
        assert "extract_stats(dataset" in script
        assert "result.json" in script

    def test_data_with_coordinates(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="data",
                data=DataOutputDef(fields=["p"], include_coordinates=True, statistics_only=False),
            ),
        )
        script = compiler.compile(pipeline)
        assert "extract_data(dataset" in script
        assert "include_coords=True" in script

    def test_csv_output(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="csv", data=DataOutputDef(format="csv")),
        )
        script = compiler.compile(pipeline)
        assert "export_file(dataset" in script
        assert "data.csv" in script

    def test_default_data(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="data"),
        )
        script = compiler.compile(pipeline)
        assert "extract_data(dataset" in script


# ── Export ────────────────────────────────────────────────────────────
class TestCompilerExport:
    def test_export_stl(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="export", export_format=".stl"),
        )
        script = compiler.compile(pipeline)
        assert "export_file(dataset" in script
        assert ".stl" in script

    def test_export_requires_format(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="export"),
        )
        with pytest.raises(ValueError, match="export_format"):
            compiler.compile(pipeline)


# ── Inspect ──────────────────────────────────────────────────────────
class TestCompilerInspect:
    def test_inspect_script(self, compiler):
        script = compiler.compile_inspect("/data/case.vtk")
        assert "inspect_dataset(dataset)" in script
        assert "get_timesteps('/data/case.vtk')" in script
        assert "list_arrays('/data/case.vtk')" in script
        assert "list_blocks('/data/case.vtk')" in script
        assert "result.json" in script

    def test_inspect_no_paraview(self, compiler):
        script = compiler.compile_inspect("/data/cavity.foam")
        assert "paraview" not in script


# ── Animation ────────────────────────────────────────────────────────
class TestCompilerAnimation:
    def test_animation_timesteps(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.foam"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), fps=24, mode="timesteps"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "get_timesteps" in script
        assert "frame_" in script
        assert "render_to_png" in script
        assert "'timesteps'" in script

    def test_animation_orbit(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(
                    render=RenderDef(field="p"),
                    mode="orbit",
                    orbit_duration=5.0,
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "'orbit'" in script
        assert "custom_camera" in script
        assert "math.cos" in script

    def test_animation_time_range(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.foam"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(
                    render=RenderDef(field="p"),
                    time_range=[0.0, 1.0],
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "[0.0, 1.0]" in script

    def test_animation_speed_factor(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.foam"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), speed_factor=5.0),
            ),
        )
        script = compiler.compile(pipeline)
        assert "_speed_factor = 5.0" in script

    def test_animation_requires_def(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="animation"),
        )
        with pytest.raises(ValueError, match="animation"):
            compiler.compile(pipeline)


# ── Split animation ──────────────────────────────────────────────────
class TestCompilerSplitAnimation:
    def test_split_anim_basic(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.foam"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render",
                            row=0,
                            col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                        PaneDef(
                            type="graph",
                            row=0,
                            col=1,
                            graph_pane=GraphPaneDef(
                                series=[GraphSeriesDef(field="p", stat="max")],
                            ),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "render_to_png" in script
        assert "extract_stats" in script
        assert "stats.json" in script
        assert "pane" in script.lower()

    def test_split_anim_requires_def(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="split_animation"),
        )
        with pytest.raises(ValueError, match="split_animation"):
            compiler.compile(pipeline)


# ── Multi output ─────────────────────────────────────────────────────
class TestCompilerMulti:
    def test_multi_render_and_data(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="multi",
                render=RenderDef(field="p"),
                data=DataOutputDef(fields=["p"]),
            ),
        )
        script = compiler.compile(pipeline)
        assert "render_to_png" in script
        assert "extract_data" in script

    def test_unknown_output_type(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        # Monkey-patch to test unknown type
        pipeline.output.type = "unknown"  # type: ignore[assignment]
        with pytest.raises(ValueError, match="Unknown output type"):
            compiler.compile(pipeline)


# ── Source files ─────────────────────────────────────────────────────
class TestCompilerSourceFiles:
    def test_explicit_file_list(self, compiler):
        pipeline = PipelineDefinition(
            source=SourceDef(
                file="/data/PartFluid_0001.vtk",
                files=["/data/PartFluid_0001.vtk", "/data/PartFluid_0002.vtk"],
            ),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "_source_files" in script
        assert "PartFluid_0001.vtk" in script
        assert "PartFluid_0002.vtk" in script

    def test_file_pattern_no_match(self, compiler):
        """file_pattern that matches nothing raises ValueError."""
        pipeline = PipelineDefinition(
            source=SourceDef(
                file="/data/dummy.vtk",
                file_pattern="/nonexistent_dir_xyz_abc/*.vtk",
            ),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        with pytest.raises(ValueError, match="matched no files"):
            compiler.compile(pipeline)

    def test_file_pattern_with_match(self, compiler, tmp_path):
        """file_pattern matching real files compiles source_files."""
        (tmp_path / "frame_001.vtk").touch()
        (tmp_path / "frame_002.vtk").touch()

        pipeline = PipelineDefinition(
            source=SourceDef(
                file=str(tmp_path / "frame_001.vtk"),
                file_pattern=str(tmp_path / "frame_*.vtk"),
            ),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert "_source_files" in script
        assert "frame_001.vtk" in script

    def test_animation_with_source_files(self, compiler):
        """Animation compile includes source_files when provided."""
        pipeline = PipelineDefinition(
            source=SourceDef(
                file="/data/case_0001.vtk",
                files=["/data/case_0001.vtk", "/data/case_0002.vtk"],
            ),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), fps=10),
            ),
        )
        script = compiler.compile(pipeline)
        assert "case_0001.vtk" in script
        assert "case_0002.vtk" in script

    def test_animation_with_file_pattern(self, compiler, tmp_path):
        """Animation compile resolves file_pattern."""
        (tmp_path / "step_001.vtk").touch()
        (tmp_path / "step_002.vtk").touch()

        pipeline = PipelineDefinition(
            source=SourceDef(
                file=str(tmp_path / "step_001.vtk"),
                file_pattern=str(tmp_path / "step_*.vtk"),
            ),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), fps=10),
            ),
        )
        script = compiler.compile(pipeline)
        assert "step_001.vtk" in script

    def test_animation_with_filters(self, compiler):
        """Animation with pipeline filters includes filter code."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="Slice", params={"origin": [0, 0, 0]})],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p"), fps=10),
            ),
        )
        script = compiler.compile(pipeline)
        assert "apply_filter" in script or "slice" in script.lower()

    def test_render_without_render_def_raises(self, compiler):
        """Image output without render definition raises."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="image"),
        )
        with pytest.raises(ValueError, match="render"):
            compiler.compile(pipeline)

    def test_split_anim_with_source_files(self, compiler):
        """Split animation compile includes source_files."""
        pipeline = PipelineDefinition(
            source=SourceDef(
                file="/data/case_0001.vtk",
                files=["/data/case_0001.vtk", "/data/case_0002.vtk"],
            ),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render",
                            row=0,
                            col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                        PaneDef(
                            type="graph",
                            row=0,
                            col=1,
                            graph_pane=GraphPaneDef(series=[GraphSeriesDef(field="p", stat="mean")]),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=2),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "case_0001.vtk" in script
        assert "case_0002.vtk" in script

    def test_split_anim_with_file_pattern(self, compiler, tmp_path):
        """Split animation compile resolves file_pattern via glob."""
        (tmp_path / "step_001.vtk").touch()
        (tmp_path / "step_002.vtk").touch()

        pipeline = PipelineDefinition(
            source=SourceDef(
                file=str(tmp_path / "step_001.vtk"),
                file_pattern=str(tmp_path / "step_*.vtk"),
            ),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render",
                            row=0,
                            col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=1),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "step_001.vtk" in script
        assert "step_002.vtk" in script

    def test_split_anim_render_pane_with_filters(self, compiler):
        """Split animation render pane with pipeline filters."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render",
                            row=0,
                            col=0,
                            render_pane=RenderPaneDef(
                                render=RenderDef(field="p"),
                                pipeline=[
                                    FilterStep(
                                        filter="Slice",
                                        params={"origin": [0, 0, 0]},
                                    ),
                                ],
                            ),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=1),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "Slice" in script or "slice_plane" in script.lower()
