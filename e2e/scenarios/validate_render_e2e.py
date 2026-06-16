"""E2E evidence for #59 — validate_render driven over the real MCP protocol.

Spins up the viznoir FastMCP server in-process, connects a Client, and calls the
`validate_render` tool exactly as an agent would: once with a bad config
(sequential colormap on signed pressure + out-of-range isovalue) and once with a
good config. The bad call must FAIL, the good call must PASS.

Run:  .venv/bin/python e2e/scenarios/validate_render_e2e.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk


def _write_vti(path: str) -> None:
    n = 6
    npts = n * n * n
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, n)
    pressure = np.linspace(-90.0, 110.0, npts).astype(np.float64)  # signed, crosses zero
    parr = numpy_to_vtk(pressure, deep=True)
    parr.SetName("pressure")
    img.GetPointData().AddArray(parr)
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetFileName(path)
    writer.SetInputData(img)
    writer.Write()


def _verdict(result) -> dict:
    # FastMCP returns structured content under .data (2.x) or .structured_content.
    data = getattr(result, "data", None)
    if data is None:
        data = getattr(result, "structured_content", None)
    return data


async def main() -> int:
    from fastmcp import Client

    from viznoir.server import mcp

    tmp = Path(tempfile.mkdtemp()) / "signed.vti"
    _write_vti(str(tmp))

    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
        assert "validate_render" in names, "validate_render not registered"

        bad = _verdict(
            await client.call_tool(
                "validate_render",
                {
                    "file_path": str(tmp),
                    "field_name": "pressure",
                    "colormap": "viridis",
                    "scalar_range": [-90.0, 110.0],
                    "filter_type": "contour",
                    "isovalue": 9999.0,
                },
            )
        )
        good = _verdict(
            await client.call_tool(
                "validate_render",
                {
                    "file_path": str(tmp),
                    "field_name": "pressure",
                    "colormap": "coolwarm",
                    "scalar_range": [-110.0, 110.0],
                    "filter_type": "contour",
                    "isovalue": 0.0,
                },
            )
        )

    print(f"field range: [{bad['field']['min']:.1f}, {bad['field']['max']:.1f}]")
    print(f"BAD  verdict={bad['verdict']} :: {bad['summary']}")
    print(f"GOOD verdict={good['verdict']} :: {good['summary']}")

    checks = {
        "validate_render exposed over MCP": "validate_render" in names,
        "bad config -> FAIL": bad["verdict"] == "fail",
        "bad flags pressure colormap": any(
            r["rule"] == "pressure_diverging_colormap" for r in bad["results"]
        ),
        "bad flags empty isosurface": any(
            r["rule"] == "empty_isosurface" and r["status"] == "fail" for r in bad["results"]
        ),
        "good config -> PASS": good["verdict"] == "pass",
        "real field range reported": bad["field"]["min"] < 0 < bad["field"]["max"],
    }
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
