"""GenericContextParser — extracts mesh quality from any VTK dataset."""

from __future__ import annotations

from viznoir.context.models import CaseContext, MeshQuality


class GenericContextParser:
    """Fallback parser: extracts mesh quality from any VTK dataset."""

    def can_parse(self, path: str) -> bool:
        return True

    def parse_dataset(self, dataset: object) -> CaseContext:
        """Extract basic mesh quality metrics from a VTK dataset."""
        cell_count = dataset.GetNumberOfCells()  # type: ignore[attr-defined]
        point_count = dataset.GetNumberOfPoints()  # type: ignore[attr-defined]

        # Cell types
        cell_types: dict[str, int] = {}
        for i in range(cell_count):
            ct = dataset.GetCellType(i)  # type: ignore[attr-defined]
            name = _vtk_cell_type_name(ct)
            cell_types[name] = cell_types.get(name, 0) + 1

        # Bounding box
        bounds = list(dataset.GetBounds())  # type: ignore[attr-defined]
        bb = [
            [bounds[0], bounds[2], bounds[4]],
            [bounds[1], bounds[3], bounds[5]],
        ]

        mq = MeshQuality(
            cell_count=cell_count,
            point_count=point_count,
            cell_types=cell_types,
            bounding_box=bb,
        )

        return CaseContext(mesh_quality=mq)


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
