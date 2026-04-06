"""CGNS context parser — extracts solver metadata from CGNS-derived VTK datasets."""

from __future__ import annotations

from viznoir.context.models import BoundaryCondition, CaseContext, MeshQuality, SolverInfo


class CGNSContextParser:
    """Parser for CGNS files loaded as VTK datasets."""

    def can_parse(self, path: str) -> bool:
        """Return True if the file has a .cgns extension (lowercase only)."""
        return path.endswith(".cgns")

    def parse_dataset(self, dataset: object) -> CaseContext:
        """Extract CaseContext from a VTK dataset loaded from a CGNS file.

        Handles both flat datasets (vtkUnstructuredGrid, vtkStructuredGrid)
        and composite datasets (vtkMultiBlockDataSet).
        """
        class_name: str = type(dataset).__name__

        if "MultiBlock" in class_name:
            return self._parse_multiblock(dataset)
        return self._parse_flat(dataset)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_flat(self, dataset: object) -> CaseContext:
        """Parse a single-block VTK dataset."""
        cell_count: int = dataset.GetNumberOfCells()  # type: ignore[attr-defined]
        point_count: int = dataset.GetNumberOfPoints()  # type: ignore[attr-defined]

        cell_types = _extract_cell_types(dataset, cell_count)
        bounds = list(dataset.GetBounds())  # type: ignore[attr-defined]
        bb = [[bounds[0], bounds[2], bounds[4]], [bounds[1], bounds[3], bounds[5]]]

        mq = MeshQuality(
            cell_count=cell_count,
            point_count=point_count,
            cell_types=cell_types,
            bounding_box=bb,
        )

        topology = _detect_topology(dataset)
        solver = SolverInfo(name="CGNS", algorithm=topology)

        return CaseContext(mesh_quality=mq, solver=solver)

    def _parse_multiblock(self, mb: object) -> CaseContext:
        """Parse a vtkMultiBlockDataSet: aggregate mesh quality + extract block names."""
        n_blocks: int = mb.GetNumberOfBlocks()  # type: ignore[attr-defined]

        total_cells = 0
        total_points = 0
        cell_types: dict[str, int] = {}
        bcs: list[BoundaryCondition] = []
        topology: str | None = None

        # Tight bounds tracking
        global_min = [float("inf")] * 3
        global_max = [float("-inf")] * 3

        for i in range(n_blocks):
            block = mb.GetBlock(i)  # type: ignore[attr-defined]
            if block is None:
                continue

            # Block name → BoundaryCondition
            block_name: str | None = None
            meta = mb.GetMetaData(i)  # type: ignore[attr-defined]
            if meta is not None:
                try:
                    import vtkmodules.vtkCommonDataModel as vtk_dm  # noqa: N813

                    if meta.Has(vtk_dm.vtkCompositeDataSet.NAME()):
                        block_name = meta.Get(vtk_dm.vtkCompositeDataSet.NAME())
                except Exception:  # noqa: BLE001
                    pass

            if block_name:
                bcs.append(BoundaryCondition(patch_name=block_name, field="block", type="zone"))

            # Aggregate cell / point counts
            block_cells: int = block.GetNumberOfCells()
            block_points: int = block.GetNumberOfPoints()
            total_cells += block_cells
            total_points += block_points
            _merge_cell_types(cell_types, _extract_cell_types(block, block_cells))

            # Bounds
            b = list(block.GetBounds())
            for dim in range(3):
                global_min[dim] = min(global_min[dim], b[dim * 2])
                global_max[dim] = max(global_max[dim], b[dim * 2 + 1])

            # Topology: use first non-None block
            if topology is None:
                topology = _detect_topology(block)

        # Guard against empty dataset
        if total_cells == 0:
            global_min = [0.0, 0.0, 0.0]
            global_max = [0.0, 0.0, 0.0]

        bb = [list(global_min), list(global_max)]
        mq = MeshQuality(
            cell_count=total_cells,
            point_count=total_points,
            cell_types=cell_types,
            bounding_box=bb,
        )
        solver = SolverInfo(name="CGNS", algorithm=topology)
        return CaseContext(mesh_quality=mq, boundary_conditions=bcs, solver=solver)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _vtk_cell_type_name(cell_type: int) -> str:
    """Map VTK cell type integer to human-readable name."""
    names = {
        3: "line",
        5: "triangle",
        8: "pixel",
        9: "quad",
        10: "tetra",
        11: "voxel",
        12: "hexahedron",
        13: "wedge",
        14: "pyramid",
    }
    return names.get(cell_type, f"type_{cell_type}")


def _extract_cell_types(dataset: object, cell_count: int) -> dict[str, int]:
    """Count each cell type in a VTK dataset."""
    cell_types: dict[str, int] = {}
    for i in range(cell_count):
        ct: int = dataset.GetCellType(i)  # type: ignore[attr-defined]
        name = _vtk_cell_type_name(ct)
        cell_types[name] = cell_types.get(name, 0) + 1
    return cell_types


def _merge_cell_types(target: dict[str, int], source: dict[str, int]) -> None:
    """Merge source cell type counts into target in-place."""
    for k, v in source.items():
        target[k] = target.get(k, 0) + v


def _detect_topology(dataset: object) -> str:
    """Detect whether a dataset is structured or unstructured."""
    class_name: str = type(dataset).__name__
    if "StructuredGrid" in class_name or "ImageData" in class_name or "RectilinearGrid" in class_name:
        return "structured"
    return "unstructured"
