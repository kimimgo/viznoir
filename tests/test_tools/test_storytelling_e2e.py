"""End-to-end test: analyze_data → compose_assets pipeline."""

from __future__ import annotations

from pathlib import Path

import vtk


def _make_wavelet_file(tmp_path: Path) -> str:
    """Create a wavelet VTK file for testing."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-8, 8, -8, 8, -8, 8)
    src.Update()

    writer = vtk.vtkXMLImageDataWriter()
    path = str(tmp_path / "wavelet.vti")
    writer.SetFileName(path)
    writer.SetInputData(src.GetOutput())
    writer.Write()
    return path


class TestAnalyzeToComposePipeline:
    def test_analyze_returns_insights(self):
        from viznoir.engine.analysis import analyze_dataset
        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(-8, 8, -8, 8, -8, 8)
        src.Update()
        report = analyze_dataset(src.GetOutput())

        assert report["summary"]["num_points"] > 0
        assert len(report["field_analyses"]) >= 1
        assert len(report["suggested_equations"]) >= 1

        # Verify recommended_views have usable params
        for fa in report["field_analyses"]:
            for view in fa["recommended_views"]:
                assert "type" in view
                assert "params" in view

    def test_compose_story_from_latex(self, tmp_path):
        from viznoir.anim.compositor import render_story_layout
        from viznoir.anim.latex import render_latex

        eq = render_latex(r"\nabla \cdot \mathbf{u} = 0", color="00D4AA")
        result = render_story_layout([eq], ["Continuity equation"], width=800, height=400)
        assert result.size == (800, 400)

        path = tmp_path / "story.png"
        result.save(str(path))
        assert path.exists()

    def test_full_pipeline_analyze_then_compose(self, tmp_path):
        """Full pipeline: analyze VTK data → compose story with LaTeX equations."""
        from viznoir.anim.compositor import render_story_layout
        from viznoir.anim.latex import render_latex
        from viznoir.engine.analysis import analyze_dataset

        # Step 1: Analyze
        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(-8, 8, -8, 8, -8, 8)
        src.Update()
        report = analyze_dataset(src.GetOutput())

        # Step 2: Get suggested equation
        assert len(report["suggested_equations"]) >= 1
        eq_info = report["suggested_equations"][0]
        eq_img = render_latex(eq_info["latex"], color="00D4AA")
        assert eq_img.width > 0

        # Step 3: Compose story layout
        result = render_story_layout(
            [eq_img],
            [eq_info["name"]],
            title=f"Domain: {report['summary']['domain_guess']}",
            width=1920,
            height=1080,
        )
        assert result.size == (1920, 1080)

        # Step 4: Save
        path = tmp_path / "full_pipeline.png"
        result.save(str(path))
        assert path.exists()
        assert path.stat().st_size > 1000  # Non-trivial image

    def test_timeline_scene_lookup(self):
        """Verify timeline scene lookup works for video composition."""
        from viznoir.anim.timeline import Scene, Timeline

        scenes = [
            Scene(asset_indices=[0], duration=2.0, transition="fade_in"),
            Scene(asset_indices=[1], duration=3.0, transition="dissolve"),
            Scene(asset_indices=[0, 1], duration=2.0, transition="fade_in"),
        ]
        tl = Timeline(scenes, fps=30)

        assert tl.total_duration == 7.0
        assert tl.frame_count == 210

        # Scene boundaries
        idx, local_t = tl.scene_at(0.0)
        assert idx == 0

        idx, local_t = tl.scene_at(2.5)
        assert idx == 1

        idx, local_t = tl.scene_at(6.0)
        assert idx == 2

    def test_cross_field_analysis_with_correlated_fields(self):
        """Verify cross-field correlation detection with synthetic multi-field data."""
        import numpy as np
        from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

        from viznoir.engine.analysis import analyze_dataset

        src = vtk.vtkRTAnalyticSource()
        src.SetWholeExtent(-8, 8, -8, 8, -8, 8)
        src.Update()
        ds = src.GetOutput()

        # Add pressure field (anti-correlated with RTData)
        rtdata = vtk_to_numpy(ds.GetPointData().GetArray("RTData"))
        pressure = rtdata * -0.5 + np.random.normal(0, 10, size=rtdata.shape)
        p_arr = numpy_to_vtk(pressure.astype(np.float64))
        p_arr.SetName("p")
        ds.GetPointData().AddArray(p_arr)

        report = analyze_dataset(ds)

        assert len(report["field_analyses"]) >= 2
        assert len(report["cross_field_insights"]) >= 1
        # Should detect anti-correlation
        corrs = [i["correlation"] for i in report["cross_field_insights"]]
        assert any(c < -0.5 for c in corrs), "Expected negative correlation between RTData and p"

    def test_transitions_produce_valid_images(self):
        """Verify transitions produce valid RGBA images."""
        from PIL import Image

        from viznoir.anim.transitions import dissolve, fade_in, wipe

        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

        # fade_in at t=0.5
        result = fade_in(img, 0.5)
        assert result.size == (100, 100)
        assert result.mode == "RGBA"

        # dissolve between two images
        img2 = Image.new("RGBA", (100, 100), (0, 0, 255, 255))
        result = dissolve(img, img2, 0.5)
        assert result.size == (100, 100)

        # wipe
        result = wipe(img, img2, 0.5, "left")
        assert result.size == (100, 100)
