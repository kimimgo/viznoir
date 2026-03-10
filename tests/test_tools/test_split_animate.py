"""Tests for split_animate tool — model validation and compilation."""

from __future__ import annotations

from typing import Any

from viznoir.core.compiler import ScriptCompiler
from viznoir.pipeline.engine import validate_pipeline
from viznoir.pipeline.models import (
    GraphPaneDef,
    GraphSeriesDef,
    OutputDef,
    PaneDef,
    PipelineDefinition,
    RenderDef,
    RenderPaneDef,
    SourceDef,
    SplitAnimationDef,
)


def _make_split_pipeline(
    panes: list[dict[str, Any]] | None = None,
    rows: int = 1,
    cols: int = 2,
) -> PipelineDefinition:
    """Create a split animation pipeline for testing."""
    if panes is None:
        panes = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}, "title": "Pressure"}},
            {"type": "render", "row": 0, "col": 1, "render_pane": {"render": {"field": "U", "colormap": "Viridis"}}},
        ]
    return PipelineDefinition(
        source=SourceDef(file="/data/case.pvd"),
        pipeline=[],
        output=OutputDef(
            type="split_animation",
            split_animation=SplitAnimationDef.model_validate(
                {
                    "panes": panes,
                    "layout": {"rows": rows, "cols": cols},
                    "fps": 24,
                    "speed_factor": 5.0,
                }
            ),
        ),
    )


class TestSplitAnimationModels:
    def test_split_animation_from_json(self) -> None:
        """SplitAnimationDef should parse from JSON."""
        data: dict[str, Any] = {
            "panes": [
                {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}}},
                {"type": "graph", "row": 0, "col": 1, "graph_pane": {"series": [{"field": "p", "stat": "max"}]}},
            ],
            "layout": {"rows": 1, "cols": 2, "gap": 8},
            "fps": 30,
            "speed_factor": 2.0,
            "resolution": [1920, 1080],
        }
        sa = SplitAnimationDef.model_validate(data)
        assert len(sa.panes) == 2
        assert sa.panes[0].type == "render"
        assert sa.panes[1].type == "graph"
        assert sa.layout.gap == 8
        assert sa.fps == 30
        assert sa.speed_factor == 2.0

    def test_split_animation_defaults(self) -> None:
        """SplitAnimationDef should have sensible defaults."""
        sa = SplitAnimationDef(
            panes=[
                PaneDef(type="render", render_pane=RenderPaneDef(render=RenderDef(field="p"))),
            ]
        )
        assert sa.layout.rows == 1
        assert sa.layout.cols == 2
        assert sa.layout.gap == 4
        assert sa.fps == 24
        assert sa.speed_factor == 1.0
        assert sa.resolution == [1920, 1080]
        assert sa.gif is True

    def test_render_pane_with_pipeline(self) -> None:
        """RenderPaneDef should accept per-pane filter pipeline."""
        data: dict[str, Any] = {
            "render": {"field": "p"},
            "title": "Sliced Pressure",
            "pipeline": [
                {"filter": "Slice", "params": {"origin": [0, 0, 0], "normal": [1, 0, 0]}},
            ],
        }
        rpd = RenderPaneDef.model_validate(data)
        assert rpd.title == "Sliced Pressure"
        assert len(rpd.pipeline) == 1
        assert rpd.pipeline[0].filter == "Slice"

    def test_graph_pane_series(self) -> None:
        """GraphPaneDef should accept multiple series."""
        gpd = GraphPaneDef(
            series=[
                GraphSeriesDef(field="p", stat="max", label="P max"),
                GraphSeriesDef(field="p", stat="mean", color="#ff0000"),
            ],
            title="Pressure",
            y_label="p [Pa]",
            y_range=[0.0, 100.0],
        )
        assert len(gpd.series) == 2
        assert gpd.y_range == [0.0, 100.0]

    def test_output_def_with_split_animation(self) -> None:
        """OutputDef should accept split_animation type."""
        od = OutputDef(
            type="split_animation",
            split_animation=SplitAnimationDef(
                panes=[
                    PaneDef(type="render", render_pane=RenderPaneDef(render=RenderDef(field="p"))),
                ]
            ),
        )
        assert od.type == "split_animation"
        assert od.split_animation is not None


class TestSplitAnimationValidation:
    def test_valid_split_animation(self) -> None:
        pipeline = _make_split_pipeline()
        errors = validate_pipeline(pipeline)
        assert errors == []

    def test_missing_split_animation_def(self) -> None:
        pipeline = PipelineDefinition(
            source=SourceDef(file="/data/case.pvd"),
            pipeline=[],
            output=OutputDef(type="split_animation"),
        )
        errors = validate_pipeline(pipeline)
        assert any("split_animation" in e for e in errors)

    def test_pane_row_out_of_range(self) -> None:
        pipeline = _make_split_pipeline(
            panes=[
                {"type": "render", "row": 5, "col": 0, "render_pane": {"render": {"field": "p"}}},
            ],
            rows=1,
            cols=2,
        )
        errors = validate_pipeline(pipeline)
        assert any("row" in e for e in errors)

    def test_pane_col_out_of_range(self) -> None:
        pipeline = _make_split_pipeline(
            panes=[
                {"type": "render", "row": 0, "col": 3, "render_pane": {"render": {"field": "p"}}},
            ],
            rows=1,
            cols=2,
        )
        errors = validate_pipeline(pipeline)
        assert any("col" in e for e in errors)

    def test_render_pane_without_definition(self) -> None:
        pipeline = _make_split_pipeline(
            panes=[{"type": "render", "row": 0, "col": 0}],
            rows=1,
            cols=1,
        )
        errors = validate_pipeline(pipeline)
        assert any("render_pane" in e for e in errors)

    def test_graph_pane_without_definition(self) -> None:
        pipeline = _make_split_pipeline(
            panes=[
                {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}}},
                {"type": "graph", "row": 0, "col": 1},
            ],
            rows=1,
            cols=2,
        )
        errors = validate_pipeline(pipeline)
        assert any("graph_pane" in e for e in errors)

    def test_no_render_pane_error(self) -> None:
        pipeline = _make_split_pipeline(
            panes=[
                {"type": "graph", "row": 0, "col": 0, "graph_pane": {"series": [{"field": "p", "stat": "max"}]}},
            ],
            rows=1,
            cols=1,
        )
        errors = validate_pipeline(pipeline)
        assert any("at least one render" in e for e in errors)


class TestSplitAnimationCompilation:
    def test_compile_basic(self) -> None:
        """split_animation should compile to a valid VTK engine script."""
        compiler = ScriptCompiler()
        pipeline = _make_split_pipeline()
        script = compiler.compile(pipeline)

        assert "render_to_png" in script
        assert "pane" in script.lower()
        assert "frame_" in script
        assert "stats.json" in script
        assert "result.json" in script

    def test_compile_with_graph_extracts_stats(self) -> None:
        """Graph pane fields should trigger stats extraction."""
        compiler = ScriptCompiler()
        panes: list[dict[str, Any]] = [
            {"type": "render", "row": 0, "col": 0, "render_pane": {"render": {"field": "p"}}},
            {
                "type": "graph",
                "row": 0,
                "col": 1,
                "graph_pane": {
                    "series": [
                        {"field": "p", "stat": "max"},
                        {"field": "U", "stat": "mean"},
                    ]
                },
            },
        ]
        pipeline = _make_split_pipeline(panes=panes)
        script = compiler.compile(pipeline)

        # stat_fields should include both p and U
        assert "'U'" in script
        assert "'p'" in script
        assert "extract_stats" in script

    def test_compile_speed_factor(self) -> None:
        """speed_factor should be passed to template."""
        compiler = ScriptCompiler()
        pipeline = _make_split_pipeline()
        script = compiler.compile(pipeline)
        assert "_speed_factor = 5.0" in script

    def test_compile_per_pane_colormap(self) -> None:
        """Each pane should use its own colormap."""
        compiler = ScriptCompiler()
        pipeline = _make_split_pipeline()
        script = compiler.compile(pipeline)
        assert '"colormap": "cool to warm"' in script
        assert '"colormap": "viridis"' in script
