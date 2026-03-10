"""OpenFOAM context parser — regex-based parsing of OpenFOAM dict files."""

from __future__ import annotations

import math
import re
from pathlib import Path

from viznoir.context.models import (
    BoundaryCondition,
    CaseContext,
    DerivedQuantity,
    MeshQuality,
    SolverInfo,
    TransportProperty,
)


class OpenFOAMContextParser:
    """Parser for OpenFOAM case directories."""

    def can_parse(self, path: str) -> bool:
        """Detect OpenFOAM case: requires system/controlDict."""
        p = Path(path)
        return (p / "system" / "controlDict").is_file()

    def parse_dataset(self, dataset: object) -> CaseContext:
        """Not used for OpenFOAM — use parse_case_dir instead."""
        raise NotImplementedError(
            "OpenFOAMContextParser requires a case directory, not a VTK dataset. Use parse_case_dir() instead."
        )

    def parse_case_dir(self, case_dir: str) -> CaseContext:
        """Extract full CaseContext from an OpenFOAM case directory."""
        root = Path(case_dir)

        # Parse controlDict → solver info
        solver = self._parse_control_dict(root / "system" / "controlDict")

        # Parse transport properties → nu, rho, etc.
        transport = self._parse_transport_properties(root / "constant" / "transportProperties")

        # Parse boundary condition files in 0/
        bcs = self._parse_boundary_files(root / "0")

        # Compute derived quantities (Re)
        derived = self._compute_derived(transport, bcs)

        # Minimal mesh quality (no VTK dataset available from case dir alone)
        mq = MeshQuality(
            cell_count=0,
            point_count=0,
            cell_types={},
            bounding_box=[[0, 0, 0], [0, 0, 0]],
        )

        return CaseContext(
            mesh_quality=mq,
            boundary_conditions=bcs,
            transport_properties=transport,
            solver=solver,
            derived_quantities=derived,
        )

    def _parse_control_dict(self, path: Path) -> SolverInfo | None:
        """Extract solver info from system/controlDict."""
        if not path.is_file():
            return None

        text = path.read_text(errors="replace")

        # application → solver name
        m = re.search(r"^\s*application\s+(\w+)\s*;", text, re.MULTILINE)
        name = m.group(1) if m else "unknown"

        # Detect steady vs transient from solver name
        steady_solvers = {"simpleFoam", "steadyState", "potentialFoam", "laplacianFoam"}
        steady = name in steady_solvers

        # Detect algorithm from solver name
        algorithm = None
        if "pimple" in name.lower() or "Pimple" in name:
            algorithm = "PIMPLE"
        elif "piso" in name.lower() or name in {"icoFoam", "pisoFoam"}:
            algorithm = "PISO"
        elif "simple" in name.lower() or name in {"simpleFoam"}:
            algorithm = "SIMPLE"

        return SolverInfo(name=name, algorithm=algorithm, steady=steady)

    def _parse_transport_properties(self, path: Path) -> list[TransportProperty]:
        """Extract transport properties from constant/transportProperties."""
        if not path.is_file():
            return []

        text = path.read_text(errors="replace")
        props: list[TransportProperty] = []

        # Pattern: property_name [dims] value;
        pattern = r"^\s*(\w+)\s+\[[\d\s\-]+\]\s+([\d.eE\+\-]+)\s*;"
        for m in re.finditer(pattern, text, re.MULTILINE):
            name = m.group(1)
            value = float(m.group(2))
            props.append(TransportProperty(name=name, value=value))

        return props

    def _parse_boundary_files(self, zero_dir: Path) -> list[BoundaryCondition]:
        """Parse all boundary condition files in 0/ directory."""
        if not zero_dir.is_dir():
            return []

        _skip_suffixes = {".orig", ".bak", ".old", ".swp", ".swo", "~"}
        bcs: list[BoundaryCondition] = []
        for field_file in sorted(zero_dir.iterdir()):
            if not field_file.is_file():
                continue
            if any(field_file.name.endswith(s) for s in _skip_suffixes):
                continue
            if field_file.name.startswith("."):
                continue
            field_name = field_file.name
            bcs.extend(self._parse_single_boundary_file(field_file, field_name))

        return bcs

    def _parse_single_boundary_file(self, path: Path, field_name: str) -> list[BoundaryCondition]:
        """Parse a single OpenFOAM boundary condition file."""
        text = path.read_text(errors="replace")
        bcs: list[BoundaryCondition] = []

        # Find boundaryField block
        bf_match = re.search(r"boundaryField\s*\{", text)
        if not bf_match:
            return []

        bf_text = text[bf_match.end() :]

        # Parse each patch block: patchName { type ...; value ...; }
        patch_pattern = r"(\w+)\s*\{([^}]*)\}"
        for m in re.finditer(patch_pattern, bf_text):
            patch_name = m.group(1)
            block = m.group(2)

            # Extract type
            type_match = re.search(r"type\s+(\w+)\s*;", block)
            if not type_match:
                continue
            bc_type = type_match.group(1)

            # Extract value
            value_match = re.search(r"value\s+(.*?)\s*;", block)
            value = None
            if value_match:
                value = _parse_openfoam_value(value_match.group(1).strip())

            bcs.append(
                BoundaryCondition(
                    patch_name=patch_name,
                    field=field_name,
                    type=bc_type,
                    value=value,
                )
            )

        return bcs

    def _compute_derived(
        self,
        transport: list[TransportProperty],
        bcs: list[BoundaryCondition],
    ) -> list[DerivedQuantity]:
        """Compute derived quantities (e.g., Reynolds number)."""
        derived: list[DerivedQuantity] = []

        # Find nu
        nu_prop = next((tp for tp in transport if tp.name == "nu"), None)
        if nu_prop is None:
            return derived

        nu = nu_prop.value

        # Find reference velocity from fixedValue BC on U
        u_ref = 0.0
        for bc in bcs:
            if bc.field == "U" and bc.type == "fixedValue" and bc.value is not None:
                if isinstance(bc.value, list):
                    u_ref = max(u_ref, math.sqrt(sum(v**2 for v in bc.value)))
                elif isinstance(bc.value, (int, float)):
                    u_ref = max(u_ref, abs(bc.value))

        if u_ref > 0 and nu > 0:
            # Use reference velocity as characteristic length proxy:
            # For cavity, L_ref = U_ref * nu gives Re = U_ref * L_ref / nu
            # Simplified: Re = U_ref / nu (assuming L_ref = 1 when not known from mesh)
            # Actually standard: Re = U * L / nu. Without mesh, assume L = 1.
            l_ref = 1.0
            re_value = u_ref * l_ref / nu
            derived.append(
                DerivedQuantity(
                    name="Re",
                    value=re_value,
                    formula="U_ref * L_ref / nu",
                    inputs={"U_ref": u_ref, "L_ref": l_ref, "nu": nu},
                )
            )

        return derived


def _parse_openfoam_value(text: str) -> float | list[float] | str:
    """Parse an OpenFOAM value string.

    Handles:
    - Scalar: "0.01" → 0.01
    - Vector: "(1 0 0)" → [1.0, 0.0, 0.0]
    - Uniform scalar: "uniform 0" → 0.0
    - Uniform vector: "uniform (1 0 0)" → [1.0, 0.0, 0.0]
    """
    text = text.strip()

    # Strip "uniform" prefix
    if text.startswith("uniform"):
        text = text[len("uniform") :].strip()

    # Vector: (x y z)
    vec_match = re.match(r"\(\s*([\d.eE\+\-]+)\s+([\d.eE\+\-]+)\s+([\d.eE\+\-]+)\s*\)", text)
    if vec_match:
        return [float(vec_match.group(i)) for i in range(1, 4)]

    # Scalar
    try:
        return float(text)
    except ValueError:
        return text
