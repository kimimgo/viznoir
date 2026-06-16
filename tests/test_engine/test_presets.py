"""Tests for engine/presets.py — physics-appropriate render candidates for autoexp."""

from __future__ import annotations

from viznoir.engine.presets import (
    DIVERGING_COLORMAPS,
    SEQUENTIAL_COLORMAPS,
    RenderPreset,
    candidates_for,
    is_signed_field,
)


class TestIsSignedField:
    def test_crosses_zero(self):
        assert is_signed_field(-5.0, 5.0) is True

    def test_one_sided_positive(self):
        assert is_signed_field(2.0, 9.0) is False

    def test_magnitude_never_signed(self):
        assert is_signed_field(-5.0, 5.0, is_magnitude=True) is False

    def test_missing_stats(self):
        assert is_signed_field(None, 5.0) is False


class TestCandidatesFor:
    def test_signed_field_gets_diverging(self):
        cands = candidates_for(-50.0, 80.0)
        assert [c.colormap for c in cands] == DIVERGING_COLORMAPS

    def test_magnitude_gets_sequential(self):
        cands = candidates_for(0.0, 5.0, is_magnitude=True)
        assert [c.colormap for c in cands] == SEQUENTIAL_COLORMAPS

    def test_one_sided_gets_sequential(self):
        cands = candidates_for(10.0, 90.0)
        assert [c.colormap for c in cands] == SEQUENTIAL_COLORMAPS

    def test_returns_render_presets(self):
        cands = candidates_for(-1.0, 1.0)
        assert all(isinstance(c, RenderPreset) for c in cands)
        assert cands[0].as_params() == {"colormap": cands[0].colormap}
