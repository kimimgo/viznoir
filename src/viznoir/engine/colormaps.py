"""Colormap presets for VTK rendering — replaces ParaView's ApplyPreset()."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk

# ---------------------------------------------------------------------------
# Colormap definitions: list of (position, R, G, B) tuples, position in [0, 1]
# Sampled from matplotlib/ParaView reference implementations.
# ---------------------------------------------------------------------------

_COOL_TO_WARM: list[tuple[float, float, float, float]] = [
    (0.0, 0.230, 0.299, 0.754),
    (0.5, 0.865, 0.865, 0.865),
    (1.0, 0.706, 0.016, 0.150),
]

_VIRIDIS: list[tuple[float, float, float, float]] = [
    (0.00, 0.267, 0.004, 0.329),
    (0.25, 0.283, 0.141, 0.458),
    (0.50, 0.127, 0.566, 0.551),
    (0.75, 0.544, 0.773, 0.247),
    (1.00, 0.993, 0.906, 0.144),
]

_PLASMA: list[tuple[float, float, float, float]] = [
    (0.00, 0.050, 0.030, 0.528),
    (0.25, 0.494, 0.012, 0.658),
    (0.50, 0.798, 0.280, 0.470),
    (0.75, 0.973, 0.585, 0.254),
    (1.00, 0.940, 0.975, 0.131),
]

_INFERNO: list[tuple[float, float, float, float]] = [
    (0.00, 0.001, 0.000, 0.014),
    (0.25, 0.320, 0.059, 0.404),
    (0.50, 0.735, 0.216, 0.330),
    (0.75, 0.993, 0.553, 0.235),
    (1.00, 0.988, 0.998, 0.645),
]

_JET: list[tuple[float, float, float, float]] = [
    (0.000, 0.0, 0.0, 0.5),
    (0.125, 0.0, 0.0, 1.0),
    (0.375, 0.0, 1.0, 1.0),
    (0.625, 1.0, 1.0, 0.0),
    (0.875, 1.0, 0.0, 0.0),
    (1.000, 0.5, 0.0, 0.0),
]

_RAINBOW_DESATURATED: list[tuple[float, float, float, float]] = [
    (0.0, 0.278, 0.278, 0.858),
    (0.143, 0.0, 0.0, 0.360),
    (0.285, 0.0, 1.0, 1.0),
    (0.429, 0.0, 0.501, 0.0),
    (0.571, 1.0, 1.0, 0.0),
    (0.714, 1.0, 0.380, 0.0),
    (0.857, 0.420, 0.0, 0.0),
    (1.0, 0.878, 0.302, 0.302),
]

_BLUES: list[tuple[float, float, float, float]] = [
    (0.0, 0.969, 0.984, 1.000),
    (0.25, 0.741, 0.843, 0.906),
    (0.50, 0.420, 0.682, 0.839),
    (0.75, 0.192, 0.510, 0.741),
    (1.0, 0.031, 0.318, 0.612),
]

_RDYLGN: list[tuple[float, float, float, float]] = [
    (0.0, 0.647, 0.000, 0.149),
    (0.25, 0.992, 0.553, 0.235),
    (0.50, 1.000, 1.000, 0.749),
    (0.75, 0.651, 0.851, 0.416),
    (1.0, 0.000, 0.408, 0.216),
]

_COOLWARM: list[tuple[float, float, float, float]] = _COOL_TO_WARM  # alias

_BLACK_BODY_RADIATION: list[tuple[float, float, float, float]] = [
    (0.0, 0.0, 0.0, 0.0),
    (0.4, 0.902, 0.0, 0.0),
    (0.8, 0.902, 0.902, 0.0),
    (1.0, 1.0, 1.0, 1.0),
]

_GRAYSCALE: list[tuple[float, float, float, float]] = [
    (0.0, 0.0, 0.0, 0.0),
    (1.0, 1.0, 1.0, 1.0),
]

_TURBO: list[tuple[float, float, float, float]] = [
    (0.000, 0.190, 0.072, 0.232),
    (0.100, 0.292, 0.381, 0.897),
    (0.200, 0.129, 0.666, 0.998),
    (0.300, 0.063, 0.876, 0.821),
    (0.400, 0.337, 0.970, 0.545),
    (0.500, 0.660, 0.992, 0.277),
    (0.600, 0.912, 0.892, 0.100),
    (0.700, 0.996, 0.690, 0.012),
    (0.800, 0.974, 0.434, 0.005),
    (0.900, 0.836, 0.180, 0.055),
    (1.000, 0.530, 0.023, 0.062),
]

_TERRAIN: list[tuple[float, float, float, float]] = [
    (0.000, 0.200, 0.290, 0.580),
    (0.150, 0.000, 0.600, 0.500),
    (0.250, 0.000, 0.800, 0.400),
    (0.500, 0.930, 0.930, 0.600),
    (0.750, 0.530, 0.320, 0.100),
    (0.850, 0.600, 0.530, 0.400),
    (1.000, 1.000, 1.000, 1.000),
]

_MAGMA: list[tuple[float, float, float, float]] = [
    (0.000, 0.001, 0.000, 0.014),
    (0.250, 0.283, 0.088, 0.463),
    (0.500, 0.716, 0.215, 0.475),
    (0.750, 0.993, 0.536, 0.382),
    (1.000, 0.987, 0.991, 0.750),
]

_CIVIDIS: list[tuple[float, float, float, float]] = [
    (0.000, 0.000, 0.135, 0.305),
    (0.250, 0.302, 0.329, 0.420),
    (0.500, 0.529, 0.529, 0.451),
    (0.750, 0.781, 0.725, 0.380),
    (1.000, 0.995, 0.910, 0.212),
]

_TWILIGHT: list[tuple[float, float, float, float]] = [
    (0.000, 0.886, 0.851, 0.886),
    (0.125, 0.620, 0.541, 0.788),
    (0.250, 0.353, 0.282, 0.663),
    (0.375, 0.184, 0.149, 0.373),
    (0.500, 0.114, 0.114, 0.114),
    (0.625, 0.318, 0.149, 0.133),
    (0.750, 0.631, 0.263, 0.227),
    (0.875, 0.835, 0.533, 0.530),
    (1.000, 0.886, 0.851, 0.886),
]

_BLUE_TO_RED_RAINBOW: list[tuple[float, float, float, float]] = [
    (0.000, 0.000, 0.000, 1.000),
    (0.250, 0.000, 1.000, 1.000),
    (0.500, 0.000, 1.000, 0.000),
    (0.750, 1.000, 1.000, 0.000),
    (1.000, 1.000, 0.000, 0.000),
]

_X_RAY: list[tuple[float, float, float, float]] = [
    (0.000, 1.000, 1.000, 1.000),
    (0.333, 0.600, 0.600, 0.600),
    (0.667, 0.300, 0.300, 0.300),
    (1.000, 0.000, 0.000, 0.000),
]

# ---------------------------------------------------------------------------
# Registry — name → control points
# Names are case-insensitive, with aliases for common spellings.
# ---------------------------------------------------------------------------

COLORMAP_REGISTRY: dict[str, list[tuple[float, float, float, float]]] = {
    "cool to warm": _COOL_TO_WARM,
    "coolwarm": _COOL_TO_WARM,
    "viridis": _VIRIDIS,
    "plasma": _PLASMA,
    "inferno": _INFERNO,
    "jet": _JET,
    "rainbow desaturated": _RAINBOW_DESATURATED,
    "blues": _BLUES,
    "rdylgn": _RDYLGN,
    "black-body radiation": _BLACK_BODY_RADIATION,
    "grayscale": _GRAYSCALE,
    "turbo": _TURBO,
    "terrain": _TERRAIN,
    "magma": _MAGMA,
    "cividis": _CIVIDIS,
    "twilight": _TWILIGHT,
    "blue to red rainbow": _BLUE_TO_RED_RAINBOW,
    "x ray": _X_RAY,
}


def build_lut(
    name: str,
    scalar_range: tuple[float, float] = (0.0, 1.0),
    log_scale: bool = False,
    nan_color: tuple[float, float, float] = (0.5, 0.5, 0.5),
    above_range_color: tuple[float, float, float] | None = None,
    below_range_color: tuple[float, float, float] | None = None,
) -> vtk.vtkScalarsToColors:
    """Build a VTK lookup table from a named colormap preset.

    Args:
        name: Colormap name (case-insensitive).
        scalar_range: (min, max) data range for mapping.
        log_scale: Use logarithmic scale.
        nan_color: RGB color for NaN values.
        above_range_color: RGB for values above max. None = clamp.
        below_range_color: RGB for values below min. None = clamp.

    Returns:
        Configured vtkColorTransferFunction.
    """
    import vtk

    key = name.lower().strip()
    points = COLORMAP_REGISTRY.get(key)
    if points is None:
        # Fallback to Cool to Warm
        points = _COOL_TO_WARM

    lo, hi = scalar_range
    ctf = vtk.vtkColorTransferFunction()

    if log_scale and lo > 0:
        ctf.SetScaleToLog10()
    else:
        ctf.SetScaleToLinear()

    for pos, r, g, b in points:
        ctf.AddRGBPoint(lo + pos * (hi - lo), r, g, b)

    ctf.SetNanColor(nan_color[0], nan_color[1], nan_color[2])

    if above_range_color is not None:
        ctf.SetAboveRangeColor(*above_range_color, 1.0)
        ctf.SetUseAboveRangeColor(True)
    else:
        ctf.SetUseAboveRangeColor(False)

    if below_range_color is not None:
        ctf.SetBelowRangeColor(*below_range_color, 1.0)
        ctf.SetUseBelowRangeColor(True)
    else:
        ctf.SetUseBelowRangeColor(False)

    return ctf


def list_colormaps() -> list[str]:
    """Return sorted list of available colormap names."""
    return sorted(set(COLORMAP_REGISTRY.keys()))
