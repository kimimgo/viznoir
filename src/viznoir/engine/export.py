"""Data inspection, statistics extraction, and file export."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import vtk

__all__ = [
    "inspect_dataset",
    "extract_stats",
    "extract_data",
    "export_file",
    "export_gltf",
    "get_leaf_block",
]


# ---------------------------------------------------------------------------
# inspect_dataset — comprehensive metadata
# ---------------------------------------------------------------------------


def inspect_dataset(dataset: vtk.vtkDataObject) -> dict[str, Any]:
    """Inspect a VTK dataset and return comprehensive metadata.

    Args:
        dataset: Any VTK data object.

    Returns:
        Dict with keys: type, num_points, num_cells, bounds, point_arrays,
        cell_arrays, field_arrays, multiblock (nested block structure).
    """
    import vtk

    result: dict[str, Any] = {
        "type": type(dataset).__name__,
        "num_points": 0,
        "num_cells": 0,
        "bounds": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        "point_arrays": [],
        "cell_arrays": [],
        "field_arrays": [],
        "multiblock": None,
    }

    if isinstance(dataset, vtk.vtkMultiBlockDataSet):
        result["multiblock"] = _inspect_multiblock(dataset)
        leaf = get_leaf_block(dataset)
        if leaf is not None:
            _fill_dataset_info(result, leaf)
    elif isinstance(dataset, vtk.vtkDataSet):
        _fill_dataset_info(result, dataset)

    return result


def _fill_dataset_info(result: dict[str, Any], ds: vtk.vtkDataSet) -> None:
    """Fill result dict with dataset info."""
    result["num_points"] = ds.GetNumberOfPoints()
    result["num_cells"] = ds.GetNumberOfCells()
    result["bounds"] = ds.GetBounds()
    result["point_arrays"] = _array_info_list(ds.GetPointData())
    result["cell_arrays"] = _array_info_list(ds.GetCellData())
    result["field_arrays"] = _array_info_list(ds.GetFieldData())


def _array_info_list(attrs: vtk.vtkDataSetAttributes | None) -> list[dict[str, Any]]:
    """Get info for all arrays in a vtkDataSetAttributes."""
    if attrs is None:
        return []

    result: list[dict[str, Any]] = []
    for i in range(attrs.GetNumberOfArrays()):
        name = attrs.GetArrayName(i)
        if name is None:
            continue
        arr = attrs.GetArray(i)
        if arr is None:
            continue
        result.append(
            {
                "name": name,
                "components": arr.GetNumberOfComponents(),
                "tuples": arr.GetNumberOfTuples(),
                "range": [arr.GetRange(c) for c in range(arr.GetNumberOfComponents())],
                "type": arr.GetDataTypeAsString(),
            }
        )

    return result


def _inspect_multiblock(mb: vtk.vtkMultiBlockDataSet) -> list[dict[str, Any]]:
    """Recursively inspect a multiblock dataset structure."""
    import vtk

    blocks: list[dict[str, Any]] = []
    for i in range(mb.GetNumberOfBlocks()):
        block = mb.GetBlock(i)
        md = mb.GetMetaData(i)
        name = ""
        if md is not None and md.Has(mb.NAME()):
            name = md.Get(mb.NAME())

        entry: dict[str, Any] = {
            "index": i,
            "name": name or f"Block_{i}",
            "type": type(block).__name__ if block else "None",
        }

        if block is None:
            entry["num_points"] = 0
            entry["num_cells"] = 0
        elif isinstance(block, vtk.vtkMultiBlockDataSet):
            entry["children"] = _inspect_multiblock(block)
        elif isinstance(block, vtk.vtkDataSet):
            entry["num_points"] = block.GetNumberOfPoints()
            entry["num_cells"] = block.GetNumberOfCells()

        blocks.append(entry)

    return blocks


# ---------------------------------------------------------------------------
# extract_stats — numpy-based field statistics
# ---------------------------------------------------------------------------


def extract_stats(
    dataset: vtk.vtkDataObject,
    fields: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Extract statistics (min, max, mean, std) for specified fields.

    Args:
        dataset: VTK dataset.
        fields: List of field names. None = all available fields.

    Returns:
        Dict mapping field_name → {min, max, mean, std, components, association}.
    """

    ds = _ensure_dataset(dataset)
    if ds is None:
        return {}

    if fields is None:
        fields = _all_array_names(ds)

    result: dict[str, dict[str, Any]] = {}
    for name in fields:
        np_arr, association = _get_numpy_array(ds, name)
        if np_arr is None:
            continue

        stats: dict[str, Any] = {
            "association": association,
            "components": 1 if np_arr.ndim == 1 else np_arr.shape[1],
        }

        if np_arr.ndim == 1:
            stats["min"] = float(np_arr.min())
            stats["max"] = float(np_arr.max())
            stats["mean"] = float(np_arr.mean())
            stats["std"] = float(np_arr.std())
        else:
            # Per-component stats
            stats["min"] = [float(np_arr[:, c].min()) for c in range(np_arr.shape[1])]
            stats["max"] = [float(np_arr[:, c].max()) for c in range(np_arr.shape[1])]
            stats["mean"] = [float(np_arr[:, c].mean()) for c in range(np_arr.shape[1])]
            stats["std"] = [float(np_arr[:, c].std()) for c in range(np_arr.shape[1])]
            # Also compute magnitude stats for vectors
            import numpy as _np

            mag = _np.linalg.norm(np_arr, axis=1)
            stats["magnitude"] = {
                "min": float(mag.min()),
                "max": float(mag.max()),
                "mean": float(mag.mean()),
                "std": float(mag.std()),
            }

        result[name] = stats

    return result


# ---------------------------------------------------------------------------
# extract_data — full field data as Python-native structures
# ---------------------------------------------------------------------------


def extract_data(
    dataset: vtk.vtkDataObject,
    fields: list[str] | None = None,
    include_coords: bool = False,
) -> dict[str, Any]:
    """Extract field data as lists (JSON-serializable).

    Args:
        dataset: VTK dataset.
        fields: List of field names. None = all fields.
        include_coords: Include point coordinates as "x", "y", "z" arrays.

    Returns:
        Dict mapping field names to nested lists of values.
        If include_coords, also contains "x", "y", "z" keys.
    """

    ds = _ensure_dataset(dataset)
    if ds is None:
        return {}

    if fields is None:
        fields = _all_array_names(ds)

    result: dict[str, Any] = {}

    if include_coords:
        coords = _get_coordinates(ds)
        if coords is not None:
            result["x"] = coords[:, 0].tolist()
            result["y"] = coords[:, 1].tolist()
            result["z"] = coords[:, 2].tolist()

    for name in fields:
        np_arr, _association = _get_numpy_array(ds, name)
        if np_arr is None:
            continue
        result[name] = np_arr.tolist()

    return result


# ---------------------------------------------------------------------------
# export_file — write to disk in various formats
# ---------------------------------------------------------------------------

_WRITER_MAP: dict[str, str] = {
    ".vtu": "vtkXMLUnstructuredGridWriter",
    ".vtp": "vtkXMLPolyDataWriter",
    ".vts": "vtkXMLStructuredGridWriter",
    ".vti": "vtkXMLImageDataWriter",
    ".vtr": "vtkXMLRectilinearGridWriter",
    ".vtm": "vtkXMLMultiBlockDataWriter",
    ".vtk": "vtkGenericDataObjectWriter",
    ".stl": "vtkSTLWriter",
    ".ply": "vtkPLYWriter",
    ".csv": "__csv__",
}


def export_file(
    dataset: vtk.vtkDataObject,
    output_path: str | Path,
    file_format: str | None = None,
) -> dict[str, Any]:
    """Export a VTK dataset to a file.

    Args:
        dataset: VTK dataset to export.
        output_path: Destination file path.
        file_format: File extension override (e.g., ".stl"). Auto-detected from path if None.

    Returns:
        Dict with "path", "format", "size_bytes".
    """
    import vtk

    path = Path(output_path).resolve()
    ext = file_format or path.suffix.lower()

    if ext == ".csv":
        return _export_csv(dataset, path)

    writer_name = _WRITER_MAP.get(ext)
    if writer_name is None:
        available = ", ".join(sorted(_WRITER_MAP.keys()))
        msg = f"Unsupported export format '{ext}'. Available: {available}"
        raise ValueError(msg)

    writer_class = getattr(vtk, writer_name, None)
    if writer_class is None:
        msg = f"VTK class '{writer_name}' not available."
        raise RuntimeError(msg)

    # STL/PLY require polydata — auto convert
    if ext in (".stl", ".ply"):
        dataset = _ensure_polydata(dataset)

    writer = writer_class()
    writer.SetFileName(str(path))
    writer.SetInputData(dataset)
    writer.Write()

    size = path.stat().st_size if path.exists() else 0
    return {
        "path": str(path),
        "format": ext,
        "size_bytes": size,
    }


def _export_csv(dataset: vtk.vtkDataObject, path: Path) -> dict[str, Any]:
    """Export dataset as CSV using numpy."""
    import csv

    ds = _ensure_dataset(dataset)
    if ds is None:
        msg = "Cannot export empty dataset to CSV"
        raise ValueError(msg)

    fields = _all_array_names(ds)
    data = extract_data(ds, fields, include_coords=True)

    # Determine row count
    n = 0
    for v in data.values():
        if isinstance(v, list):
            n = len(v)
            break

    if n == 0:
        msg = "No data to export"
        raise ValueError(msg)

    # Build flat columns
    columns: dict[str, list[float]] = {}
    for key, values in data.items():
        if not isinstance(values, list) or len(values) != n:
            continue
        if isinstance(values[0], list):
            # Multi-component: expand to key_0, key_1, key_2
            num_comp = len(values[0])
            for c in range(num_comp):
                col_name = f"{key}_{c}"
                columns[col_name] = [row[c] for row in values]
        else:
            columns[key] = values

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        headers = list(columns.keys())
        writer.writerow(headers)
        for i in range(n):
            writer.writerow([columns[h][i] for h in headers])

    size = path.stat().st_size if path.exists() else 0
    return {
        "path": str(path),
        "format": ".csv",
        "size_bytes": size,
    }


# ---------------------------------------------------------------------------
# get_leaf_block — navigate multiblock to largest leaf
# ---------------------------------------------------------------------------


def get_leaf_block(dataset: vtk.vtkDataObject) -> vtk.vtkDataSet | None:
    """Get the largest leaf dataset from a (potentially nested) multiblock.

    Args:
        dataset: Any VTK data object.

    Returns:
        The leaf vtkDataSet with the most cells, or None.
    """
    import vtk

    if isinstance(dataset, vtk.vtkDataSet):
        return dataset

    if not isinstance(dataset, vtk.vtkMultiBlockDataSet):
        return None

    best: vtk.vtkDataSet | None = None
    best_cells = -1

    for leaf in _iter_leaves(dataset):
        nc = leaf.GetNumberOfCells()
        if nc > best_cells:
            best = leaf
            best_cells = nc

    return best


def _iter_leaves(mb: vtk.vtkMultiBlockDataSet) -> list[vtk.vtkDataSet]:
    """Iterate all leaf datasets in a multiblock (depth-first)."""
    import vtk

    leaves: list[vtk.vtkDataSet] = []
    for i in range(mb.GetNumberOfBlocks()):
        block = mb.GetBlock(i)
        if block is None:
            continue
        if isinstance(block, vtk.vtkMultiBlockDataSet):
            leaves.extend(_iter_leaves(block))
        elif isinstance(block, vtk.vtkDataSet):
            leaves.append(block)
    return leaves


# ---------------------------------------------------------------------------
# Internal helpers — numpy array access
# ---------------------------------------------------------------------------


def _ensure_dataset(data: vtk.vtkDataObject) -> vtk.vtkDataSet | None:
    """Ensure we have a vtkDataSet, extracting from multiblock if needed."""
    import vtk

    if isinstance(data, vtk.vtkDataSet):
        return data
    if isinstance(data, vtk.vtkMultiBlockDataSet):
        return get_leaf_block(data)
    return None


def _ensure_polydata(data: vtk.vtkDataObject) -> vtk.vtkPolyData:
    """Convert dataset to polydata for STL/PLY export."""
    import vtk

    if isinstance(data, vtk.vtkPolyData):
        return data

    surf = vtk.vtkDataSetSurfaceFilter()
    surf.SetInputData(data)
    surf.Update()
    return surf.GetOutput()


def _all_array_names(ds: vtk.vtkDataSet) -> list[str]:
    """Get all point and cell array names."""
    names: list[str] = []
    pd = ds.GetPointData()
    if pd:
        for i in range(pd.GetNumberOfArrays()):
            name = pd.GetArrayName(i)
            if name:
                names.append(name)
    cd = ds.GetCellData()
    if cd:
        for i in range(cd.GetNumberOfArrays()):
            name = cd.GetArrayName(i)
            if name and name not in names:
                names.append(name)
    return names


def _get_numpy_array(
    ds: vtk.vtkDataSet,
    name: str,
) -> tuple[Any, str]:
    """Get a field as numpy array, trying point data then cell data.

    Returns:
        (numpy_array, association) where association is "point" or "cell".
        numpy_array is None if not found.
    """
    from vtk.util.numpy_support import vtk_to_numpy

    pd = ds.GetPointData()
    if pd:
        arr = pd.GetArray(name)
        if arr is not None:
            return vtk_to_numpy(arr), "point"

    cd = ds.GetCellData()
    if cd:
        arr = cd.GetArray(name)
        if arr is not None:
            return vtk_to_numpy(arr), "cell"

    return None, "point"


def _get_coordinates(ds: vtk.vtkDataSet) -> Any:
    """Get point coordinates as Nx3 numpy array."""
    from vtk.util.numpy_support import vtk_to_numpy

    points = ds.GetPoints()
    if points is None:
        return None

    return vtk_to_numpy(points.GetData())


def export_gltf(
    dataset: vtk.vtkDataObject,
    output_path: str | Path,
    binary: bool = True,
) -> dict[str, Any]:
    """Export VTK data to glTF/glB format for 3D web viewers.

    Requires VTK 9.4+ with vtkGLTFExporter support.

    Args:
        dataset: VTK dataset to export.
        output_path: Destination file path (.gltf or .glb).
        binary: If True, inline data for binary glTF (.glb).

    Returns:
        Dict with "path", "format", "size_bytes".
    """
    import vtk

    path = Path(output_path).resolve()

    if not hasattr(vtk, "vtkGLTFExporter"):
        msg = "vtkGLTFExporter not available. Requires VTK >= 9.4"
        raise RuntimeError(msg)

    # Create a standalone offscreen render window (avoid shared singleton
    # which can SIGSEGV in headless CI environments without GPU/EGL).
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(True)
    rw.SetSize(800, 600)
    renderer = vtk.vtkRenderer()
    rw.AddRenderer(renderer)

    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputData(dataset)
    mapper.SetScalarVisibility(False)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer.AddActor(actor)
    renderer.ResetCamera()

    exporter = vtk.vtkGLTFExporter()
    exporter.SetRenderWindow(rw)
    exporter.SetFileName(str(path))
    if binary:
        exporter.InlineDataOn()
    exporter.Write()

    # Clean up
    renderer.RemoveAllViewProps()
    rw.GetRenderers().RemoveAllItems()

    size = path.stat().st_size if path.exists() else 0
    return {
        "path": str(path),
        "format": path.suffix,
        "size_bytes": size,
    }


def supported_export_formats() -> list[str]:
    """Return sorted list of supported export file extensions."""
    return sorted(_WRITER_MAP.keys())
