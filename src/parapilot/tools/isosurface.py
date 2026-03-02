"""IsoSurface tool — DualSPHysics bi4 → VTK surface mesh conversion."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any


async def pv_isosurface_impl(
    bi4_dir: str,
    output_dir: str,
    *,
    vars: str = "+vel,+press,+rhop",
    only_type: str = "+fluid",
    docker_image: str = "dsph-agent:latest",
) -> dict[str, Any]:
    """Run DualSPHysics IsoSurface to generate VTK surface mesh files.

    Args:
        bi4_dir: Directory containing bi4 data files
        output_dir: Directory for output VTK files
        vars: Variable selection (e.g., "+vel,+press,+rhop")
        only_type: Particle type filter (e.g., "+fluid")
        docker_image: Docker image with IsoSurface tool

    Returns:
        Dict with iso_files list and count
    """
    bi4_path = Path(bi4_dir).resolve()
    out_path = Path(output_dir).resolve()
    os.makedirs(out_path, exist_ok=True)

    # Uses asyncio.create_subprocess_exec (no shell) to avoid command injection
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{bi4_path}:/data/input:ro",
        "-v", f"{out_path}:/data/output",
        docker_image,
        "isosurface",
        "-dirin", "/data/input",
        "-saveiso", "/data/output/iso",
        f"-vars:{vars}",
        f"-onlytype:{only_type}",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(
            f"IsoSurface failed (exit {proc.returncode}): {stderr.decode()}"
        )

    # Collect generated VTK files
    iso_files = sorted(
        str(f) for f in out_path.glob("iso_*.vtk")
    )

    return {
        "iso_files": iso_files,
        "count": len(iso_files),
        "output_dir": str(out_path),
        "stdout": stdout.decode().strip()[-500:] if stdout else "",
    }
