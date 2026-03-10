"""inspect_physics tool — structured physics data extraction for LLM storytelling.

Extracts L2 FieldTopology (vortex detection, critical points, centerline probes,
gradient stats) and L3 CaseContext (boundary conditions, transport properties,
solver info, mesh quality, derived quantities) from simulation datasets.
"""

from __future__ import annotations

import time
from typing import Any

from viznoir.context.generic import GenericContextParser
from viznoir.context.parser import get_default_registry
from viznoir.engine.readers import read_dataset
from viznoir.engine.topology import analyze_field_topology


async def inspect_physics_impl(
    file_path: str,
    *,
    case_dir: str | None = None,
    fields: list[str] | None = None,
    probe_lines: int = 3,
    vortex_threshold: float = 0.01,
) -> dict[str, Any]:
    """Extract structured physics data from a simulation dataset.

    Parameters
    ----------
    file_path : str
        Path to the simulation data file (VTK, OpenFOAM, etc.).
    case_dir : str | None
        OpenFOAM case directory for L3 context extraction.
        If None, only mesh quality (GenericParser) is provided.
    fields : list[str] | None
        Specific field names to analyze. None = all fields.
    probe_lines : int
        Number of auto-generated centerline probe lines (1-3).
    vortex_threshold : float
        Q-criterion threshold for vortex detection.

    Returns
    -------
    dict
        {field_topologies, case_context, case_context_hint, extraction_time_ms}
    """
    t0 = time.perf_counter()

    dataset = read_dataset(file_path)

    # Discover available fields from point and cell data
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    all_fields: list[str] = []
    for i in range(pd.GetNumberOfArrays()):
        name = pd.GetArrayName(i)
        if name:
            all_fields.append(name)
    for i in range(cd.GetNumberOfArrays()):
        name = cd.GetArrayName(i)
        if name and name not in all_fields:
            all_fields.append(name)

    if fields:
        all_fields = [f for f in all_fields if f in fields]

    # L2: Field topology analysis per field
    topologies: list[dict[str, Any]] = []
    for field_name in all_fields:
        topo = analyze_field_topology(
            dataset,
            field_name,
            probe_lines=probe_lines,
            vortex_threshold=vortex_threshold,
        )
        topologies.append(topo.to_dict())

    # L3: Case context
    hint: str | None = None
    if case_dir:
        registry = get_default_registry()
        parser = registry.get_parser(case_dir)
        if parser and hasattr(parser, "parse_case_dir"):
            ctx = parser.parse_case_dir(case_dir)
        else:
            ctx = GenericContextParser().parse_dataset(dataset)
            hint = "No solver-specific parser found for this case directory"
    else:
        ctx = GenericContextParser().parse_dataset(dataset)
        hint = "Provide case_dir for full solver metadata (boundary conditions, transport properties, solver info)"

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "field_topologies": topologies,
        "case_context": ctx.to_dict(),
        "case_context_hint": hint,
        "extraction_time_ms": round(elapsed_ms, 1),
    }
