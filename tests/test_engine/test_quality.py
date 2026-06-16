"""Tests for engine/quality.py — render quality metrics.

Pure-numpy image quality measures (contrast, edge entropy, field coverage) that
feed the autoexp modify->render->measure loop. Synthetic numpy images only, so
these run in CI without GPU/VTK rendering.
"""

from __future__ import annotations

import numpy as np
import pytest

from viznoir.engine.quality import (
    QualityMetrics,
    contrast,
    edge_entropy,
    field_coverage,
    measure_quality,
)


# --------------------------------------------------------------------------- #
# synthetic image helpers
# --------------------------------------------------------------------------- #
def _solid(h: int, w: int, color) -> np.ndarray:
    img = np.empty((h, w, 3), dtype=np.uint8)
    img[:] = np.asarray(color, dtype=np.uint8)
    return img


def _checkerboard(h: int, w: int, square: int = 8) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    mask = ((yy // square) + (xx // square)) % 2 == 0
    img[mask] = 255
    return img


def _noise(h: int, w: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


# --------------------------------------------------------------------------- #
# contrast
# --------------------------------------------------------------------------- #
class TestContrast:
    def test_flat_image_is_zero(self):
        assert contrast(_solid(32, 32, (128, 128, 128))) == pytest.approx(0.0, abs=1e-6)

    def test_checkerboard_is_high(self):
        assert contrast(_checkerboard(64, 64)) > 0.4

    def test_in_unit_range(self):
        assert 0.0 <= contrast(_checkerboard(64, 64)) <= 1.0
        assert 0.0 <= contrast(_noise(64, 64)) <= 1.0

    def test_ordering_flat_gradient_checker(self):
        flat = contrast(_solid(32, 32, (120, 120, 120)))
        ramp = np.stack([np.tile(np.linspace(100, 140, 32, dtype=np.uint8), (32, 1))] * 3, axis=-1)
        gradient = contrast(ramp)
        checker = contrast(_checkerboard(32, 32))
        assert flat < gradient < checker


# --------------------------------------------------------------------------- #
# edge entropy
# --------------------------------------------------------------------------- #
class TestEdgeEntropy:
    def test_flat_image_is_zero(self):
        assert edge_entropy(_solid(32, 32, (80, 80, 80))) == pytest.approx(0.0, abs=1e-9)

    def test_edges_are_positive(self):
        assert edge_entropy(_checkerboard(64, 64, square=8)) > 0.0

    def test_noise_richer_than_checkerboard(self):
        # noise spreads gradient magnitudes across many bins -> higher entropy
        assert edge_entropy(_noise(64, 64)) > edge_entropy(_checkerboard(64, 64, square=8))

    def test_non_negative(self):
        assert edge_entropy(_noise(48, 48)) >= 0.0


# --------------------------------------------------------------------------- #
# field coverage
# --------------------------------------------------------------------------- #
class TestFieldCoverage:
    def test_all_background_is_zero(self):
        bg = (255, 255, 255)
        assert field_coverage(_solid(32, 32, bg), background_color=bg) == pytest.approx(0.0, abs=1e-6)

    def test_full_object_is_one(self):
        img = _solid(32, 32, (10, 20, 30))
        assert field_coverage(img, background_color=(255, 255, 255)) == pytest.approx(1.0, abs=1e-6)

    def test_half_coverage(self):
        bg = (255, 255, 255)
        img = _solid(32, 32, bg)
        img[:16, :] = (10, 10, 10)
        assert field_coverage(img, background_color=bg) == pytest.approx(0.5, abs=0.02)

    def test_auto_background_from_corners(self):
        bg = (0, 0, 0)
        img = _solid(40, 40, bg)
        img[10:30, 10:30] = (200, 200, 200)
        assert field_coverage(img) == pytest.approx((20 * 20) / (40 * 40), abs=0.02)


# --------------------------------------------------------------------------- #
# input coercion / validation
# --------------------------------------------------------------------------- #
class TestInputHandling:
    def test_accepts_grayscale(self):
        gray = np.full((16, 16), 100, dtype=np.uint8)
        assert contrast(gray) == pytest.approx(0.0, abs=1e-6)

    def test_accepts_rgba(self):
        rgba = np.zeros((16, 16, 4), dtype=np.uint8)
        rgba[..., 3] = 255
        # alpha channel must be ignored
        assert contrast(rgba) == pytest.approx(0.0, abs=1e-6)

    def test_rejects_bad_shape(self):
        with pytest.raises(ValueError):
            contrast(np.zeros((4,), dtype=np.uint8))


# --------------------------------------------------------------------------- #
# measure_quality aggregate
# --------------------------------------------------------------------------- #
class TestMeasureQuality:
    def test_returns_metrics_in_range(self):
        m = measure_quality(_checkerboard(64, 64))
        assert isinstance(m, QualityMetrics)
        assert 0.0 <= m.contrast <= 1.0
        assert m.edge_entropy >= 0.0
        assert 0.0 <= m.field_coverage <= 1.0
        assert 0.0 <= m.score <= 1.0

    def test_blank_scores_lower_than_rich(self):
        blank = measure_quality(_solid(64, 64, (255, 255, 255)), background_color=(255, 255, 255))
        rich = measure_quality(_noise(64, 64))
        assert rich.score > blank.score

    def test_blank_score_is_near_zero(self):
        blank = measure_quality(_solid(64, 64, (255, 255, 255)), background_color=(255, 255, 255))
        assert blank.score == pytest.approx(0.0, abs=1e-6)

    def test_to_dict_keys(self):
        d = measure_quality(_checkerboard(32, 32)).to_dict()
        assert set(d) >= {"contrast", "edge_entropy", "field_coverage", "score"}
        assert all(isinstance(v, float) for v in d.values())


# --------------------------------------------------------------------------- #
# load_png round-trip (uses VTK PNG writer/reader — no GPU)
# --------------------------------------------------------------------------- #
class TestLoadPng:
    def test_round_trip(self, tmp_path):
        from viznoir.engine.quality import load_png

        vtk = pytest.importorskip("vtk")
        from vtk.util.numpy_support import numpy_to_vtk

        h, w = 6, 4
        src = _checkerboard(h, w, square=2)
        # write via VTK (origin bottom-left -> flip rows so the file matches src)
        img = vtk.vtkImageData()
        img.SetDimensions(w, h, 1)
        flat = src[::-1].reshape(-1, 3).astype(np.uint8)
        scalars = numpy_to_vtk(flat, deep=True)
        scalars.SetNumberOfComponents(3)
        img.GetPointData().SetScalars(scalars)
        path = tmp_path / "tile.png"
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputData(img)
        writer.Write()

        out = load_png(str(path))
        assert out.shape == (h, w, 3)
        assert out.dtype == np.uint8
        np.testing.assert_array_equal(out, src)
