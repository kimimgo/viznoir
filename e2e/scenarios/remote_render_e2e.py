"""E2E evidence for #67 — stream orbit frames over a real WebSocket with real renders.

Starts the viznoir remote render server, connects a real WebSocket client, and
requests a 3-frame orbit of a VTK wavelet — verifying real PNG frames arrive over
the wire. Needs EGL/GPU.

Run:  VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow .venv/bin/python e2e/scenarios/remote_render_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from viznoir.remote import serve


def _write_vti(path: str) -> None:
    n = 8
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, n)
    arr = numpy_to_vtk(np.linspace(0.0, 255.0, n * n * n).astype(np.float64), deep=True)
    arr.SetName("RTData")
    img.GetPointData().AddArray(arr)
    w = vtk.vtkXMLImageDataWriter()
    w.SetFileName(path)
    w.SetInputData(img)
    w.Write()


async def main() -> int:
    import websockets

    path = str(Path(tempfile.mkdtemp()) / "w.vti")
    _write_vti(path)
    port = 14241
    server = asyncio.create_task(serve(host="127.0.0.1", port=port))
    frames: list[bytes] = []
    done = None
    try:
        for _ in range(50):
            try:
                conn = await websockets.connect(f"ws://127.0.0.1:{port}")
                break
            except OSError:
                await asyncio.sleep(0.1)
        async with conn:
            await conn.send(json.dumps({"file_path": path, "field_name": "RTData", "frames": 3}))
            while True:
                msg = await asyncio.wait_for(conn.recv(), timeout=30)
                if isinstance(msg, (bytes, bytearray)):
                    frames.append(msg)
                else:
                    done = json.loads(msg)
                    break
    finally:
        server.cancel()
        try:
            await server
        except asyncio.CancelledError:
            pass

    print(f"received {len(frames)} frame(s), sizes={[len(f) for f in frames]} bytes")
    print(f"done message: {done}")
    checks = {
        "3 frames streamed over WebSocket": len(frames) == 3,
        "every frame is a valid PNG": all(f[:4] == b"\x89PNG" for f in frames),
        "frames are non-trivial renders": all(len(f) > 1000 for f in frames),
        "done summary correct": done == {"done": True, "frames": 3},
    }
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
