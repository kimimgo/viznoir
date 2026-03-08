# Science Storyteller v2 — Physics-Aware Analysis Pipeline

## Problem

v0.5.0 `analyze_dataset()` is broken by design:
- Outputs trivial statistics (min/max/mean) — no physics insight
- `suggested_equations`: hardcoded NS/Bernoulli regardless of simulation type
- `physics_context`: "Relatively uniform distribution" — useless
- `compose_assets`: pretty layout of garbage data

An engineer running lid-driven cavity at Re=100 gets the same output as someone doing heat transfer. No understanding of WHY the simulation was set up, WHAT the results mean, or HOW to interpret the flow topology.

## Design Decision

**viznoir = data extraction engine, LLM = physics reasoning.**

viznoir is an MCP server — the LLM client does the interpretation. Instead of hardcoding physics knowledge, viznoir extracts comprehensive, structured, quantitative data that enables an LLM to construct physics-based narratives.

## Architecture

```
VTK data ──→ L2: FieldTopologyAnalyzer (universal VTK)
         │     ├─ vortex detection (Q-criterion)
         │     ├─ critical points (stagnation, separation)
         │     ├─ centerline profiles (auto line probe)
         │     └─ gradient analysis
         │
Case dir ──→ L3: CaseContextParser (solver-specific, extensible)
               ├─ boundary conditions
               ├─ transport properties → derived quantities (Re, Ma)
               ├─ solver settings
               └─ mesh quality
                        ↓
               StructuredReport (JSON) → LLM builds the story
```

## Level 2: Field Topology (Universal)

Works with ANY VTK dataset that has velocity/pressure fields.

### Extraction Methods

| Item | VTK Method | Requirement |
|------|-----------|-------------|
| Vortex detection | `vtkGradientFilter` → Q-criterion, vorticity | velocity field |
| Vortex center/strength | Q > threshold → `vtkConnectivityFilter` → centroid | velocity field |
| Rotation direction | vorticity z-component sign | velocity field |
| Stagnation points | \|U\| < ε → point extraction | velocity field |
| Centerline profiles | `vtkLineSource` + `vtkProbeFilter` | any field |
| Pressure gradient | `vtkGradientFilter(p)` | pressure field |
| Symmetry detection | cross-centerline correlation | any field |

### Data Model

```python
@dataclass
class Vortex:
    center: list[float]       # [x, y] or [x, y, z]
    strength: float           # |ω| at center
    rotation: str             # "clockwise" / "counter-clockwise"
    radius: float | None      # approximate extent

@dataclass
class CriticalPoint:
    position: list[float]
    type: str                 # "stagnation", "separation", "reattachment"
    velocity_magnitude: float

@dataclass
class LineProfile:
    name: str                 # "vertical_x0.5"
    start: list[float]
    end: list[float]
    coordinates: list[float]
    fields: dict[str, list[float]]

@dataclass
class FieldTopology:
    field_name: str
    vortices: list[Vortex]
    critical_points: list[CriticalPoint]
    centerline_profiles: list[LineProfile]
    gradient_stats: dict[str, Any]
    field_range: dict[str, float]       # absorbs L1 stats
    spatial_distribution: str | None    # "symmetric", "asymmetric", etc.
```

## Level 3: Case Context (Extensible)

### CaseContext Contract

New solver parsers MUST populate this schema:

```python
@dataclass
class BoundaryCondition:
    patch_name: str
    field: str
    type: str                 # "fixedValue", "noSlip", "zeroGradient"
    value: Any | None

@dataclass
class TransportProperty:
    name: str                 # "nu", "mu", "rho"
    value: float
    unit: str | None

@dataclass
class SolverInfo:
    name: str                 # "icoFoam", "simpleFoam"
    algorithm: str | None     # "SIMPLE", "PISO"
    turbulence_model: str | None
    steady: bool | None

@dataclass
class MeshQuality:
    cell_count: int
    point_count: int
    cell_types: dict[str, int]
    bounding_box: tuple[list[float], list[float]]
    max_aspect_ratio: float | None
    max_non_orthogonality: float | None
    max_skewness: float | None

@dataclass
class DerivedQuantity:
    name: str                 # "Re", "Ma", "Pr"
    value: float
    formula: str
    inputs: dict[str, float]

@dataclass
class CaseContext:
    solver: SolverInfo | None
    boundary_conditions: list[BoundaryCondition]
    transport_properties: list[TransportProperty]
    mesh_quality: MeshQuality
    derived_quantities: list[DerivedQuantity]
    dimensions: int
    time_steps: list[float] | None
    raw_metadata: dict[str, Any]
```

### Required vs Optional Fields

| Field | Required | Reason |
|-------|----------|--------|
| `boundary_conditions` | **Required** | Can't explain "why this setup" without BC |
| `mesh_quality` | **Required** | Baseline for result trustworthiness |
| `transport_properties` | Recommended | Needed for Re, Ma, etc. |
| `solver` | Recommended | What assumptions (steady/transient, turbulence) |
| `derived_quantities` | Auto-computed | From transport + geometry |
| `dimensions` | **Required** | 2D vs 3D changes interpretation entirely |
| `time_steps` | Conditional | Transient only |
| `raw_metadata` | Free-form | Solver-specific extras for LLM |

### Parser Protocol

```python
class ContextParser(Protocol):
    def can_parse(self, path: str) -> bool: ...
    def parse(self, path: str) -> CaseContext: ...
```

### Coverage by Format

| Format | L1 Stats | L2 Topology | L3 Context |
|--------|----------|-------------|------------|
| OpenFOAM (.foam) | Full | Full | **Full** |
| VTK (.vtu/.vti) | Full | Full | None (null) |
| VTK multiblock (.vtm) | Full | Full | Block names only |
| CGNS | Full | Full | Partial |
| Exodus | Full | Full | Partial |
| STL/PLY/OBJ | None | None | None |

v0.6.0 scope: OpenFOAM parser only. Others via ContextParser extensions.

## MCP Tool Interface

### New: `inspect_physics`

```python
inspect_physics(
    file_path: str,
    case_dir: str | None = None,
    fields: list[str] | None = None,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> {
    "field_topologies": [FieldTopology, ...],
    "case_context": CaseContext | None,
    "case_context_hint": str | None,
    "extraction_time_ms": float,
}
```

### Deprecated: `analyze_data`

Existing `analyze_data` remains as deprecated wrapper. Removed in v0.7.0.

### Deleted from analysis.py

- `_EXACT_FIELD_MAP` (hardcoded field→physics mapping)
- `suggested_equations` (hardcoded NS/Bernoulli)
- `physics_context` (useless string)
- `_classify_field()` (pattern-matching inference)

Kept: `stats` → absorbed into `FieldTopology.field_range`

## File Structure

```
src/viznoir/
├── engine/
│   ├── topology.py          # NEW: L2 FieldTopology extraction (universal VTK)
│   └── analysis.py          # deprecated, thin wrapper
├── context/                 # NEW: L3 case context module
│   ├── __init__.py
│   ├── models.py            # CaseContext, BoundaryCondition, etc.
│   ├── parser.py            # ContextParser protocol + registry
│   ├── openfoam.py          # OpenFOAMContextParser
│   └── generic.py           # GenericContextParser (mesh quality only)
├── tools/
│   ├── analyze.py           # deprecated
│   └── inspect_physics.py   # NEW: inspect_physics MCP tool
```

## Example Output: Cavity Re=100

```json
{
  "field_topologies": [
    {
      "field_name": "U",
      "vortices": [
        {"center": [0.52, 0.76], "strength": 0.034, "rotation": "clockwise", "radius": 0.35},
        {"center": [0.08, 0.07], "strength": 0.002, "rotation": "counter-clockwise", "radius": 0.05}
      ],
      "critical_points": [
        {"position": [0.99, 0.99], "type": "stagnation", "velocity_magnitude": 0.001}
      ],
      "centerline_profiles": [
        {"name": "vertical_x0.5", "start": [0.5, 0, 0], "end": [0.5, 1, 0],
         "coordinates": [0.0, 0.05, 0.1, ...],
         "fields": {"Ux": [0.0, -0.02, ...], "Uy": [0.0, 0.01, ...]}}
      ],
      "gradient_stats": {"mean_magnitude": 0.15, "max_magnitude": 2.3, "dominant_direction": [0.1, 0.9, 0.0]},
      "field_range": {"min": 0.0, "max": 1.0, "mean": 0.12, "std": 0.18},
      "spatial_distribution": "asymmetric"
    }
  ],
  "case_context": {
    "solver": {"name": "icoFoam", "algorithm": "PISO", "turbulence_model": "laminar", "steady": false},
    "boundary_conditions": [
      {"patch_name": "movingWall", "field": "U", "type": "fixedValue", "value": [1, 0, 0]},
      {"patch_name": "fixedWalls", "field": "U", "type": "noSlip", "value": null},
      {"patch_name": "frontAndBack", "field": "U", "type": "empty", "value": null}
    ],
    "transport_properties": [{"name": "nu", "value": 0.01, "unit": "m^2/s"}],
    "mesh_quality": {"cell_count": 40000, "point_count": 40401, "cell_types": {"hexahedron": 40000},
                     "bounding_box": [[0,0,0],[1,1,0.1]], "max_aspect_ratio": 1.0,
                     "max_non_orthogonality": 0.0, "max_skewness": 0.0},
    "derived_quantities": [
      {"name": "Re", "value": 100.0, "formula": "U_ref * L_ref / nu",
       "inputs": {"U_ref": 1.0, "L_ref": 1.0, "nu": 0.01}}
    ],
    "dimensions": 2,
    "time_steps": [0.0, 0.005, 0.01, 0.5],
    "raw_metadata": {"deltaT": 0.005, "endTime": 0.5, "writeInterval": 0.1}
  },
  "case_context_hint": null,
  "extraction_time_ms": 45.2
}
```

With this data, an LLM can construct:
> "lid-driven cavity, Re=100 (icoFoam, PISO, laminar). Top wall moves at U=(1,0,0), other walls no-slip, 2D (empty front/back). Primary clockwise vortex detected at (0.52, 0.76) with strength 0.034 — compare Ghia et al. benchmark center (0.5313, 0.5625). Secondary counter-clockwise vortex at bottom-left (0.08, 0.07) confirms expected corner recirculation. Mesh: 40k hex cells, orthogonal, adequate for Re=100."
