# E2E Evidence — #67 Remote render (WebSocket streaming)

- **Date**: 2026-06-16
- **Scenario**: `e2e/scenarios/remote_render_e2e.py` (+ `tests/test_remote_vtk.py`)
- **Environment**: oliveeelab self-hosted, RTX 4090, EGL

## What was delivered

`viznoir/remote.py` — a WebSocket render server that streams rendered frames from
the GPU host:

- client sends a JSON request (`file_path`, `field_name`, `colormap`, `frames`/`azimuths`)
- server renders an **orbit** of camera azimuths through the renderer singleton
  and streams each frame back as a binary PNG, ending with `{"done": true, "frames": n}`
- a malformed request gets `{"error": ...}` and the connection stays open
- renders run synchronously on the event-loop thread (VTK is thread-affine; the
  shared GPU singleton serializes renders anyway)

Run it with `python -m viznoir.remote --host 0.0.0.0 --port 14100`.

## End-to-end demonstration (real socket, real GPU renders)

```
received 3 frame(s), sizes=[131422, 240696, 189016] bytes
done message: {'done': True, 'frames': 3}
  [PASS] 3 frames streamed over WebSocket
  [PASS] every frame is a valid PNG
  [PASS] frames are non-trivial renders
  [PASS] done summary correct
```

The three frames have different sizes because they are genuinely different camera
angles of the orbit — confirming real rendering, not a cached/echoed payload.

## Tests

- `tests/test_remote.py` — 11 unit tests (parse/expand/stream/handler) with a fake
  websocket + fake render_fn (no GPU/socket)
- `tests/test_remote_vtk.py` — 2 GPU tests: `_default_render_fn` produces a real
  PNG, and a full real-WebSocket roundtrip streams an orbit (runs on the
  self-hosted GPU job)
- `remote.py` at **100%** coverage (transport via unit tests, render+serve via the
  GPU tests, CLI `pragma: no cover`). mypy clean.
