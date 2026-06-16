"""Physics-aware render rules — catch hallucinated visualization choices.

Each rule inspects a :class:`GuardContext` (field statistics + render settings)
and returns a :class:`RuleResult` when it *applies*, or ``None`` when it does
not. Rules are pure logic (no VTK), so they run anywhere.

Rules implemented (see issue #58):

* pressure (signed) -> diverging, zero-centered colormap
* velocity magnitude -> sequential, non-negative range
* temperature below absolute zero -> warn
* empty isosurface -> fail, suggest the data range
* camera outside the data bounds -> warn, reset recommended
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    """Verdict severity, ordered PASS < WARN < FAIL (see ``validator._ORDER``)."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class GuardContext:
    """Everything a rule needs: field statistics + the render's choices."""

    field_name: str | None = None
    field_min: float | None = None
    field_max: float | None = None
    is_magnitude: bool = False
    colormap: str | None = None
    scalar_range: tuple[float, float] | None = None
    camera_position: tuple[float, float, float] | None = None
    # (xmin, xmax, ymin, ymax, zmin, zmax)
    data_bounds: tuple[float, float, float, float, float, float] | None = None
    filter_type: str | None = None
    isosurface_cell_count: int | None = None


@dataclass
class RuleResult:
    """Outcome of one rule."""

    rule: str
    status: Status
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "rule": self.rule,
            "status": self.status.value,
            "message": self.message,
            "suggestion": self.suggestion,
        }


# Colormaps suited to signed / zero-centered fields (names per COLORMAP_REGISTRY).
_DIVERGING = {"coolwarm", "cool to warm", "rdylgn"}


def _norm(name: str | None) -> str:
    return (name or "").strip().lower()


def _is_pressure(name: str | None) -> bool:
    n = _norm(name)
    return n in {"p", "p_rgh", "pressure"} or "pressure" in n


def _is_temperature(name: str | None) -> bool:
    n = _norm(name)
    return n in {"t", "temp", "temperature"} or "temperature" in n or n.startswith("temp")


def _is_velocity_magnitude(name: str | None) -> bool:
    n = _norm(name)
    if n in {"speed", "umag", "vmag", "|u|", "velocity magnitude"}:
        return True
    return "magnitude" in n or ("mag" in n and ("u" in n or "vel" in n))


def _is_diverging(colormap: str | None) -> bool:
    return _norm(colormap) in _DIVERGING


def check_pressure_colormap(ctx: GuardContext) -> RuleResult | None:
    """Signed pressure should use a diverging colormap centered at zero."""
    if not _is_pressure(ctx.field_name):
        return None
    if ctx.field_min is None or ctx.field_max is None:
        return None
    # Only applies when the field actually crosses zero.
    if not (ctx.field_min < 0.0 < ctx.field_max):
        return None

    name = "pressure_diverging_colormap"
    if not _is_diverging(ctx.colormap):
        return RuleResult(
            name,
            Status.WARN,
            f"pressure '{ctx.field_name}' is signed but colormap '{ctx.colormap}' is not "
            "diverging — use a diverging zero-centered map (e.g. coolwarm) so the zero "
            "crossing is visible.",
            suggestion="colormap=coolwarm",
        )
    if ctx.scalar_range is not None:
        lo, hi = ctx.scalar_range
        span = max(abs(lo), abs(hi), 1e-12)
        if abs(lo + hi) > 0.05 * 2 * span:  # not symmetric about zero
            sym = max(abs(lo), abs(hi))
            return RuleResult(
                name,
                Status.WARN,
                f"diverging colormap on signed pressure but range {ctx.scalar_range} is not "
                "centered at zero — the white midpoint won't sit at 0.",
                suggestion=f"scalar_range=({-sym}, {sym})",
            )
    return RuleResult(name, Status.PASS, "pressure uses a diverging zero-centered colormap.")


def check_magnitude_colormap(ctx: GuardContext) -> RuleResult | None:
    """A magnitude (>= 0) should use a sequential colormap and a non-negative range."""
    if not (ctx.is_magnitude or _is_velocity_magnitude(ctx.field_name)):
        return None

    name = "magnitude_sequential_colormap"
    if _is_diverging(ctx.colormap):
        return RuleResult(
            name,
            Status.WARN,
            f"'{ctx.field_name}' is a non-negative magnitude but colormap '{ctx.colormap}' is "
            "diverging — half its range is wasted; use a sequential map (e.g. viridis).",
            suggestion="colormap=viridis",
        )
    if ctx.scalar_range is not None and ctx.scalar_range[0] < 0.0:
        return RuleResult(
            name,
            Status.WARN,
            f"magnitude '{ctx.field_name}' is >= 0 but scalar_range starts at {ctx.scalar_range[0]} < 0.",
            suggestion=f"scalar_range=(0, {ctx.scalar_range[1]})",
        )
    return RuleResult(name, Status.PASS, "magnitude uses a sequential non-negative mapping.")


def check_temperature_below_zero(ctx: GuardContext) -> RuleResult | None:
    """Absolute temperature below 0 K is unphysical (or the units are not Kelvin)."""
    if not _is_temperature(ctx.field_name):
        return None
    if ctx.field_min is None:
        return None

    name = "temperature_below_absolute_zero"
    if ctx.field_min < 0.0:
        return RuleResult(
            name,
            Status.WARN,
            f"temperature '{ctx.field_name}' min {ctx.field_min} < 0 — below absolute zero if "
            "this is Kelvin. Check the units (Celsius?) before trusting the colors.",
        )
    return RuleResult(name, Status.PASS, "temperature is above absolute zero.")


def check_empty_isosurface(ctx: GuardContext) -> RuleResult | None:
    """An isosurface with no geometry means the isovalue was outside the data range."""
    if _norm(ctx.filter_type) not in {"contour", "isosurface", "iso"}:
        return None
    if ctx.isosurface_cell_count is None:
        return None

    name = "empty_isosurface"
    if ctx.isosurface_cell_count == 0:
        rng = ""
        if ctx.field_min is not None and ctx.field_max is not None:
            rng = f" valid range for '{ctx.field_name}' is [{ctx.field_min}, {ctx.field_max}]"
        return RuleResult(
            name,
            Status.FAIL,
            "isosurface produced no geometry — the isovalue is likely outside the data range.",
            suggestion=f"pick an isovalue inside the data range.{rng}".strip(),
        )
    return RuleResult(name, Status.PASS, "isosurface produced geometry.")


def check_camera_bounds(ctx: GuardContext) -> RuleResult | None:
    """Camera far outside (or inside) the data bounds hides the object — reset recommended."""
    if ctx.camera_position is None or ctx.data_bounds is None:
        return None

    name = "camera_outside_bounds"
    xmin, xmax, ymin, ymax, zmin, zmax = ctx.data_bounds
    center = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
    diag = ((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2) ** 0.5
    if diag <= 0.0:
        return None
    dist = sum((c - p) ** 2 for c, p in zip(ctx.camera_position, center)) ** 0.5

    inside = (
        xmin <= ctx.camera_position[0] <= xmax
        and ymin <= ctx.camera_position[1] <= ymax
        and zmin <= ctx.camera_position[2] <= zmax
    )
    if inside:
        return RuleResult(
            name,
            Status.WARN,
            "camera is inside the data bounding box — the object will be clipped. Reset the camera.",
            suggestion="reset camera to frame the dataset.",
        )
    if dist > 100.0 * diag:
        return RuleResult(
            name,
            Status.WARN,
            f"camera is {dist / diag:.0f}x the dataset size away — the object is a speck. Reset the camera.",
            suggestion="reset camera to frame the dataset.",
        )
    return RuleResult(name, Status.PASS, "camera frames the dataset.")


# Order matters only for readability of the report.
ALL_RULES = [
    check_pressure_colormap,
    check_magnitude_colormap,
    check_temperature_below_zero,
    check_empty_isosurface,
    check_camera_bounds,
]
