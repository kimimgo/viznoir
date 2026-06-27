"""WebSocket remote render — stream rendered frames from a GPU host.

A thin WebSocket server: a client sends a JSON render request, the server renders
each requested frame (an orbit of camera azimuths) through the renderer singleton
and streams the PNG bytes back as binary messages, finishing with a small JSON
``{"done": true, "frames": n}``. A malformed request gets a JSON ``{"error": ...}``
and the connection stays open.

The frame-producing core takes an injected ``render_fn`` so the transport is
testable without a GPU or a real socket; ``_default_render_fn`` is the real
renderer path used by :func:`serve`.

Run:  python -m viznoir.remote --host 0.0.0.0 --port 14100
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import AsyncIterator, Callable
from typing import Any

from viznoir.logging import get_logger

logger = get_logger("remote")

RenderFn = Callable[[dict[str, Any]], bytes]

_BASE_KEYS = ("file_path", "field_name", "association", "colormap", "scalar_range", "timestep")


def parse_request(raw: str | bytes) -> dict[str, Any]:
    """Parse and validate a render-request message. Raises ValueError on bad input."""
    try:
        req = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(req, dict) or "file_path" not in req:
        raise ValueError("render request requires a 'file_path'")
    return req


def expand_frames(req: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand a request into per-frame parameter dicts (an orbit of azimuths)."""
    base = {k: req[k] for k in _BASE_KEYS if k in req}
    azimuths = req.get("azimuths")
    if azimuths:
        return [{**base, "azimuth": a} for a in azimuths]
    n = int(req.get("frames", 1))
    if n > 1:
        return [{**base, "azimuth": 360.0 * i / n} for i in range(n)]
    return [{**base, "azimuth": req.get("azimuth", 0.0)}]


async def render_frames(req: dict[str, Any], render_fn: RenderFn) -> AsyncIterator[bytes]:
    """Yield one PNG (bytes) per frame.

    Renders run synchronously on the event-loop thread: VTK's render window is
    thread-affine, and the shared GPU singleton serializes renders anyway, so a
    render server processes one frame at a time rather than risking a cross-thread
    OpenGL context crash.
    """
    for frame_params in expand_frames(req):
        yield render_fn(frame_params)


async def handle_connection(websocket: Any, render_fn: RenderFn) -> None:
    """Serve one client: stream frames per request; report errors as JSON."""
    async for message in websocket:
        try:
            req = parse_request(message)
        except ValueError as exc:
            await websocket.send(json.dumps({"error": str(exc)}))
            continue
        count = 0
        async for frame in render_frames(req, render_fn):
            await websocket.send(frame)
            count += 1
        await websocket.send(json.dumps({"done": True, "frames": count}))


def _default_render_fn(params: dict[str, Any]) -> bytes:
    """Render one orbit frame of a dataset to PNG (the real GPU path)."""
    from viznoir.engine.camera import CameraConfig
    from viznoir.engine.readers import read_dataset
    from viznoir.engine.renderer import RenderConfig, render_to_png

    data = read_dataset(params["file_path"], timestep=params.get("timestep"))
    b = data.GetBounds()
    center = ((b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0)
    diag = math.sqrt((b[1] - b[0]) ** 2 + (b[3] - b[2]) ** 2 + (b[5] - b[4]) ** 2) or 1.0
    rad = math.radians(float(params.get("azimuth", 0.0)))
    dist = diag * 2.0
    position = (
        center[0] + dist * math.cos(rad) * 0.7,
        center[1] + dist * math.sin(rad) * 0.7,
        center[2] + dist * 0.5,
    )
    camera = CameraConfig(position=position, focal_point=center, view_up=(0.0, 0.0, 1.0))
    config = RenderConfig(
        array_name=params.get("field_name"),
        colormap=params.get("colormap", "cool to warm"),
        scalar_range=tuple(params["scalar_range"]) if params.get("scalar_range") else None,
    )
    return render_to_png(data, config, camera_config=camera)


async def serve(host: str = "127.0.0.1", port: int = 14100, render_fn: RenderFn | None = None) -> None:
    """Run the WebSocket render server until cancelled."""
    import websockets

    fn = render_fn or _default_render_fn

    async def handler(ws: Any) -> None:
        await handle_connection(ws, fn)

    logger.info("viznoir remote render server on ws://%s:%d", host, port)
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever


def main() -> None:  # pragma: no cover - CLI entry point
    import argparse

    ap = argparse.ArgumentParser(description="viznoir WebSocket remote render server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=14100)
    args = ap.parse_args()
    asyncio.run(serve(host=args.host, port=args.port))


if __name__ == "__main__":  # pragma: no cover
    main()
