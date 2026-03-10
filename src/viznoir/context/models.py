"""L3 CaseContext data models for solver-specific metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BoundaryCondition:
    """A boundary condition on a specific patch for a specific field."""

    patch_name: str
    field: str
    type: str
    value: Any = None


@dataclass
class TransportProperty:
    """A transport property (e.g., viscosity, density)."""

    name: str
    value: float
    unit: str | None = None


@dataclass
class SolverInfo:
    """Solver metadata (name, algorithm, turbulence model)."""

    name: str
    algorithm: str | None = None
    turbulence_model: str | None = None
    steady: bool = True


@dataclass
class MeshQuality:
    """Mesh quality metrics extracted from the dataset."""

    cell_count: int
    point_count: int
    cell_types: dict[str, int]
    bounding_box: list[list[float]]
    max_aspect_ratio: float | None = None
    max_non_orthogonality: float | None = None
    max_skewness: float | None = None

    @property
    def dimensions(self) -> int:
        """Infer 2D vs 3D from bounding box thickness."""
        bb = self.bounding_box
        extents = [abs(bb[1][i] - bb[0][i]) for i in range(3)]
        max_extent = max(extents)
        if max_extent == 0:
            return 3
        min_extent = min(extents)
        if min_extent / max_extent < 0.01:
            return 2
        return 3


@dataclass
class DerivedQuantity:
    """A derived dimensionless quantity (Re, Ma, Pr, etc.)."""

    name: str
    value: float
    formula: str
    inputs: dict[str, float]


@dataclass
class CaseContext:
    """Complete case context from solver-specific metadata."""

    mesh_quality: MeshQuality
    boundary_conditions: list[BoundaryCondition] = field(default_factory=list)
    transport_properties: list[TransportProperty] = field(default_factory=list)
    solver: SolverInfo | None = None
    derived_quantities: list[DerivedQuantity] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)
