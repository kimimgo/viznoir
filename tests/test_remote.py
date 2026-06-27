"""Tests for viznoir.remote — WebSocket render streaming transport.

A fake websocket + fake render_fn exercise the streaming logic without a GPU or
a real socket.
"""

from __future__ import annotations

import json

import pytest

from viznoir.remote import (
    expand_frames,
    handle_connection,
    parse_request,
    render_frames,
)


class _FakeWS:
    """Minimal async websocket double: iterates given messages, records sends."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.sent: list = []

    def __aiter__(self):
        async def gen():
            for m in self._messages:
                yield m

        return gen()

    async def send(self, data):
        self.sent.append(data)


def _fake_render(params):
    return b"\x89PNG" + str(params.get("azimuth", 0)).encode()


# --------------------------------------------------------------------------- #
class TestParseRequest:
    def test_valid(self):
        req = parse_request('{"file_path": "/x.vti", "field_name": "p"}')
        assert req["file_path"] == "/x.vti"

    def test_requires_file_path(self):
        with pytest.raises(ValueError):
            parse_request('{"field_name": "p"}')

    def test_bad_json(self):
        with pytest.raises(ValueError):
            parse_request("not json{")


class TestExpandFrames:
    def test_single_default(self):
        frames = expand_frames({"file_path": "/x", "field_name": "p"})
        assert len(frames) == 1

    def test_orbit_count(self):
        frames = expand_frames({"file_path": "/x", "frames": 4})
        assert len(frames) == 4
        assert [f["azimuth"] for f in frames] == [0.0, 90.0, 180.0, 270.0]

    def test_explicit_azimuths(self):
        frames = expand_frames({"file_path": "/x", "azimuths": [10, 20, 30]})
        assert [f["azimuth"] for f in frames] == [10, 20, 30]

    def test_carries_base_params(self):
        frames = expand_frames({"file_path": "/x", "field_name": "U", "colormap": "viridis", "frames": 2})
        assert all(f["file_path"] == "/x" and f["field_name"] == "U" for f in frames)


class TestRenderFrames:
    async def test_yields_one_per_frame(self):
        req = {"file_path": "/x", "frames": 3}
        out = [frame async for frame in render_frames(req, _fake_render)]
        assert len(out) == 3
        assert all(f.startswith(b"\x89PNG") for f in out)


class TestHandleConnection:
    async def test_streams_frames_then_done(self):
        ws = _FakeWS(['{"file_path": "/x", "frames": 2}'])
        await handle_connection(ws, _fake_render)
        binary = [m for m in ws.sent if isinstance(m, (bytes, bytearray))]
        texts = [json.loads(m) for m in ws.sent if isinstance(m, str)]
        assert len(binary) == 2
        assert texts[-1] == {"done": True, "frames": 2}

    async def test_bad_request_sends_error(self):
        ws = _FakeWS(["not json{"])
        await handle_connection(ws, _fake_render)
        texts = [json.loads(m) for m in ws.sent if isinstance(m, str)]
        assert "error" in texts[0]
        # no frames streamed for a bad request
        assert not [m for m in ws.sent if isinstance(m, (bytes, bytearray))]

    async def test_multiple_requests(self):
        ws = _FakeWS(['{"file_path": "/a", "frames": 1}', '{"file_path": "/b", "frames": 1}'])
        await handle_connection(ws, _fake_render)
        dones = [json.loads(m) for m in ws.sent if isinstance(m, str)]
        assert len(dones) == 2 and all(d["done"] for d in dones)
