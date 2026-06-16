"""Render quality metrics — contrast, edge entropy, field coverage.

Pure-numpy image-quality measures that judge whether a rendered frame is
*informative* (vs. blank, clipped, or empty). They feed the autoexp
modify->render->measure loop (``core/autoexp.py``): a higher score means keep
the change, a lower score means revert it.

No heavy dependencies — only numpy (always present via VTK). The metric
functions operate on a rendered image given as a numpy array:

* ``(H, W)``       — grayscale
* ``(H, W, 3)``    — RGB
* ``(H, W, 4)``    — RGBA (the alpha channel is ignored)

``load_png()`` converts a PNG file produced by the renderer into such an array.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Rec. 601 luma weights — perceptual luminance from linear RGB channels.
_LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float64)

# Score normalisation constants (see ``measure_quality``).
_RMS_CONTRAST_MAX = 0.5  # std of values in [0, 1] peaks at 0.5 (50/50 black/white)
_ENTROPY_BINS = 64
_ENTROPY_MAX = float(np.log2(_ENTROPY_BINS))  # max Shannon entropy for the histogram


@dataclass
class QualityMetrics:
    """Aggregate render-quality measurement.

    All fields are floats. ``contrast``/``field_coverage`` are in ``[0, 1]``;
    ``edge_entropy`` is in bits (``>= 0``); ``score`` is a normalised blend in
    ``[0, 1]`` where higher is a richer, more informative frame.
    """

    contrast: float
    edge_entropy: float
    field_coverage: float
    score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "contrast": self.contrast,
            "edge_entropy": self.edge_entropy,
            "field_coverage": self.field_coverage,
            "score": self.score,
        }


def _as_rgb(image: np.ndarray) -> np.ndarray:
    """Coerce an image to a float64 ``(H, W, 3)`` array, dropping any alpha."""
    arr = np.asarray(image)
    if arr.ndim == 2:
        rgb = np.repeat(arr[:, :, None].astype(np.float64), 3, axis=2)
    elif arr.ndim == 3 and arr.shape[2] in (3, 4):
        rgb = arr[..., :3].astype(np.float64)
    else:
        raise ValueError(f"expected (H,W), (H,W,3) or (H,W,4) image, got shape {arr.shape}")
    if rgb.size == 0:
        raise ValueError("image has no pixels")
    # Float images in [0, 1] are scaled up to the 0-255 range the metrics assume.
    if arr.dtype.kind == "f" and float(np.nanmax(arr)) <= 1.0:
        rgb = rgb * 255.0
    return rgb


def _as_luminance(image: np.ndarray) -> np.ndarray:
    """Coerce an image to a float64 luminance plane in ``[0, 255]``."""
    return _as_rgb(image) @ _LUMA


def contrast(image: np.ndarray) -> float:
    """RMS contrast in ``[0, 1]`` — the standard deviation of normalised luminance.

    A flat frame is ``0``; a balanced black/white pattern approaches ``0.5``.
    """
    luma = _as_luminance(image) / 255.0
    return float(np.std(luma))


def edge_entropy(image: np.ndarray, bins: int = _ENTROPY_BINS) -> float:
    """Shannon entropy (bits) of the gradient-magnitude histogram.

    Measures how *varied* the edge structure is. A blank frame has a single
    (zero) gradient bin -> ``0`` bits; a detailed render spreads gradient
    magnitudes across many bins -> higher entropy.
    """
    luma = _as_luminance(image)
    gy, gx = np.gradient(luma)
    mag = np.hypot(gx, gy)
    peak = float(mag.max())
    if peak <= 1e-9:
        return 0.0
    hist, _ = np.histogram(mag, bins=bins, range=(0.0, peak))
    counts = hist.astype(np.float64)
    total = counts.sum()
    if total <= 0:
        return 0.0
    probs = counts / total
    nz = probs[probs > 0]
    return float(-(nz * np.log2(nz)).sum())


def field_coverage(
    image: np.ndarray,
    background_color: tuple[float, float, float] | None = None,
    threshold: float = 12.0,
) -> float:
    """Fraction of pixels that differ from the background — i.e. the rendered object.

    Args:
        image: rendered image array.
        background_color: RGB of the background. If ``None``, it is inferred as
            the per-channel median of the four corner pixels.
        threshold: euclidean RGB distance (0-255) above which a pixel counts as
            foreground.

    Returns:
        Coverage fraction in ``[0, 1]``.
    """
    rgb = _as_rgb(image)
    if background_color is None:
        corners = np.stack([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
        bg = np.median(corners, axis=0)
    else:
        bg = np.asarray(background_color, dtype=np.float64)[:3]
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=-1))
    return float((dist > threshold).mean())


def measure_quality(
    image: np.ndarray,
    background_color: tuple[float, float, float] | None = None,
) -> QualityMetrics:
    """Compute all metrics and a normalised ``[0, 1]`` quality score.

    The score weights detail (contrast + edge entropy) over raw coverage, since
    a richly-detailed frame is more informative than a flatly-filled one:
    ``0.4 * contrast_norm + 0.4 * entropy_norm + 0.2 * field_coverage``.
    """
    c = contrast(image)
    e = edge_entropy(image)
    cov = field_coverage(image, background_color=background_color)

    c_norm = min(c / _RMS_CONTRAST_MAX, 1.0)
    e_norm = min(e / _ENTROPY_MAX, 1.0) if _ENTROPY_MAX > 0 else 0.0
    score = 0.4 * c_norm + 0.4 * e_norm + 0.2 * cov
    return QualityMetrics(contrast=c, edge_entropy=e, field_coverage=cov, score=float(score))


def load_png(path: str) -> np.ndarray:
    """Load a PNG file into an ``(H, W, 3)`` uint8 array (lazy VTK import).

    VTK stores images bottom-left-origin, so rows are flipped to match the
    natural top-left-origin convention the metric helpers expect.
    """
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    reader = vtk.vtkPNGReader()
    reader.SetFileName(str(path))
    reader.Update()
    img = reader.GetOutput()
    w, h, _ = img.GetDimensions()
    scalars = img.GetPointData().GetScalars()
    if scalars is None:
        raise ValueError(f"could not read PNG: {path}")
    arr = vtk_to_numpy(scalars).reshape(h, w, -1)[::-1]
    if arr.shape[2] == 1:
        arr = np.repeat(arr, 3, axis=2)
    return np.ascontiguousarray(arr[..., :3]).astype(np.uint8)
