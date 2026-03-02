"""Configuration for parapilot."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

__all__ = ["PVConfig"]


@dataclass(frozen=True)
class PVConfig:
    """Immutable configuration resolved from environment variables.

    Render backend (PARAPILOT_RENDER_BACKEND):
        "gpu"  — EGL headless (default). Requires NVIDIA GPU + driver.
        "cpu"  — OSMesa software rendering. No GPU needed.
        "auto" — GPU if nvidia-smi available, else CPU fallback.

    VTK backend (PARAPILOT_VTK_BACKEND):
        "egl"    — EGL offscreen rendering (NVIDIA GPU).
        "osmesa" — OSMesa software rendering.
        "auto"   — EGL if GPU available, else OSMesa.
    """

    data_dir: Path = field(default_factory=lambda: Path(os.getenv("PARAPILOT_DATA_DIR", "/data")))
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("PARAPILOT_OUTPUT_DIR", "/output")))
    python_bin: str = field(
        default_factory=lambda: os.getenv("PARAPILOT_PYTHON_BIN", sys.executable)
    )
    vtk_backend: Literal["egl", "osmesa", "auto"] = field(
        default_factory=lambda: _parse_vtk_backend(os.getenv("PARAPILOT_VTK_BACKEND", "auto"))
    )
    docker_image: str = field(
        default_factory=lambda: os.getenv("PARAPILOT_DOCKER_IMAGE", "parapilot:latest")
    )
    default_timeout: float = field(
        default_factory=lambda: float(os.getenv("PARAPILOT_TIMEOUT", "600"))
    )
    render_backend: Literal["gpu", "cpu", "auto"] = field(
        default_factory=lambda: _parse_render_backend(os.getenv("PARAPILOT_RENDER_BACKEND", "gpu"))
    )
    gpu_device: int = field(
        default_factory=lambda: int(os.getenv("PARAPILOT_GPU_DEVICE", "0"))
    )
    default_resolution: tuple[int, int] = (1920, 1080)

    @property
    def use_gpu(self) -> bool:
        """Resolve whether to use GPU rendering."""
        if self.render_backend == "gpu":
            return True
        if self.render_backend == "cpu":
            return False
        # auto: detect GPU availability
        return _gpu_available()


def _parse_render_backend(value: str) -> Literal["gpu", "cpu", "auto"]:
    """Parse and validate render backend string."""
    v = value.lower().strip()
    if v in ("gpu", "cpu", "auto"):
        return v  # type: ignore[return-value]
    return "gpu"


def _parse_vtk_backend(value: str) -> Literal["egl", "osmesa", "auto"]:
    """Parse and validate VTK backend string."""
    v = value.lower().strip()
    if v in ("egl", "osmesa", "auto"):
        return v  # type: ignore[return-value]
    return "auto"


def _gpu_available() -> bool:
    """Check if NVIDIA GPU is available (nvidia-smi probe)."""
    return shutil.which("nvidia-smi") is not None
