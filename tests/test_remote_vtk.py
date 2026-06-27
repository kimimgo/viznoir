"""GPU/socket E2E for viznoir.remote — real WebSocket roundtrip with real renders.

Renders an orbit of a VTK wavelet over an actual WebSocket connection. Needs EGL,
so it is skipped on GitHub-hosted CI (``*_vtk.py``) and runs on the self-hosted
GPU runner.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from viznoir.remote import _default_render_fn, serve


def _write_vti(path: str) -> None:
    n = 6
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, n)
    rt = np.linspace(0.0, 200.0, n * n * n).astype(np.float64)
    arr = numpy_to_vtk(rt, deep=True)
    arr.SetName("RTData")
    img.GetPointData().AddArray(arr)
    w = vtk.vtkXMLImageDataWriter()
    w.SetFileName(path)
    w.SetInputData(img)
    w.Write()


class TestDefaultRenderFn:
    def test_renders_orbit_frame_to_png(self, tmp_path):
        path = str(tmp_path / "w.vti")
        _write_vti(path)
        png = _default_render_fn({"file_path": path, "field_name": "RTData", "azimuth": 45.0})
        assert png[:4] == b"\x89PNG"
        assert len(png) > 1000


class TestRealSocketRoundtrip:
    async def test_stream_orbit_over_websocket(self, tmp_path):
        import websockets

        path = str(tmp_path / "w.vti")
        _write_vti(path)
        port = 14237
        server = asyncio.create_task(serve(host="127.0.0.1", port=port))
        try:
            # wait for the server to accept connections
            conn = None
            for _ in range(50):
                try:
                    conn = await websockets.connect(f"ws://127.0.0.1:{port}")
                    break
                except OSError:
                    await asyncio.sleep(0.1)
            if conn is None:
                raise RuntimeError("remote render server did not start in time")

            async with conn:
                await conn.send(json.dumps({"file_path": path, "field_name": "RTData", "frames": 2}))
                frames = []
                while True:
                    msg = await asyncio.wait_for(conn.recv(), timeout=30)
                    if isinstance(msg, (bytes, bytearray)):
                        frames.append(msg)
                    else:
                        done = json.loads(msg)
                        break
            assert done == {"done": True, "frames": 2}
            assert len(frames) == 2
            assert all(f[:4] == b"\x89PNG" for f in frames)
        finally:
            server.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await server
