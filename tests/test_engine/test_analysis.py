"""Tests for engine/analysis.py — data insight extraction."""

from __future__ import annotations

import pytest
import vtk


def _make_wavelet():
    """Create a wavelet dataset for testing."""
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-16, 16, -16, 16, -16, 16)
    src.Update()
    return src.GetOutput()


class TestComputeFieldStats:
    def test_returns_dict_with_required_keys(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        stats = compute_field_stats(ds, "RTData")
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "std" in stats

    def test_min_less_than_max(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        stats = compute_field_stats(ds, "RTData")
        assert stats["min"] < stats["max"]

    def test_mean_between_min_and_max(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        stats = compute_field_stats(ds, "RTData")
        assert stats["min"] <= stats["mean"] <= stats["max"]

    def test_unknown_field_raises(self):
        from viznoir.engine.analysis import compute_field_stats
        ds = _make_wavelet()
        with pytest.raises(KeyError):
            compute_field_stats(ds, "NonExistentField")


class TestDetectAnomalies:
    def test_returns_list(self):
        from viznoir.engine.analysis import detect_anomalies
        ds = _make_wavelet()
        anomalies = detect_anomalies(ds, "RTData")
        assert isinstance(anomalies, list)

    def test_anomalies_have_location_and_value(self):
        from viznoir.engine.analysis import detect_anomalies
        ds = _make_wavelet()
        anomalies = detect_anomalies(ds, "RTData")
        if anomalies:
            a = anomalies[0]
            assert "location" in a
            assert "value" in a
            assert "type" in a
            assert len(a["location"]) == 3

    def test_finds_extrema_in_wavelet(self):
        from viznoir.engine.analysis import detect_anomalies
        ds = _make_wavelet()
        anomalies = detect_anomalies(ds, "RTData")
        assert len(anomalies) >= 1


class TestInferPhysicsContext:
    def test_known_field_returns_context(self):
        from viznoir.engine.analysis import infer_physics_context
        ctx = infer_physics_context("Pressure", {"min": -100, "max": 500, "mean": 200, "std": 120})
        assert isinstance(ctx, str)
        assert len(ctx) > 10

    def test_unknown_field_returns_generic(self):
        from viznoir.engine.analysis import infer_physics_context
        ctx = infer_physics_context("RTData", {"min": 0, "max": 300, "mean": 150, "std": 50})
        assert isinstance(ctx, str)


class TestRecommendViews:
    def test_returns_list_of_dicts(self):
        from viznoir.engine.analysis import recommend_views
        anomalies = [{"type": "local_extremum", "location": [3.0, 0, 0], "value": 500}]
        views = recommend_views("Pressure", anomalies, bounds=[[-10, 10], [-5, 5], [-5, 5]])
        assert isinstance(views, list)
        if views:
            v = views[0]
            assert "type" in v
            assert "params" in v
            assert "reason" in v

    def test_anomaly_generates_slice_view(self):
        from viznoir.engine.analysis import recommend_views
        anomalies = [{"type": "local_extremum", "location": [3.0, 0, 0], "value": 500}]
        views = recommend_views("Pressure", anomalies, bounds=[[-10, 10], [-5, 5], [-5, 5]])
        slice_views = [v for v in views if v["type"] == "slice"]
        assert len(slice_views) >= 1


class TestFullAnalysis:
    def test_analyze_dataset_returns_report(self):
        from viznoir.engine.analysis import analyze_dataset
        ds = _make_wavelet()
        report = analyze_dataset(ds)
        assert "summary" in report
        assert "field_analyses" in report
        assert report["summary"]["num_points"] > 0

    def test_analyze_dataset_with_domain_hint(self):
        from viznoir.engine.analysis import analyze_dataset
        ds = _make_wavelet()
        report = analyze_dataset(ds, domain="cfd")
        assert report["summary"]["domain_guess"] == "cfd"

    def test_analyze_dataset_with_focus(self):
        from viznoir.engine.analysis import analyze_dataset
        ds = _make_wavelet()
        report = analyze_dataset(ds, focus="RTData")
        assert len(report["field_analyses"]) == 1
        assert report["field_analyses"][0]["name"] == "RTData"
