"""Mechanical domain detection from file metadata.

Simple heuristic: file extension + field names → domain string.
Complex inference is delegated to LLM via sampling.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

# File extensions strongly associated with a domain
_CFD_EXTENSIONS = {".foam", ".cas", ".cgns", ".msh", ".ccm"}
_FEA_EXTENSIONS = {".inp", ".op2", ".bdf", ".dat"}
_SPH_EXTENSIONS = {".bi4"}

# Field names that indicate a domain (case-insensitive matching)
_CFD_FIELDS = {"p", "u", "k", "epsilon", "omega", "nut", "alphat", "p_rgh", "alpha.water"}
_FEA_FIELDS = {"displacement", "von_mises_stress", "stress", "strain", "reaction_force"}
_SPH_FIELDS = {"type", "rhop"}  # "Velocity" is ambiguous; needs "Type" to confirm SPH


def detect_domain(metadata: dict[str, Any]) -> str:
    """Detect simulation domain from inspect_data metadata.

    Returns: "cfd", "fea", "sph", or "generic".
    """
    file_path = metadata.get("file_path", "")
    ext = PurePosixPath(file_path).suffix.lower()
    arrays = metadata.get("arrays", {})
    field_names = {name.lower() for name in arrays}

    # 1. Extension-based detection (strongest signal)
    if ext in _CFD_EXTENSIONS:
        return "cfd"
    if ext in _FEA_EXTENSIONS:
        return "fea"
    if ext in _SPH_EXTENSIONS:
        return "sph"

    # 2. Field-based detection
    if field_names & _SPH_FIELDS and "velocity" in field_names:
        return "sph"
    if field_names & _FEA_FIELDS:
        return "fea"
    if field_names & _CFD_FIELDS:
        return "cfd"

    return "generic"
