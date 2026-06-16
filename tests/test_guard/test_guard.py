"""Tests for the guard/ module — physics-aware post-render validation.

The guard checks a render's *choices* (colormap, scalar range, camera) against
the physical field, catching agent hallucinations like a sequential colormap on
signed pressure or an isovalue outside the data range. Pure logic over a
GuardContext — no VTK, runs in CI.
"""

from __future__ import annotations

from viznoir.guard import GuardContext, Status, ValidationReport, validate
from viznoir.guard.rules import (
    check_camera_bounds,
    check_empty_isosurface,
    check_magnitude_colormap,
    check_pressure_colormap,
    check_temperature_below_zero,
)


# --------------------------------------------------------------------------- #
# pressure -> diverging, zero-centered
# --------------------------------------------------------------------------- #
class TestPressureColormap:
    def test_signed_pressure_sequential_warns(self):
        ctx = GuardContext(
            field_name="pressure",
            field_min=-50.0,
            field_max=80.0,
            colormap="viridis",
            scalar_range=(-50.0, 80.0),
        )
        r = check_pressure_colormap(ctx)
        assert r is not None and r.status is Status.WARN
        assert "diverging" in r.message.lower()

    def test_signed_pressure_diverging_centered_passes(self):
        ctx = GuardContext(
            field_name="p",
            field_min=-80.0,
            field_max=80.0,
            colormap="coolwarm",
            scalar_range=(-80.0, 80.0),
        )
        r = check_pressure_colormap(ctx)
        assert r is not None and r.status is Status.PASS

    def test_diverging_but_not_centered_warns(self):
        ctx = GuardContext(
            field_name="pressure",
            field_min=-50.0,
            field_max=80.0,
            colormap="coolwarm",
            scalar_range=(0.0, 80.0),
        )
        r = check_pressure_colormap(ctx)
        assert r is not None and r.status is Status.WARN
        assert "cent" in r.message.lower()

    def test_non_pressure_not_applicable(self):
        ctx = GuardContext(field_name="velocity", field_min=-1.0, field_max=1.0, colormap="viridis")
        assert check_pressure_colormap(ctx) is None

    def test_all_positive_pressure_not_applicable(self):
        # gauge pressure that never crosses zero doesn't require a diverging map
        ctx = GuardContext(field_name="pressure", field_min=10.0, field_max=90.0, colormap="viridis")
        assert check_pressure_colormap(ctx) is None


# --------------------------------------------------------------------------- #
# velocity magnitude -> sequential, non-negative
# --------------------------------------------------------------------------- #
class TestMagnitudeColormap:
    def test_magnitude_diverging_warns(self):
        ctx = GuardContext(
            field_name="U_magnitude",
            is_magnitude=True,
            field_min=0.0,
            field_max=5.0,
            colormap="coolwarm",
            scalar_range=(0.0, 5.0),
        )
        r = check_magnitude_colormap(ctx)
        assert r is not None and r.status is Status.WARN
        assert "sequential" in r.message.lower()

    def test_magnitude_sequential_passes(self):
        ctx = GuardContext(
            field_name="speed",
            is_magnitude=True,
            field_min=0.0,
            field_max=5.0,
            colormap="viridis",
            scalar_range=(0.0, 5.0),
        )
        r = check_magnitude_colormap(ctx)
        assert r is not None and r.status is Status.PASS

    def test_magnitude_negative_range_warns(self):
        ctx = GuardContext(
            field_name="speed",
            is_magnitude=True,
            field_min=0.0,
            field_max=5.0,
            colormap="viridis",
            scalar_range=(-1.0, 5.0),
        )
        r = check_magnitude_colormap(ctx)
        assert r is not None and r.status is Status.WARN

    def test_non_magnitude_not_applicable(self):
        ctx = GuardContext(field_name="pressure", field_min=-1.0, field_max=1.0, colormap="coolwarm")
        assert check_magnitude_colormap(ctx) is None


# --------------------------------------------------------------------------- #
# temperature < 0 K
# --------------------------------------------------------------------------- #
class TestTemperatureBelowZero:
    def test_negative_kelvin_warns(self):
        ctx = GuardContext(field_name="temperature", field_min=-10.0, field_max=300.0)
        r = check_temperature_below_zero(ctx)
        assert r is not None and r.status is Status.WARN

    def test_positive_temperature_passes(self):
        ctx = GuardContext(field_name="T", field_min=280.0, field_max=320.0)
        r = check_temperature_below_zero(ctx)
        assert r is not None and r.status is Status.PASS

    def test_non_temperature_not_applicable(self):
        ctx = GuardContext(field_name="pressure", field_min=-5.0, field_max=5.0)
        assert check_temperature_below_zero(ctx) is None


# --------------------------------------------------------------------------- #
# empty isosurface -> suggest data range
# --------------------------------------------------------------------------- #
class TestEmptyIsosurface:
    def test_empty_isosurface_fails_with_range(self):
        ctx = GuardContext(
            field_name="RTData",
            field_min=37.0,
            field_max=277.0,
            filter_type="contour",
            isosurface_cell_count=0,
        )
        r = check_empty_isosurface(ctx)
        assert r is not None and r.status is Status.FAIL
        assert r.suggestion is not None
        assert "37" in r.suggestion and "277" in r.suggestion

    def test_nonempty_isosurface_passes(self):
        ctx = GuardContext(filter_type="contour", isosurface_cell_count=1200)
        r = check_empty_isosurface(ctx)
        assert r is not None and r.status is Status.PASS

    def test_no_filter_not_applicable(self):
        assert check_empty_isosurface(GuardContext(field_name="p")) is None


# --------------------------------------------------------------------------- #
# camera outside bounds -> reset
# --------------------------------------------------------------------------- #
class TestCameraBounds:
    BOUNDS = (-10.0, 10.0, -10.0, 10.0, -10.0, 10.0)

    def test_reasonable_camera_passes(self):
        ctx = GuardContext(camera_position=(0.0, 0.0, 60.0), data_bounds=self.BOUNDS)
        r = check_camera_bounds(ctx)
        assert r is not None and r.status is Status.PASS

    def test_camera_far_away_warns(self):
        ctx = GuardContext(camera_position=(0.0, 0.0, 1.0e6), data_bounds=self.BOUNDS)
        r = check_camera_bounds(ctx)
        assert r is not None and r.status is Status.WARN

    def test_camera_inside_bounds_warns(self):
        ctx = GuardContext(camera_position=(0.0, 0.0, 0.0), data_bounds=self.BOUNDS)
        r = check_camera_bounds(ctx)
        assert r is not None and r.status is Status.WARN

    def test_missing_data_not_applicable(self):
        assert check_camera_bounds(GuardContext(camera_position=(0, 0, 1))) is None


# --------------------------------------------------------------------------- #
# validator aggregation
# --------------------------------------------------------------------------- #
class TestValidate:
    def test_clean_context_passes(self):
        ctx = GuardContext(
            field_name="speed",
            is_magnitude=True,
            field_min=0.0,
            field_max=5.0,
            colormap="viridis",
            scalar_range=(0.0, 5.0),
        )
        report = validate(ctx)
        assert isinstance(report, ValidationReport)
        assert report.verdict is Status.PASS

    def test_warn_dominates_pass(self):
        ctx = GuardContext(
            field_name="pressure",
            field_min=-50.0,
            field_max=80.0,
            colormap="viridis",
            scalar_range=(-50.0, 80.0),
        )
        report = validate(ctx)
        assert report.verdict is Status.WARN

    def test_fail_dominates(self):
        ctx = GuardContext(
            field_name="RTData",
            field_min=37.0,
            field_max=277.0,
            colormap="viridis",
            scalar_range=(37.0, 277.0),
            filter_type="contour",
            isosurface_cell_count=0,
        )
        report = validate(ctx)
        assert report.verdict is Status.FAIL

    def test_to_dict(self):
        ctx = GuardContext(
            field_name="pressure", field_min=-1.0, field_max=1.0, colormap="viridis", scalar_range=(-1.0, 1.0)
        )
        d = validate(ctx).to_dict()
        assert d["verdict"] == "warn"
        assert isinstance(d["results"], list) and len(d["results"]) >= 1
        assert {"rule", "status", "message"} <= set(d["results"][0])

    def test_results_only_include_applicable_rules(self):
        # a bare context with no field/render info triggers no rules
        report = validate(GuardContext())
        assert report.results == []
        assert report.verdict is Status.PASS
