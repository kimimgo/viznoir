"""VTK file readers — unified DataReader with auto-detection for 26+ formats."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from parapilot.errors import FileFormatError
from parapilot.logging import get_logger

if TYPE_CHECKING:
    import vtk

logger = get_logger("readers")

__all__ = [
    "DataReader",
    "DatasetInfo",
    "read_dataset",
    "get_timesteps",
    "list_arrays",
    "list_blocks",
]


# ---------------------------------------------------------------------------
# Reader registry — extension → (vtk_class_name, is_xml)
# ---------------------------------------------------------------------------

_READER_MAP: dict[str, tuple[str, bool]] = {
    # VTK Legacy
    ".vtk": ("vtkGenericDataObjectReader", False),
    # VTK XML formats
    ".vtu": ("vtkXMLUnstructuredGridReader", True),
    ".vtp": ("vtkXMLPolyDataReader", True),
    ".vts": ("vtkXMLStructuredGridReader", True),
    ".vti": ("vtkXMLImageDataReader", True),
    ".vtr": ("vtkXMLRectilinearGridReader", True),
    ".vtm": ("vtkXMLMultiBlockDataReader", True),
    ".vthb": ("vtkXMLUniformGridAMRReader", True),
    # OpenFOAM
    ".foam": ("vtkOpenFOAMReader", False),
    ".openfoam": ("vtkOpenFOAMReader", False),
    # Geometry
    ".stl": ("vtkSTLReader", False),
    ".ply": ("vtkPLYReader", False),
    ".obj": ("vtkOBJReader", False),
    # CGNS
    ".cgns": ("vtkCGNSReader", False),
    # Exodus
    ".e": ("vtkExodusIIReader", False),
    ".exo": ("vtkExodusIIReader", False),
    ".ex2": ("vtkExodusIIReader", False),
    # EnSight
    ".case": ("vtkGenericEnSightReader", False),
    # XDMF
    ".xdmf": ("vtkXdmf3Reader", False),
    ".xmf": ("vtkXdmf3Reader", False),
    # PVD (handled specially)
    ".pvd": ("__pvd__", False),
}

# Series formats: .vtu.series, .vtp.series, etc.
_SERIES_EXTENSIONS = {".series"}


def _format_suggestion(suffix: str) -> str | None:
    """Suggest a close format match for a typo'd extension."""
    import difflib

    known = list(_READER_MAP.keys()) + list(_SERIES_EXTENSIONS) + [".pvd"]
    matches = difflib.get_close_matches(suffix, known, n=1, cutoff=0.6)
    return matches[0] if matches else None


@dataclass
class DatasetInfo:
    """Metadata about a loaded dataset."""

    file_path: str
    reader_type: str
    dataset_type: str
    num_points: int
    num_cells: int
    bounds: tuple[float, float, float, float, float, float]
    point_arrays: list[str]
    cell_arrays: list[str]
    field_arrays: list[str]
    timesteps: list[float]
    num_blocks: int
    block_names: list[str]


@dataclass
class _PvdEntry:
    """A single file entry from a PVD file."""

    __slots__ = ("time", "file", "part", "group")
    time: float
    file: str
    part: int
    group: str


@dataclass
class _SeriesEntry:
    """A single file entry from a .series JSON file."""

    __slots__ = ("time", "file")
    time: float
    file: str


# ---------------------------------------------------------------------------
# DataReader — main class
# ---------------------------------------------------------------------------


class DataReader:
    """Unified VTK file reader with auto-detection and timestep support."""

    __slots__ = ("_path", "_reader", "_timesteps", "_is_multiblock", "_pvd_entries", "_series_entries")

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path).resolve()
        self._reader: vtk.vtkAlgorithm | None = None
        self._timesteps: list[float] = []
        self._is_multiblock: bool = False
        self._pvd_entries: list[_PvdEntry] = []
        self._series_entries: list[_SeriesEntry] = []

        logger.debug("DataReader: opening %s (format=%s)", self._path, self._path.suffix.lower())

        if not self._path.exists():
            msg = f"File not found: {self._path}"
            raise FileNotFoundError(msg)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def timesteps(self) -> list[float]:
        return list(self._timesteps)

    def read(self, timestep: float | None = None) -> vtk.vtkDataObject:
        """Read the dataset, optionally at a specific timestep.

        Args:
            timestep: Target time value. None = first/only timestep.

        Returns:
            VTK data object (vtkDataSet, vtkMultiBlockDataSet, etc.)
        """
        if self._reader is None:
            self._create_reader()

        if timestep is not None and self._timesteps:
            self._set_timestep(timestep)
        elif self._reader is not None:
            self._reader.Update()

        assert self._reader is not None
        # vtkTrivialProducer (meshio fallback) lacks GetOutput()
        if hasattr(self._reader, "GetOutput"):
            return self._reader.GetOutput()
        return self._reader.GetOutputDataObject(0)

    def get_info(self, timestep: float | None = None) -> DatasetInfo:
        """Get metadata about the dataset."""
        output = self.read(timestep)
        return _extract_info(output, str(self._path), type(self._reader).__name__, self._timesteps)

    def close(self) -> None:
        """Release the VTK reader."""
        self._reader = None
        self._timesteps = []

    # -- Private methods ---------------------------------------------------

    def _create_reader(self) -> None:
        """Instantiate the correct VTK reader based on file extension."""
        import vtk

        suffix = self._path.suffix.lower()

        # Handle .series files (e.g. .vtu.series)
        if suffix in _SERIES_EXTENSIONS:
            self._read_series()
            return

        # Handle PVD
        if suffix == ".pvd":
            self._read_pvd()
            return

        entry = _READER_MAP.get(suffix)
        if entry is None:
            # Try meshio fallback for additional format support
            self._try_meshio_fallback(suffix)
            return

        class_name, _is_xml = entry
        logger.debug("DataReader: using %s for %s", class_name, suffix)
        reader_class = getattr(vtk, class_name, None)
        if reader_class is None:
            msg = f"VTK class '{class_name}' not available. Check your VTK build."
            raise RuntimeError(msg)

        reader = reader_class()

        if class_name == "vtkGenericEnSightReader":
            reader.SetCaseFileName(str(self._path))
        else:
            reader.SetFileName(str(self._path))

        # OpenFOAM-specific setup
        if class_name == "vtkOpenFOAMReader":
            self._setup_openfoam(reader)
        else:
            reader.Update()

        self._reader = reader
        self._timesteps = _extract_timesteps(reader)
        self._is_multiblock = isinstance(
            reader.GetOutput(), vtk.vtkMultiBlockDataSet
        )

    def _try_meshio_fallback(self, suffix: str) -> None:
        """Attempt to read the file via meshio and convert to VTK."""
        import vtk

        hint = _format_suggestion(suffix)

        try:
            import meshio
        except ImportError:
            available = ", ".join(sorted(_READER_MAP.keys()))
            msg = (
                f"Unsupported file format '{suffix}'. Supported: {available}. "
                f"For more formats: pip install mcp-server-parapilot[mesh]"
            )
            if hint:
                msg += f" Did you mean '{hint}'?"
            raise FileFormatError(msg)

        try:
            mesh = meshio.read(str(self._path))
        except Exception as exc:
            available = ", ".join(sorted(_READER_MAP.keys()))
            msg = (
                f"Unsupported file format '{suffix}'. Native VTK: {available}. "
                f"meshio also failed: {exc}"
            )
            if hint:
                msg += f" Did you mean '{hint}'?"
            raise FileFormatError(msg) from exc
        vtk_data = _meshio_to_vtk(mesh)

        # Wrap converted data in vtkTrivialProducer for pipeline compatibility
        producer = vtk.vtkTrivialProducer()
        producer.SetOutput(vtk_data)
        producer.Update()

        self._reader = producer
        self._timesteps = []
        self._is_multiblock = False

    def _setup_openfoam(self, reader: vtk.vtkOpenFOAMReader) -> None:
        """Configure OpenFOAM reader with all patches and cell arrays enabled."""
        # First update to discover arrays and patches
        reader.Update()
        reader.SetDecomposePolyhedra(True)
        reader.SetSkipZeroTime(True)
        reader.SetCreateCellToPoint(True)

        # Enable all cell arrays
        for i in range(reader.GetCellDataArraySelection().GetNumberOfArrays()):
            reader.GetCellDataArraySelection().EnableArray(
                reader.GetCellDataArraySelection().GetArrayName(i)
            )

        # Enable all patch arrays
        reader.EnableAllPatchArrays()
        reader.Update()

    def _read_pvd(self) -> None:
        """Parse PVD XML and set up reader for the file series."""

        entries = _parse_pvd(self._path)
        if not entries:
            msg = f"No dataset entries found in PVD file: {self._path}"
            raise ValueError(msg)

        self._pvd_entries = entries
        self._timesteps = sorted({e.time for e in entries})

        # Use first entry to create reader
        first_file = (self._path.parent / entries[0].file).resolve()
        if not first_file.exists():
            msg = f"PVD references missing file: {first_file}"
            raise FileNotFoundError(msg)

        # Create reader for the actual file type
        sub_reader = DataReader(first_file)
        sub_reader._create_reader()
        self._reader = sub_reader._reader
        self._is_multiblock = sub_reader._is_multiblock

    def _read_series(self) -> None:
        """Parse .series JSON and set up reader for the file series."""

        entries = _parse_series(self._path)
        if not entries:
            msg = f"No entries found in series file: {self._path}"
            raise ValueError(msg)

        self._series_entries = entries
        self._timesteps = [e.time for e in entries]

        # Use first entry to create reader
        first_file = (self._path.parent / entries[0].file).resolve()
        if not first_file.exists():
            msg = f"Series references missing file: {first_file}"
            raise FileNotFoundError(msg)

        sub_reader = DataReader(first_file)
        sub_reader._create_reader()
        self._reader = sub_reader._reader
        self._is_multiblock = sub_reader._is_multiblock

    def _set_timestep(self, target_time: float) -> None:
        """Set the reader to a specific timestep using executive pipeline."""
        import vtk

        assert self._reader is not None

        # For PVD/series: switch to the correct file
        if self._pvd_entries:
            self._switch_pvd_file(target_time)
            return
        if self._series_entries:
            self._switch_series_file(target_time)
            return

        # Standard VTK timestep selection via executive
        exe = self._reader.GetExecutive()
        out_info = exe.GetOutputInformation(0)
        key = vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP()
        out_info.Set(key, target_time)
        self._reader.Modified()
        self._reader.Update()

    def _switch_pvd_file(self, target_time: float) -> None:
        """Switch PVD reader to the file for the closest timestep."""
        closest = min(self._pvd_entries, key=lambda e: abs(e.time - target_time))
        target_file = (self._path.parent / closest.file).resolve()
        assert self._reader is not None
        self._reader.SetFileName(str(target_file))
        self._reader.Modified()
        self._reader.Update()

    def _switch_series_file(self, target_time: float) -> None:
        """Switch series reader to the file for the closest timestep."""
        closest = min(self._series_entries, key=lambda e: abs(e.time - target_time))
        target_file = (self._path.parent / closest.file).resolve()
        assert self._reader is not None
        self._reader.SetFileName(str(target_file))
        self._reader.Modified()
        self._reader.Update()


# ---------------------------------------------------------------------------
# File parsers
# ---------------------------------------------------------------------------


def _parse_pvd(pvd_path: Path) -> list[_PvdEntry]:
    """Parse a ParaView PVD file into a list of entries."""
    tree = ET.parse(pvd_path)
    root = tree.getroot()
    entries: list[_PvdEntry] = []

    for dataset in root.iter("DataSet"):
        time_str = dataset.get("timestep", "0")
        file_str = dataset.get("file", "")
        part_str = dataset.get("part", "0")
        group_str = dataset.get("group", "")

        if not file_str:
            continue

        entries.append(
            _PvdEntry(
                time=float(time_str),
                file=file_str,
                part=int(part_str),
                group=group_str,
            )
        )

    entries.sort(key=lambda e: e.time)
    return entries


def _parse_series(series_path: Path) -> list[_SeriesEntry]:
    """Parse a VTK .series JSON file into a list of entries."""
    with open(series_path) as f:
        data = json.load(f)

    entries: list[_SeriesEntry] = []
    for item in data.get("files", []):
        entries.append(
            _SeriesEntry(
                time=float(item.get("time", 0.0)),
                file=item.get("name", ""),
            )
        )

    return entries


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def _extract_timesteps(reader: vtk.vtkAlgorithm) -> list[float]:
    """Extract available timesteps from a VTK reader."""
    import vtk

    timesteps: list[float] = []

    exe = reader.GetExecutive()
    if exe is None:
        return timesteps

    out_info = exe.GetOutputInformation(0)
    if out_info is None:
        return timesteps

    key = vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS()
    if out_info.Has(key):
        n = out_info.Length(key)
        timesteps = [out_info.Get(key, i) for i in range(n)]

    return timesteps


def _get_array_names(data_attrs: vtk.vtkDataSetAttributes) -> list[str]:
    """Get all array names from a vtkDataSetAttributes object."""
    if data_attrs is None:
        return []
    return [
        data_attrs.GetArrayName(i)
        for i in range(data_attrs.GetNumberOfArrays())
        if data_attrs.GetArrayName(i) is not None
    ]


def _extract_info(
    output: vtk.vtkDataObject,
    file_path: str,
    reader_type: str,
    timesteps: list[float],
) -> DatasetInfo:
    """Extract DatasetInfo from a VTK data object."""
    import vtk

    dataset_type = type(output).__name__
    num_blocks = 0
    block_names: list[str] = []
    point_arrays: list[str] = []
    cell_arrays: list[str] = []
    field_arrays: list[str] = []
    num_points = 0
    num_cells = 0
    bounds = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    if isinstance(output, vtk.vtkMultiBlockDataSet):
        num_blocks = output.GetNumberOfBlocks()
        block_names = _get_block_names(output)
        # Get arrays from first non-None leaf block
        leaf = _first_leaf(output)
        if leaf is not None:
            point_arrays = _get_array_names(leaf.GetPointData())
            cell_arrays = _get_array_names(leaf.GetCellData())
            field_arrays = _get_array_names(leaf.GetFieldData())
            num_points = leaf.GetNumberOfPoints()
            num_cells = leaf.GetNumberOfCells()
            bounds = leaf.GetBounds()
    elif isinstance(output, vtk.vtkDataSet):
        point_arrays = _get_array_names(output.GetPointData())
        cell_arrays = _get_array_names(output.GetCellData())
        field_arrays = _get_array_names(output.GetFieldData())
        num_points = output.GetNumberOfPoints()
        num_cells = output.GetNumberOfCells()
        bounds = output.GetBounds()

    return DatasetInfo(
        file_path=file_path,
        reader_type=reader_type,
        dataset_type=dataset_type,
        num_points=num_points,
        num_cells=num_cells,
        bounds=bounds,
        point_arrays=point_arrays,
        cell_arrays=cell_arrays,
        field_arrays=field_arrays,
        timesteps=timesteps,
        num_blocks=num_blocks,
        block_names=block_names,
    )


def _get_block_names(mb: vtk.vtkMultiBlockDataSet) -> list[str]:
    """Get names of all blocks in a multiblock dataset."""
    names: list[str] = []
    meta = mb.GetMetaData
    for i in range(mb.GetNumberOfBlocks()):
        md = meta(i)
        if md is not None and md.Has(mb.NAME()):
            names.append(md.Get(mb.NAME()))
        else:
            names.append(f"Block_{i}")
    return names


def _extract_blocks(mb: vtk.vtkMultiBlockDataSet, block_names: list[str]) -> vtk.vtkDataObject:
    """Extract named blocks from a multiblock dataset.

    Returns the first matching block as a dataset, or the original if none match.
    """

    for i in range(mb.GetNumberOfBlocks()):
        md = mb.GetMetaData(i)
        name = md.Get(mb.NAME()) if md is not None and md.Has(mb.NAME()) else None
        if name in block_names:
            block = mb.GetBlock(i)
            if block is not None:
                return block
    # Fallback: return first leaf
    leaf = _first_leaf(mb)
    return leaf if leaf is not None else mb


def _first_leaf(mb: vtk.vtkMultiBlockDataSet) -> vtk.vtkDataSet | None:
    """Get the first non-None leaf dataset from a multiblock."""
    import vtk

    for i in range(mb.GetNumberOfBlocks()):
        block = mb.GetBlock(i)
        if block is None:
            continue
        if isinstance(block, vtk.vtkMultiBlockDataSet):
            result = _first_leaf(block)
            if result is not None:
                return result
        elif isinstance(block, vtk.vtkDataSet):
            return block
    return None


# ---------------------------------------------------------------------------
# meshio → VTK conversion
# ---------------------------------------------------------------------------

# meshio cell type → VTK cell type constant
_MESHIO_TO_VTK_TYPE: dict[str, int] = {
    "vertex": 1,
    "line": 3,
    "triangle": 5,
    "quad": 9,
    "tetra": 10,
    "hexahedron": 12,
    "wedge": 13,
    "pyramid": 14,
    "line3": 21,
    "triangle6": 22,
    "quad8": 23,
    "tetra10": 24,
    "hexahedron20": 25,
}


def _meshio_to_vtk(mesh: Any) -> vtk.vtkUnstructuredGrid:
    """Convert a meshio.Mesh to vtkUnstructuredGrid.

    Args:
        mesh: A meshio.Mesh object with .points, .cells, .point_data attrs.

    Returns:
        VTK unstructured grid with points, cells, and point data.
    """
    import numpy as np
    import vtk
    from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

    # Create points
    pts_np = np.ascontiguousarray(mesh.points, dtype=np.float64)
    if pts_np.shape[1] == 2:
        # 2D mesh — pad with zeros
        pts_np = np.column_stack([pts_np, np.zeros(len(pts_np))])

    vtk_points = vtk.vtkPoints()
    vtk_points.SetData(numpy_to_vtk(pts_np))  # type: ignore[no-untyped-call]

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(vtk_points)

    # Convert cells
    for cell_block in mesh.cells:
        cell_type_str = cell_block.type
        vtk_type = _MESHIO_TO_VTK_TYPE.get(cell_type_str)
        if vtk_type is None:
            continue  # skip unsupported cell types

        cell_data = np.ascontiguousarray(cell_block.data, dtype=np.int64)
        n_cells, n_nodes = cell_data.shape

        # Build VTK cell array: [n_nodes, id0, id1, ..., n_nodes, id0, id1, ...]
        col = np.full((n_cells, 1), n_nodes, dtype=np.int64)
        connectivity = np.hstack([col, cell_data]).ravel()

        cells = vtk.vtkCellArray()
        vtk_id_arr = numpy_to_vtkIdTypeArray(connectivity)  # type: ignore[no-untyped-call]
        cells.SetCells(n_cells, vtk_id_arr)

        grid.SetCells(vtk_type, cells)

    # Point data
    for name, arr in mesh.point_data.items():
        np_arr = np.ascontiguousarray(arr)
        vtk_arr = numpy_to_vtk(np_arr)  # type: ignore[no-untyped-call]
        vtk_arr.SetName(name)
        grid.GetPointData().AddArray(vtk_arr)

    return grid


# ---------------------------------------------------------------------------
# Public convenience functions
# ---------------------------------------------------------------------------


def read_dataset(
    file_path: str | Path,
    timestep: float | None = None,
    blocks: list[str] | None = None,
    source_files: list[str] | None = None,
) -> vtk.vtkDataObject:
    """Read a VTK dataset from file.

    Args:
        file_path: Path to any supported VTK file format.
        timestep: Target time value for transient data.
        blocks: Block names to extract from multiblock datasets (OpenFOAM).
            If None, returns the full dataset (extracting first leaf for multiblock).
        source_files: Ignored here; used by animation templates for multi-file iteration.

    Returns:
        VTK data object.
    """
    import vtk

    _ = source_files  # used only in animation code generation
    reader = DataReader(file_path)
    dataset = reader.read(timestep)

    if blocks and isinstance(dataset, vtk.vtkMultiBlockDataSet):
        dataset = _extract_blocks(dataset, blocks)

    return dataset


def get_timesteps(file_path: str | Path) -> list[float]:
    """Get available timesteps from a file.

    Args:
        file_path: Path to any supported VTK file format.

    Returns:
        List of time values. Empty if no time data.
    """
    reader = DataReader(file_path)
    reader.read()
    return reader.timesteps


def list_arrays(file_path: str | Path) -> dict[str, list[str]]:
    """List all data arrays in a file.

    Args:
        file_path: Path to any supported VTK file format.

    Returns:
        Dict with keys 'point', 'cell', 'field', each mapping to array name lists.
    """
    reader = DataReader(file_path)
    info = reader.get_info()
    return {
        "point": info.point_arrays,
        "cell": info.cell_arrays,
        "field": info.field_arrays,
    }


def list_blocks(file_path: str | Path) -> list[str]:
    """List block names in a multiblock dataset.

    Args:
        file_path: Path to a multiblock VTK file (.vtm, .foam, etc.)

    Returns:
        List of block names. Empty if not multiblock.
    """
    reader = DataReader(file_path)
    info = reader.get_info()
    return info.block_names


def supported_extensions() -> list[str]:
    """Return sorted list of supported file extensions."""
    exts = sorted(_READER_MAP.keys())
    exts.append(".series")
    return exts
