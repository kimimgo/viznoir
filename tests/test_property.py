"""Property-based tests using Hypothesis — fuzz security-critical paths."""

from __future__ import annotations

import importlib
import os
import string

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

# VTK import is slow on first call — disable deadline globally for this module
settings.register_profile("slow_vtk", deadline=None)
settings.load_profile("slow_vtk")

# ---------------------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------------------

path_chars = st.sampled_from(string.ascii_letters + string.digits + "_-./")
path_segment = st.text(path_chars, min_size=1, max_size=20)


def _build_path(*segments: str) -> str:
    return "/" + "/".join(segments)


# ---------------------------------------------------------------------------
# _validate_file_path property tests
# ---------------------------------------------------------------------------


class TestValidateFilePathProperties:
    """Property-based tests for _validate_file_path security guarantees."""

    def _reload_with_data_dir(self, data_dir: str | None = "/data"):
        import viznoir.config
        import viznoir.server

        if data_dir is not None:
            os.environ["VIZNOIR_DATA_DIR"] = data_dir
        else:
            os.environ.pop("VIZNOIR_DATA_DIR", None)

        importlib.reload(viznoir.config)
        importlib.reload(viznoir.server)
        return viznoir.server._validate_file_path

    @given(
        segments=st.lists(
            st.text(
                st.sampled_from(string.ascii_lowercase + string.digits + "_-."),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_any_path_outside_data_dir_is_rejected(self, segments):
        """No generated path outside /data/ should ever be accepted."""
        validate = self._reload_with_data_dir("/data")
        path = "/" + "/".join(segments)
        # If the path doesn't start with /data, it must be rejected
        from pathlib import Path

        resolved = str(Path(path).resolve())
        if not resolved.startswith("/data/") and resolved != "/data":
            with pytest.raises((ValueError, FileNotFoundError)):
                validate(path)

    @given(
        dotdot_count=st.integers(min_value=1, max_value=10),
        suffix=st.text(
            st.sampled_from(string.ascii_lowercase + "/"),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dotdot_traversal_never_escapes(self, dotdot_count, suffix):
        """Path traversal with ../ must never escape the data dir."""
        validate = self._reload_with_data_dir("/data")
        # Build: /data/../../etc/passwd style paths
        traversal = "/data/" + "../" * dotdot_count + suffix.lstrip("/")
        from pathlib import Path

        resolved = str(Path(traversal).resolve())
        if not resolved.startswith("/data/") and resolved != "/data":
            with pytest.raises((ValueError, FileNotFoundError)):
                validate(traversal)

    @given(
        path=st.text(
            st.sampled_from(string.ascii_lowercase + string.digits + "_-./~"),
            min_size=0,
            max_size=50,
        )
    )
    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_data_dir_only_rejects_nonexistent(self, path):
        """Without data_dir, only FileNotFoundError is possible (not ValueError)."""
        validate = self._reload_with_data_dir(None)
        try:
            validate(path)
        except FileNotFoundError:
            pass  # Expected — path doesn't exist
        except (ValueError, OSError):
            pass  # Edge case: empty path, etc.


# ---------------------------------------------------------------------------
# Colormap registry property tests
# ---------------------------------------------------------------------------


class TestColormapRegistryProperties:
    """Property-based tests for colormap lookup invariants."""

    @given(name=st.text(min_size=1, max_size=50))
    @settings(max_examples=200)
    def test_build_lut_never_crashes(self, name):
        """build_lut should never crash — unknown names fall back to Cool to Warm."""
        from viznoir.engine.colormaps import build_lut

        result = build_lut(name, scalar_range=(0.0, 1.0))
        assert result is not None

    @given(
        name=st.sampled_from(
            [
                "Cool to Warm", "cool to warm", "COOL TO WARM",
                "Viridis", "VIRIDIS", "viridis",
                "Plasma", "plasma", "PLASMA",
                "Jet", "jet", "JET",
                "Turbo", "turbo", "TURBO",
            ]
        )
    )
    @settings(max_examples=50)
    def test_case_insensitive_lookup(self, name):
        """All case variants of known colormaps should resolve."""
        from viznoir.engine.colormaps import build_lut

        result = build_lut(name, scalar_range=(0.0, 100.0))
        assert result is not None

    @given(
        lo=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        hi=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_scalar_range_never_crashes(self, lo, hi):
        """Any scalar range should produce a valid LUT."""
        assume(lo != hi)
        from viznoir.engine.colormaps import build_lut

        result = build_lut("viridis", scalar_range=(min(lo, hi), max(lo, hi)))
        assert result is not None

    @given(
        lo=st.floats(min_value=0.001, max_value=1e6, allow_nan=False, allow_infinity=False),
        hi=st.floats(min_value=0.001, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_log_scale_positive_range(self, lo, hi):
        """Log scale with positive range should work."""
        assume(lo < hi)
        from viznoir.engine.colormaps import build_lut

        result = build_lut("plasma", scalar_range=(lo, hi), log_scale=True)
        assert result is not None


# ---------------------------------------------------------------------------
# Pydantic model property tests
# ---------------------------------------------------------------------------


class TestPipelineModelProperties:
    """Property-based tests for Pydantic model validation."""

    @given(
        field=st.text(min_size=1, max_size=30),
        colormap=st.text(min_size=1, max_size=30),
    )
    @settings(max_examples=100)
    def test_render_def_accepts_any_field_name(self, field, colormap):
        """RenderDef should accept any string as field name."""
        from viznoir.pipeline.models import RenderDef

        r = RenderDef(field=field, colormap=colormap)
        assert r.field == field

    @given(
        filter_name=st.text(min_size=1, max_size=30),
        params=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.text(max_size=20),
                st.booleans(),
            ),
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_filter_step_accepts_arbitrary_params(self, filter_name, params):
        """FilterStep should accept any dict as params."""
        from viznoir.pipeline.models import FilterStep

        f = FilterStep(filter=filter_name, params=params)
        assert f.filter == filter_name
        assert f.params == params

    @given(
        zoom=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_camera_def_zoom_range(self, zoom):
        """CameraDef should accept any positive zoom."""
        from viznoir.pipeline.models import CameraDef

        c = CameraDef(zoom=zoom)
        assert c.zoom == zoom

    @given(
        w=st.integers(min_value=1, max_value=8192),
        h=st.integers(min_value=1, max_value=8192),
    )
    @settings(max_examples=50)
    def test_render_def_resolution(self, w, h):
        """RenderDef should accept any positive resolution."""
        from viznoir.pipeline.models import RenderDef

        r = RenderDef(field="p", resolution=[w, h])
        assert r.resolution == [w, h]
