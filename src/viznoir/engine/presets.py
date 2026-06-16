"""Domain render-tuning presets for autoexp — physics-appropriate render candidates.

Distinct from ``presets/registry.py`` (case-level scene presets): these are
field-level render-parameter candidates (colormaps tuned to the field's physics)
that the autoexp loop tries and scores. Encodes the same physics the guard checks
(#58): signed fields get diverging colormaps, magnitudes get sequential ones.
"""

from __future__ import annotations

from dataclasses import dataclass

# Physics-appropriate colormap families (names per engine.colormaps COLORMAP_REGISTRY).
DIVERGING_COLORMAPS = ["coolwarm", "rdylgn"]
SEQUENTIAL_COLORMAPS = ["viridis", "plasma", "inferno", "turbo"]


@dataclass(frozen=True)
class RenderPreset:
    """A candidate render tweak the autoexp loop can try."""

    name: str
    colormap: str
    description: str

    def as_params(self) -> dict[str, str]:
        """Render-parameter override this preset applies."""
        return {"colormap": self.colormap}


def is_signed_field(field_min: float | None, field_max: float | None, is_magnitude: bool = False) -> bool:
    """True when a scalar field crosses zero (and is not a magnitude)."""
    if is_magnitude or field_min is None or field_max is None:
        return False
    return field_min < 0.0 < field_max


def candidates_for(field_min: float | None, field_max: float | None, is_magnitude: bool = False) -> list[RenderPreset]:
    """Physics-appropriate render presets to try for a field's statistics.

    Signed fields (crossing zero) get diverging colormaps; magnitudes and
    one-sided fields get sequential colormaps.
    """
    if is_signed_field(field_min, field_max, is_magnitude):
        family, kind = DIVERGING_COLORMAPS, "diverging"
    else:
        family, kind = SEQUENTIAL_COLORMAPS, "sequential"
    return [RenderPreset(name=c, colormap=c, description=f"{kind} {c}") for c in family]
