"""VTK file readers — unified DataReader with auto-detection for 26+ formats."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import vtk

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
        return self._reader.GetOutput()

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
            available = ", ".join(sorted(_READER_MAP.keys()))
            msg = f"Unsupported file format '{suffix}'. Supported: {available}"
            raise ValueError(msg)

        class_name, _is_xml = entry
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
        import vtk

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
        import vtk

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
# Public convenience functions
# ---------------------------------------------------------------------------


def read_dataset(
    file_path: str | Path,
    timestep: float | None = None,
) -> vtk.vtkDataObject:
    """Read a VTK dataset from file.

    Args:
        file_path: Path to any supported VTK file format.
        timestep: Target time value for transient data.

    Returns:
        VTK data object.
    """
    reader = DataReader(file_path)
    return reader.read(timestep)


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
