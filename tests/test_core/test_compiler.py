"""Tests for ScriptCompiler — Pipeline JSON → pvpython script verification."""

from __future__ import annotations

from typing import Any

import pytest

from parapilot.core.compiler import ScriptCompiler
from parapilot.pipeline.models import (
    AnimationDef,
    CameraDef,
    DataOutputDef,
    FilterStep,
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


class TestScriptCompilerBase:
    def test_compile_basic_render(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="pressure"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "from paraview.simple import *" in script
        assert "LegacyVTKReader" in script
        assert "SaveScreenshot" in script
        assert "pressure" in script

    def test_compile_openfoam_reader(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/cavity.foam", timestep="latest"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "OpenFOAMReader" in script
        assert "timesteps[-1]" in script

    def test_compile_with_blocks(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.foam", blocks=["internalMesh"]),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="U"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "internalMesh" in script


class TestScriptCompilerFilters:
    def test_compile_slice(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(
                    filter="Slice",
                    params={"origin": [0.05, 0, 0], "normal": [1, 0, 0]},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "Slice" in script
        assert "[0.05, 0, 0]" in script
        assert "[1, 0, 0]" in script

    def test_compile_calculator(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(
                    filter="Calculator",
                    params={"expression": "mag(U)", "result_name": "Umag"},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="Umag"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "Calculator" in script
        assert "mag(U)" in script
        assert "Umag" in script

    def test_compile_filter_chain(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="Slice", params={"origin": [0, 0, 0], "normal": [0, 0, 1]}),
                FilterStep(
                    filter="Calculator",
                    params={"expression": "mag(U)", "result_name": "Umag"},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="Umag"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "f_1" in script  # First filter
        assert "f_2" in script  # Second filter
        assert "current = f_1" in script
        assert "current = f_2" in script

    def test_compile_integrate_variables(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(filter="IntegrateVariables"),
            ],
            output=OutputDef(
                type="data",
                data=DataOutputDef(fields=["p"]),
            ),
        )
        script = compiler.compile(pipeline)
        assert "IntegrateVariables" in script


class TestScriptCompilerOutput:
    def test_compile_data_output(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="data",
                data=DataOutputDef(fields=["p", "U"], statistics_only=True),
            ),
        )
        script = compiler.compile(pipeline)
        assert "servermanager.Fetch" in script
        assert "result.json" in script

    def test_compile_export_output(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="export", export_format="stl"),
        )
        script = compiler.compile(pipeline)
        assert "SaveData" in script
        assert "export.stl" in script

    def test_compile_render_with_camera_preset(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(
                    field="p",
                    camera=CameraDef(preset="top"),
                    resolution=[800, 600],
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "CameraPosition = [0, 0, 1]" in script
        assert "[800, 600]" in script

    def test_compile_render_custom_colormap(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p", colormap="Viridis"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "Viridis" in script
        assert "ApplyPreset" in script


class TestScriptCompilerRenderAdvanced:
    """Tests for POC-derived render features: LUT init, scalar bar, log scale, etc."""

    def test_lut_always_initialized(self, compiler: ScriptCompiler):
        """LUT ApplyPreset should always be emitted, even for default colormap."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),  # default "Cool to Warm"
            ),
        )
        script = compiler.compile(pipeline)
        assert 'ApplyPreset("Cool to Warm", True)' in script

    def test_log_scale(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p", log_scale=True),
            ),
        )
        script = compiler.compile(pipeline)
        assert "UseLogScale = 1" in script
        assert "MapControlPointsToLogSpace" in script

    def test_clamped_range_colors(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(
                    field="p",
                    scalar_range=[100.0, 200.0],
                    above_range_color=[0.5, 0.0, 0.0],
                    below_range_color=[0.0, 0.0, 0.5],
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "UseAboveRangeColor = 1" in script
        assert "AboveRangeColor = [0.5, 0.0, 0.0]" in script
        assert "UseBelowRangeColor = 1" in script
        assert "BelowRangeColor = [0.0, 0.0, 0.5]" in script

    def test_scalar_bar_config(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(
                    field="p",
                    scalar_bar_config=ScalarBarDef(
                        title="Pressure",
                        component_title="[Pa]",
                        orientation="Horizontal",
                        position=[0.3, 0.05],
                        label_format="%.1f",
                    ),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert 'sb.Title = "Pressure"' in script
        assert 'sb.ComponentTitle = "[Pa]"' in script
        assert 'sb.Orientation = "Horizontal"' in script
        assert "WindowLocation = 'Any Location'" in script
        assert "sb.Position = [0.3, 0.05]" in script
        assert 'sb.RangeLabelFormat = "%.1f"' in script

    def test_orthographic_camera(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(
                    field="p",
                    camera=CameraDef(preset="top", orthographic=True),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "CameraParallelProjection = 1" in script
        assert "CameraPosition = [0, 0, 1]" in script

    def test_specular_lighting(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p", specular=0.6, specular_power=30.0),
            ),
        )
        script = compiler.compile(pipeline)
        assert "display.Specular = 0.6" in script
        assert "display.SpecularPower = 30.0" in script

    def test_point_gaussian_representation(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(
                    field="p",
                    representation="Point Gaussian",
                    point_size=0.8,
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert 'display.Representation = "Point Gaussian"' in script
        # Auto-scaling: GaussianRadius = _dp_est * point_size
        assert "GetDataInformation().GetBounds()" in script
        assert "GetNumberOfPoints()" in script
        assert "_dp_est" in script
        assert "* 0.8" in script
        assert "ShaderPreset = 'Sphere'" in script


class TestScriptCompilerAnimation:
    """Tests for animation template: LUT init, representation, scalar bar."""

    def _make_anim_pipeline(
        self,
        speed_factor: float = 1.0,
        orbit_duration: float = 10.0,
        fps: int = 24,
        mode: str = "timesteps",
        time_range: list[float] | None = None,
        **render_overrides: Any,
    ) -> PipelineDefinition:
        render_kwargs: dict[str, Any] = {"field": "p"}
        render_kwargs.update(render_overrides)
        return PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(
                    render=RenderDef(**render_kwargs),
                    fps=fps,
                    speed_factor=speed_factor,
                    mode=mode,
                    time_range=time_range,
                    orbit_duration=orbit_duration,
                ),
            ),
        )

    def test_animate_lut_always_initialized(self, compiler: ScriptCompiler):
        """LUT ApplyPreset should always be emitted in animate, even for default colormap."""
        pipeline = self._make_anim_pipeline()  # default "Cool to Warm"
        script = compiler.compile(pipeline)
        assert 'ApplyPreset("Cool to Warm", True)' in script

    def test_animate_custom_colormap(self, compiler: ScriptCompiler):
        """Custom colormap should be applied in animation."""
        pipeline = self._make_anim_pipeline(colormap="Viridis")
        script = compiler.compile(pipeline)
        assert 'ApplyPreset("Viridis", True)' in script

    def test_animate_representation_passed(self, compiler: ScriptCompiler):
        """Representation should be passed to animate template."""
        pipeline = self._make_anim_pipeline(representation="Wireframe")
        script = compiler.compile(pipeline)
        assert 'display.Representation = "Wireframe"' in script

    def test_animate_point_gaussian(self, compiler: ScriptCompiler):
        """Point Gaussian representation should auto-scale GaussianRadius in animate."""
        pipeline = self._make_anim_pipeline(
            representation="Point Gaussian", point_size=0.8
        )
        script = compiler.compile(pipeline)
        assert 'display.Representation = "Point Gaussian"' in script
        # Auto-scaling: GaussianRadius = _dp_est * point_size
        assert "GetDataInformation().GetBounds()" in script
        assert "_dp_est" in script
        assert "* 0.8" in script
        assert "ShaderPreset = 'Sphere'" in script

    def test_animate_scalar_bar_enabled(self, compiler: ScriptCompiler):
        """Scalar bar should be enabled by default in animate."""
        pipeline = self._make_anim_pipeline()
        script = compiler.compile(pipeline)
        assert "SetScalarBarVisibility(render_view, True)" in script
        assert "GetScalarBar" in script

    def test_animate_scalar_bar_disabled(self, compiler: ScriptCompiler):
        """Scalar bar can be disabled in animate."""
        pipeline = self._make_anim_pipeline(scalar_bar=False)
        script = compiler.compile(pipeline)
        assert "SetScalarBarVisibility(render_view, False)" in script

    def test_animate_opacity(self, compiler: ScriptCompiler):
        """Opacity should be passed to animate template."""
        pipeline = self._make_anim_pipeline(opacity=0.5)
        script = compiler.compile(pipeline)
        assert "display.Opacity = 0.5" in script

    def test_animate_scalar_range(self, compiler: ScriptCompiler):
        """Fixed scalar range should be passed to animate template."""
        pipeline = self._make_anim_pipeline(scalar_range=[0.0, 1.0])
        script = compiler.compile(pipeline)
        assert "RescaleTransferFunction(0.0, 1.0)" in script

    def test_animate_speed_factor_default(self, compiler: ScriptCompiler):
        """Default speed_factor=1.0 should produce real-time animation."""
        pipeline = self._make_anim_pipeline()
        script = compiler.compile(pipeline)
        assert "_speed_factor = 1.0" in script
        assert "_anim_duration = _physics_duration / _speed_factor" in script

    def test_animate_speed_factor_5x(self, compiler: ScriptCompiler):
        """speed_factor=5.0 should fast-forward 5x."""
        pipeline = self._make_anim_pipeline(speed_factor=5.0)
        script = compiler.compile(pipeline)
        assert "_speed_factor = 5.0" in script

    def test_animate_speed_factor_slowmo(self, compiler: ScriptCompiler):
        """speed_factor=0.2 should produce 5x slow-motion."""
        pipeline = self._make_anim_pipeline(speed_factor=0.2)
        script = compiler.compile(pipeline)
        assert "_speed_factor = 0.2" in script

    def test_animate_frame_sampling_logic(self, compiler: ScriptCompiler):
        """Animation should compute target frames with dedup cap."""
        pipeline = self._make_anim_pipeline(fps=24, speed_factor=1.0)
        script = compiler.compile(pipeline)
        # Frame count is capped at available timesteps to prevent duplicate renders
        assert "min(int(round(_anim_duration * _fps)), len(_all_timesteps))" in script
        assert "_seen_indices" in script  # Deduplication
        assert "_t_target = _all_timesteps[0]" in script
        assert "effective_fps" in script

    def test_animate_orbit_duration(self, compiler: ScriptCompiler):
        """Orbit mode should use orbit_duration parameter."""
        pipeline = self._make_anim_pipeline(mode="orbit", orbit_duration=5.0)
        script = compiler.compile(pipeline)
        assert "_orbit_duration = 5.0" in script
        assert "n_frames = int(_orbit_duration * _fps)" in script

    def test_animate_time_range_filter(self, compiler: ScriptCompiler):
        """time_range should filter timesteps in generated script."""
        pipeline = self._make_anim_pipeline(time_range=[0.5, 1.5])
        script = compiler.compile(pipeline)
        assert "0.5 <= t <= 1.5" in script

    def test_animate_result_includes_speed_info(self, compiler: ScriptCompiler):
        """Result dict should include speed_factor and timing info."""
        pipeline = self._make_anim_pipeline(speed_factor=2.0)
        script = compiler.compile(pipeline)
        assert '"speed_factor": _speed_factor' in script
        assert '"physics_duration": _physics_duration' in script
        assert '"animation_duration": _anim_duration' in script


class TestScriptCompilerRenderScalarBar:
    """Tests for scalar bar default styling."""

    def test_scalar_bar_default_font_sizes(self, compiler: ScriptCompiler):
        """When scalar_bar=True but no config, default font sizes should be set."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),  # scalar_bar=True by default, no config
            ),
        )
        script = compiler.compile(pipeline)
        assert "GetScalarBar" in script
        assert "int(32 * _font_scale)" in script
        assert "int(24 * _font_scale)" in script


class TestScriptCompilerInspect:
    def test_compile_inspect(self, compiler: ScriptCompiler):
        script = compiler.compile_inspect("/data/case.vtk")
        assert "LegacyVTKReader" in script
        assert "GetNumberOfPoints" in script
        assert "GetNumberOfCells" in script
        assert "result.json" in script


class TestExtractBlockSelector:
    """Tests for ExtractBlock selector-based block search."""

    def test_extractblock_selector_in_script(self, compiler: ScriptCompiler):
        """ExtractBlock should generate selector-based block search code."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtm"),
            pipeline=[
                FilterStep(
                    filter="ExtractBlock",
                    params={"selector": "internalMesh"},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        # Should contain selector-based search, not hardcoded BlockIndices = [1]
        assert "internalMesh" in script
        assert "GetCompositeDataInformation" in script
        assert "Selectors" in script
        assert "BlockIndices = [1]" not in script


    def test_extractblock_exact_match_mode(self, compiler: ScriptCompiler):
        """ExtractBlock with match_mode='exact' should use equality check."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtm"),
            pipeline=[
                FilterStep(
                    filter="ExtractBlock",
                    params={"selector": "wall", "match_mode": "exact"},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        assert '_match_mode = "exact"' in script
        assert "_name == _selector" in script

    def test_extractblock_no_match_raises_error(self, compiler: ScriptCompiler):
        """ExtractBlock should raise RuntimeError when no blocks match."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtm"),
            pipeline=[
                FilterStep(
                    filter="ExtractBlock",
                    params={"selector": "nonexistent"},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "raise RuntimeError" in script
        assert "no block matching" in script


class TestProgrammableFilterInjection:
    """Tests for ProgrammableFilter script injection prevention."""

    def test_programmable_filter_script_escaped(self, compiler: ScriptCompiler):
        """Triple-quote script should be safely handled via b64 encoding."""
        # Intentionally crafted string that would break triple-quote escaping
        tricky_script = 'output.ShallowCopy(input)\n"""\nprint("escaped")\n"""'
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(
                    filter="ProgrammableFilter",
                    params={"script": tricky_script},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        # Should NOT contain raw triple-quote that would break syntax
        assert '"""\nprint' not in script
        # Should use b64 decoding
        assert "b64decode" in script

    def test_programmable_filter_normal_script(self, compiler: ScriptCompiler):
        """Normal script should work correctly via b64 encoding."""
        normal_script = "output.ShallowCopy(inputs[0].VTKObject)"
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(
                    filter="ProgrammableFilter",
                    params={"script": normal_script},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "b64decode" in script
        # Verify the base64 decodes back to original
        import base64
        encoded = base64.b64encode(normal_script.encode()).decode()
        assert encoded in script


class TestScriptCompilerValidation:
    def test_unknown_filter_raises(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="FakeFilter")],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        with pytest.raises(KeyError, match="Unknown filter"):
            compiler.compile(pipeline)

    def test_missing_required_param_raises(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[FilterStep(filter="Slice", params={})],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        with pytest.raises(ValueError, match="requires parameter"):
            compiler.compile(pipeline)

    def test_unknown_format_raises(self, compiler: ScriptCompiler):
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.xyz"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        with pytest.raises(ValueError, match="Unsupported file format"):
            compiler.compile(pipeline)


class TestRunnerNoMountLeak:
    """Tests for ParaViewRunner extra_mounts state isolation."""

    def test_runner_no_mount_leak(self):
        """Consecutive execute() calls should not leak _extra_mounts state."""
        from parapilot.core.runner import ParaViewRunner

        runner = ParaViewRunner(mode="local")

        # Simulate first call setting extra_mounts
        # After the fix, execute() should not store extra_mounts on self
        assert not hasattr(runner, "_extra_mounts") or runner._extra_mounts == []

        # The runner should not accumulate mounts across calls
        # We verify the fix by checking _run_docker accepts extra_mounts param
        import inspect
        sig = inspect.signature(runner._run_docker)
        assert "extra_mounts" in sig.parameters, (
            "_run_docker should accept extra_mounts parameter"
        )


class TestGPUConfig:
    """Tests for GPU rendering configuration."""

    def test_default_render_backend_is_gpu(self):
        """Default render_backend should be 'gpu'."""
        from parapilot.config import PVConfig
        config = PVConfig(data_dir="/data", output_dir="/output")
        assert config.render_backend == "gpu"
        assert config.use_gpu is True

    def test_cpu_backend(self):
        """CPU render_backend should disable GPU."""
        from parapilot.config import PVConfig
        config = PVConfig(data_dir="/data", output_dir="/output", render_backend="cpu")
        assert config.render_backend == "cpu"
        assert config.use_gpu is False

    def test_gpu_device_default(self):
        """Default GPU device should be 0."""
        from parapilot.config import PVConfig
        config = PVConfig(data_dir="/data", output_dir="/output")
        assert config.gpu_device == 0

    def test_render_backend_from_env(self, monkeypatch: Any):
        """PARAPILOT_RENDER_BACKEND env var should be respected."""
        monkeypatch.setenv("PARAPILOT_RENDER_BACKEND", "cpu")
        from parapilot.config import PVConfig
        config = PVConfig(data_dir="/data", output_dir="/output")
        assert config.render_backend == "cpu"

    def test_invalid_render_backend_defaults_to_gpu(self):
        """Invalid render_backend value should fall back to 'gpu'."""
        from parapilot.config import _parse_render_backend
        assert _parse_render_backend("invalid") == "gpu"
        assert _parse_render_backend("GPU") == "gpu"
        assert _parse_render_backend(" cpu ") == "cpu"


class TestOutputFilename:
    """Tests for customizable output filename (P1-2)."""

    def test_render_default_filename(self, compiler: ScriptCompiler):
        """Default output filename should be 'render.png'."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert '"render.png"' in script

    def test_render_custom_filename(self, compiler: ScriptCompiler):
        """Custom output filename should be used."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p", output_filename="snapshot_press.png"),
            ),
        )
        script = compiler.compile(pipeline)
        assert '"snapshot_press.png"' in script
        assert '"render.png"' not in script


class TestFileSeriesSupport:
    """Tests for VTK file series support (P0-1)."""

    def test_source_def_files(self):
        """SourceDef should accept files list."""
        source = SourceDef(
            file="/data/Part_0000.vtk",
            files=["/data/Part_0000.vtk", "/data/Part_0001.vtk"],
        )
        assert source.files is not None
        assert len(source.files) == 2

    def test_source_def_file_pattern(self):
        """SourceDef should accept file_pattern."""
        source = SourceDef(
            file="/data/Part_0000.vtk",
            file_pattern="/data/Part_*.vtk",
        )
        assert source.file_pattern == "/data/Part_*.vtk"

    def test_compile_with_files_list(self, compiler: ScriptCompiler):
        """Multi-file source should generate FileNames list."""
        files = ["/data/Part_0000.vtk", "/data/Part_0001.vtk", "/data/Part_0002.vtk"]
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/Part_0000.vtk", files=files),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        # Should use multi-file reader
        assert "LegacyVTKReader" in script
        assert '"/data/Part_0000.vtk"' in script
        assert '"/data/Part_0001.vtk"' in script
        assert '"/data/Part_0002.vtk"' in script

    def test_compile_single_file_unchanged(self, compiler: ScriptCompiler):
        """Single-file source should remain unchanged."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        script = compiler.compile(pipeline)
        assert 'FileNames=["/data/case.vtk"]' in script

    def test_compile_file_pattern_no_match(self, compiler: ScriptCompiler):
        """file_pattern with no matches should raise ValueError."""
        pipeline = PipelineDefinition(
            source=SourceDef(
                file="/nonexistent/Part_0000.vtk",
                file_pattern="/nonexistent/Part_*.vtk",
            ),
            pipeline=[],
            output=OutputDef(type="image", render=RenderDef(field="p")),
        )
        with pytest.raises(ValueError, match="matched no files"):
            compiler.compile(pipeline)


class TestAnimationVideoOutput:
    """Tests for video output model fields (P0-2)."""

    def test_animation_def_default_format(self):
        """Default output_format should be 'frames'."""
        anim = AnimationDef(render=RenderDef(field="p"))
        assert anim.output_format == "frames"
        assert anim.video_quality == 23

    def test_animation_def_mp4(self):
        """AnimationDef should accept mp4 output_format."""
        anim = AnimationDef(
            render=RenderDef(field="p"),
            output_format="mp4",
            video_quality=18,
            text_overlay="Case: test",
        )
        assert anim.output_format == "mp4"
        assert anim.video_quality == 18
        assert anim.text_overlay == "Case: test"

    def test_animation_def_webm(self):
        """AnimationDef should accept webm output_format."""
        anim = AnimationDef(
            render=RenderDef(field="p"),
            output_format="webm",
        )
        assert anim.output_format == "webm"


class TestProgressReporting:
    """Tests for progress.json generation (P2-1)."""

    def test_animate_has_progress(self, compiler: ScriptCompiler):
        """Animation script should write progress.json."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p")),
            ),
        )
        script = compiler.compile(pipeline)
        assert "progress.json" in script
        assert '"pct"' in script

    def test_split_animate_has_progress(self, compiler: ScriptCompiler):
        """Split animation script should write progress.json."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render", row=0, col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=1),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "progress.json" in script


class TestColorByAutoDetect:
    """Tests for Issue #4: ColorBy association auto-detection."""

    def test_compile_render_colorby_autodetect(self, compiler: ScriptCompiler):
        """Render template should include auto-detect logic for association."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.vtk"),
            pipeline=[
                FilterStep(
                    filter="Slice",
                    params={"origin": [0, 0, 0], "normal": [1, 0, 0]},
                ),
            ],
            output=OutputDef(
                type="image",
                render=RenderDef(field="p"),
            ),
        )
        script = compiler.compile(pipeline)
        assert "GetPointDataInformation" in script
        assert "GetCellDataInformation" in script
        assert "GetArrayInformation" in script

    def test_compile_animate_colorby_autodetect(self, compiler: ScriptCompiler):
        """Animate template should include auto-detect logic for association."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p")),
            ),
        )
        script = compiler.compile(pipeline)
        assert "GetPointDataInformation" in script
        assert "GetCellDataInformation" in script
        assert "GetArrayInformation" in script

    def test_compile_split_animate_colorby_autodetect(self, compiler: ScriptCompiler):
        """Split animate template should include auto-detect logic for association."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render", row=0, col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=1),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "GetPointDataInformation" in script
        assert "GetCellDataInformation" in script
        assert "GetArrayInformation" in script


class TestPerFileLoading:
    """Tests for Issue #6: Per-file loading fallback for animations."""

    def test_compile_animation_perfile_mode(self, compiler: ScriptCompiler):
        """Animation with source_files should generate per-file loading code."""
        files = ["/data/Part_0000.vtk", "/data/Part_0001.vtk", "/data/Part_0002.vtk"]
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/Part_0000.vtk", files=files),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p")),
            ),
        )
        script = compiler.compile(pipeline)
        # Should contain per-file loading markers
        assert "Per-file loading mode" in script
        assert "_source_files" in script
        assert "LegacyVTKReader" in script
        assert "Hide(" in script
        assert "Delete(" in script
        # Should NOT contain time-series mode
        assert "reader.UpdatePipeline(time=_t)" not in script

    def test_compile_animation_timeseries_mode(self, compiler: ScriptCompiler):
        """Animation without source_files should use existing time-series mode."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="animation",
                animation=AnimationDef(render=RenderDef(field="p")),
            ),
        )
        script = compiler.compile(pipeline)
        # Should contain time-series mode
        assert "Time-series mode" in script
        assert "reader.UpdatePipeline()" in script
        assert "_all_timesteps" in script
        # Should NOT contain per-file loading
        assert "Per-file loading mode" not in script

    def test_compile_split_animation_perfile_mode(self, compiler: ScriptCompiler):
        """Split animation with source_files should generate per-file loading code."""
        files = ["/data/Part_0000.vtk", "/data/Part_0001.vtk"]
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/Part_0000.vtk", files=files),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render", row=0, col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=1),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "Per-file loading mode" in script
        assert "_source_files" in script

    def test_compile_split_animation_timeseries_mode(self, compiler: ScriptCompiler):
        """Split animation without source_files should use time-series mode."""
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(
                type="split_animation",
                split_animation=SplitAnimationDef(
                    panes=[
                        PaneDef(
                            type="render", row=0, col=0,
                            render_pane=RenderPaneDef(render=RenderDef(field="p")),
                        ),
                    ],
                    layout=LayoutDef(rows=1, cols=1),
                ),
            ),
        )
        script = compiler.compile(pipeline)
        assert "Time-series mode" in script
        assert "Per-file loading mode" not in script


class TestIsoSurfaceTool:
    """Tests for Issue #5: pv_isosurface MCP tool."""

    def test_isosurface_tool_registered(self):
        """pv_isosurface tool should be registered on the MCP server."""
        from parapilot.server import mcp

        # get_tool returns the tool or raises; _tools is the internal dict
        tools = mcp._tool_manager._tools
        assert "pv_isosurface" in tools

    def test_isosurface_impl_exists(self):
        """pv_isosurface_impl function should be importable."""
        from parapilot.tools.isosurface import pv_isosurface_impl

        assert callable(pv_isosurface_impl)
