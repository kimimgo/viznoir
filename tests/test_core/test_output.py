"""Tests for viznoir.core.output — OutputHandler and PipelineResult."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from viznoir.core.output import OutputHandler, PipelineResult, _to_json_data
from viznoir.core.runner import RunResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_result(**kwargs) -> RunResult:
    """Create a successful RunResult with defaults."""
    defaults = dict(stdout="", stderr="", exit_code=0)
    defaults.update(kwargs)
    return RunResult(**defaults)


def _fail_result(**kwargs) -> RunResult:
    defaults = dict(stdout="", stderr="script error", exit_code=1)
    defaults.update(kwargs)
    return RunResult(**defaults)


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_ok_true(self):
        rr = _ok_result()
        pr = PipelineResult(output_type="image", raw=rr)
        assert pr.ok is True

    def test_ok_false_exit_code(self):
        rr = _fail_result()
        pr = PipelineResult(output_type="image", raw=rr)
        assert pr.ok is False

    def test_ok_false_no_raw(self):
        pr = PipelineResult(output_type="image", raw=None)
        assert pr.ok is False

    def test_defaults(self):
        pr = PipelineResult(output_type="data")
        assert pr.json_data is None
        assert pr.image_bytes is None
        assert pr.image_base64 is None
        assert pr.file_path is None
        assert pr.raw is None


# ---------------------------------------------------------------------------
# _to_json_data
# ---------------------------------------------------------------------------


class TestToJsonData:
    def test_none(self):
        assert _to_json_data(None) is None

    def test_dict_passthrough(self):
        d = {"key": "val"}
        assert _to_json_data(d) is d

    def test_list_wrapped(self):
        lst = [1, 2, 3]
        result = _to_json_data(lst)
        assert result == {"data": [1, 2, 3]}


# ---------------------------------------------------------------------------
# OutputHandler
# ---------------------------------------------------------------------------


class TestOutputHandler:
    def setup_method(self):
        self.handler = OutputHandler()

    # -- error propagation --
    def test_parse_raises_on_failed_result(self):
        rr = _fail_result()
        with pytest.raises(RuntimeError, match="exited with code 1"):
            self.handler.parse(rr, "image")

    def test_parse_cleanup_crash_does_not_raise(self):
        """VTK cleanup crash (non-zero exit but output exists) should not raise."""
        rr = RunResult(
            stdout="",
            stderr="free(): invalid pointer",
            exit_code=-6,
            output_file_data={"render.png": b"\x89PNG"},
        )
        result = self.handler.parse(rr, "image")
        assert result.output_type == "image"

    # -- image parsing --
    def test_parse_image_from_memory(self):
        png_data = b"\x89PNG\r\n\x1a\nfakedata"
        rr = _ok_result(output_file_data={"output.png": png_data})
        result = self.handler.parse(rr, "image")
        assert result.output_type == "image"
        assert result.image_bytes == png_data
        assert result.image_base64 == base64.b64encode(png_data).decode("ascii")
        assert result.file_path == "output.png"

    def test_parse_image_from_disk(self, tmp_path):
        png_data = b"\x89PNG\r\n\x1a\ndiskdata"
        img_file = tmp_path / "render.png"
        img_file.write_bytes(png_data)
        rr = _ok_result(output_files=[img_file])
        result = self.handler.parse(rr, "image")
        assert result.image_bytes == png_data
        assert result.file_path == str(img_file)

    def test_parse_image_no_image_found(self):
        rr = _ok_result()
        result = self.handler.parse(rr, "image")
        assert result.image_bytes is None
        assert result.image_base64 is None

    def test_parse_image_jpg(self):
        jpg_data = b"\xff\xd8\xff\xe0jpegdata"
        rr = _ok_result(output_file_data={"photo.jpg": jpg_data})
        result = self.handler.parse(rr, "image")
        assert result.image_bytes == jpg_data

    def test_parse_image_jpeg_extension(self):
        data = b"jpegdata"
        rr = _ok_result(output_file_data={"photo.JPEG": data})
        result = self.handler.parse(rr, "image")
        assert result.image_bytes == data

    # -- data parsing --
    def test_parse_data(self):
        rr = _ok_result(json_result={"stats": {"min": 0, "max": 100}})
        result = self.handler.parse(rr, "data")
        assert result.output_type == "data"
        assert result.json_data == {"stats": {"min": 0, "max": 100}}

    def test_parse_csv(self):
        rr = _ok_result(json_result=[1, 2, 3])
        result = self.handler.parse(rr, "csv")
        assert result.output_type == "data"
        assert result.json_data == {"data": [1, 2, 3]}

    def test_parse_inspect(self):
        rr = _ok_result(json_result={"fields": ["p", "U"]})
        result = self.handler.parse(rr, "inspect")
        assert result.output_type == "data"

    # -- animation parsing --
    def test_parse_animation(self):
        rr = _ok_result(json_result={"frames_dir": "/tmp/frames", "count": 10})
        result = self.handler.parse(rr, "animation")
        assert result.output_type == "animation"
        assert result.file_path == "/tmp/frames"
        assert result.json_data["count"] == 10

    def test_parse_animation_no_frames_dir(self):
        rr = _ok_result(json_result={"count": 5})
        result = self.handler.parse(rr, "animation")
        assert result.file_path is None

    def test_parse_animation_no_json(self):
        rr = _ok_result()
        result = self.handler.parse(rr, "animation")
        assert result.file_path is None

    # -- export parsing --
    def test_parse_export_from_json(self):
        rr = _ok_result(json_result={"path": "/out/mesh.vtu"})
        result = self.handler.parse(rr, "export")
        assert result.output_type == "export"
        assert result.file_path == "/out/mesh.vtu"

    def test_parse_export_from_files(self, tmp_path):
        vtu = tmp_path / "out.vtu"
        vtu.touch()
        rr = _ok_result(output_files=[vtu])
        result = self.handler.parse(rr, "export")
        assert result.file_path == str(vtu)

    def test_parse_export_no_file(self):
        rr = _ok_result()
        result = self.handler.parse(rr, "export")
        assert result.file_path is None

    def test_parse_export_stl(self, tmp_path):
        stl = tmp_path / "mesh.stl"
        stl.touch()
        rr = _ok_result(output_files=[stl])
        result = self.handler.parse(rr, "export")
        assert result.file_path == str(stl)

    # -- split_animation --
    def test_parse_split_animation(self):
        rr = _ok_result(json_result={"panes": 4, "gif": "/out/split.gif"})
        result = self.handler.parse(rr, "split_animation")
        assert result.output_type == "split_animation"
        assert result.json_data["panes"] == 4

    # -- multi --
    def test_parse_multi(self):
        png = b"\x89PNGmulti"
        rr = _ok_result(
            output_file_data={"view.png": png},
            json_result={"extra": True},
        )
        result = self.handler.parse(rr, "multi")
        assert result.output_type == "multi"
        assert result.image_bytes == png
        assert result.json_data == {"extra": True}

    # -- unknown type --
    def test_parse_unknown_type(self):
        rr = _ok_result(json_result={"foo": "bar"})
        result = self.handler.parse(rr, "custom_type")
        assert result.output_type == "custom_type"
        assert result.json_data == {"foo": "bar"}

    # -- _find_file --
    def test_find_file_match(self, tmp_path):
        txt = tmp_path / "data.csv"
        txt.touch()
        rr = _ok_result(output_files=[txt])
        found = self.handler._find_file(rr, [".csv"])
        assert found == txt

    def test_find_file_no_match(self, tmp_path):
        txt = tmp_path / "data.txt"
        txt.touch()
        rr = _ok_result(output_files=[txt])
        found = self.handler._find_file(rr, [".csv"])
        assert found is None

    def test_find_file_nonexistent(self):
        rr = _ok_result(output_files=[Path("/nonexistent/file.png")])
        found = self.handler._find_file(rr, [".png"])
        assert found is None


# ---------------------------------------------------------------------------
# RunResult properties (bonus coverage)
# ---------------------------------------------------------------------------


class TestRunResult:
    def test_ok_true(self):
        assert _ok_result().ok is True

    def test_ok_false(self):
        assert _fail_result().ok is False

    def test_is_cleanup_crash_true(self):
        rr = RunResult(
            stdout="",
            stderr="munmap_chunk(): invalid pointer",
            exit_code=-11,
            output_file_data={"out.png": b"data"},
        )
        assert rr.is_cleanup_crash is True

    def test_is_cleanup_crash_false_no_files(self):
        rr = RunResult(
            stdout="",
            stderr="free(): invalid pointer",
            exit_code=-6,
        )
        assert rr.is_cleanup_crash is False

    def test_is_cleanup_crash_false_exit_zero(self):
        rr = RunResult(
            stdout="",
            stderr="free(): invalid pointer",
            exit_code=0,
            output_file_data={"out.png": b"data"},
        )
        assert rr.is_cleanup_crash is False

    def test_raise_on_error_ok(self):
        _ok_result().raise_on_error()  # should not raise

    def test_raise_on_error_fail(self):
        with pytest.raises(RuntimeError, match="exited with code 1"):
            _fail_result().raise_on_error()

    def test_raise_on_error_cleanup_crash(self):
        rr = RunResult(
            stdout="",
            stderr="double free or corruption",
            exit_code=-6,
            output_file_data={"out.png": b"data"},
        )
        rr.raise_on_error()  # should not raise for cleanup crash
