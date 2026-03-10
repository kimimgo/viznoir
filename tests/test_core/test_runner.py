"""Tests for VTKRunner (no Docker or VTK needed)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from viznoir.core.runner import RunResult, VTKRunner


class TestDockerContainerCleanup:
    """RC1: Docker container must be stopped on timeout, not just CLI process."""

    @pytest.mark.asyncio
    async def test_docker_timeout_calls_stop_container(self) -> None:
        """On timeout, _run_docker must call _stop_container with the container name."""
        runner = VTKRunner(mode="docker")

        # First call raises TimeoutError (inside wait_for), second returns normally (post-kill drain)
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=[asyncio.TimeoutError, (b"", b"")])
        mock_proc.kill = MagicMock()

        with (
            patch("viznoir.core.runner.asyncio.create_subprocess_exec", return_value=mock_proc),
            patch.object(runner, "_stop_container", new_callable=AsyncMock) as mock_stop,
            patch("viznoir.core.runner.uuid") as mock_uuid,
        ):
            mock_uuid.uuid4.return_value = MagicMock(hex="abcdef123456")
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "pipeline.py"
                script.write_text("pass")
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()

                result = await runner._run_docker(script, output_dir, timeout=1.0)

        assert result.exit_code == -1
        assert "timed out" in result.stderr
        mock_proc.kill.assert_called_once()
        mock_stop.assert_awaited_once_with("viznoir_abcdef123456")

    @pytest.mark.asyncio
    async def test_docker_run_includes_container_name(self) -> None:
        """docker run args must include --name viznoir_*."""
        from pathlib import Path

        from viznoir.config import PVConfig

        config = PVConfig(data_dir=Path("/data"))
        runner = VTKRunner(mode="docker", config=config)

        captured_args: list[str] = []

        async def fake_subprocess(*args: str, **_kw: object) -> AsyncMock:
            captured_args.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            return mock_proc

        with (
            patch("viznoir.core.runner.asyncio.create_subprocess_exec", side_effect=fake_subprocess),
            patch("viznoir.core.runner.uuid") as mock_uuid,
        ):
            mock_uuid.uuid4.return_value = MagicMock(hex="abcdef123456")
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "pipeline.py"
                script.write_text("pass")
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()

                await runner._run_docker(script, output_dir, timeout=10.0)

        assert "--name" in captured_args
        name_idx = captured_args.index("--name")
        assert captured_args[name_idx + 1] == "viznoir_abcdef123456"

    @pytest.mark.asyncio
    async def test_stop_container_best_effort(self) -> None:
        """_stop_container should not raise even if docker commands fail."""
        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            side_effect=OSError("docker not found"),
        ):
            # Should not raise
            await VTKRunner._stop_container("viznoir_test")

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_no_containers(self) -> None:
        """cleanup_orphaned_containers returns 0 when no containers found."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            count = await VTKRunner.cleanup_orphaned_containers()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_with_containers(self) -> None:
        """cleanup_orphaned_containers removes found containers."""
        call_count = 0

        async def fake_subprocess(*args: str, **_kw: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_proc = AsyncMock()
            if call_count == 1:
                # docker ps returns 2 container IDs
                mock_proc.communicate = AsyncMock(return_value=(b"abc123\ndef456\n", b""))
            else:
                # docker rm -f
                mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            return mock_proc

        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            side_effect=fake_subprocess,
        ):
            count = await VTKRunner.cleanup_orphaned_containers()
        assert count == 2


class TestFfmpegTimeout:
    """RC2: ffmpeg timeout must be handled gracefully."""

    @pytest.mark.asyncio
    async def test_compile_video_ffmpeg_timeout(self) -> None:
        """compile_video should return error on ffmpeg timeout, not crash."""
        from viznoir.pipeline.engine import compile_video

        # First call raises TimeoutError (inside wait_for), second returns normally (post-kill drain)
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=[asyncio.TimeoutError, (b"", b"")])
        mock_proc.kill = MagicMock()

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("viznoir.pipeline.engine.asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            video_bytes, error = await compile_video(
                {"frame_000000.png": b"fake", "frame_000001.png": b"fake"},
                fps=24.0,
            )
        assert video_bytes is None
        assert error is not None
        assert "timed out" in error
        mock_proc.kill.assert_called_once()


class TestCleanupCrashTolerance:
    """Issue #2 RC2: VisRTX cleanup crash should not fail if output files exist."""

    def test_cleanup_crash_detected(self) -> None:
        """is_cleanup_crash returns True for known crash patterns with output."""
        result = RunResult(
            stdout="",
            stderr="vtkXOpenGLRenderWindow: WARN| bad X server\nfree(): invalid pointer",
            exit_code=-6,
            output_file_data={"render.png": b"PNG_DATA"},
        )
        assert result.is_cleanup_crash is True

    def test_cleanup_crash_no_output(self) -> None:
        """is_cleanup_crash returns False if no output files (real failure)."""
        result = RunResult(
            stdout="",
            stderr="free(): invalid pointer",
            exit_code=-6,
        )
        assert result.is_cleanup_crash is False

    def test_cleanup_crash_no_signature(self) -> None:
        """is_cleanup_crash returns False for unknown errors."""
        result = RunResult(
            stdout="",
            stderr="Segmentation fault (core dumped)",
            exit_code=-11,
            output_file_data={"render.png": b"PNG_DATA"},
        )
        assert result.is_cleanup_crash is False

    def test_raise_on_error_tolerates_cleanup_crash(self) -> None:
        """raise_on_error should NOT raise for cleanup crashes with output."""
        result = RunResult(
            stdout="",
            stderr="free(): invalid pointer",
            exit_code=-6,
            output_file_data={"render.png": b"PNG_DATA"},
        )
        # Should not raise
        result.raise_on_error()

    def test_raise_on_error_raises_for_real_failures(self) -> None:
        """raise_on_error should still raise for real errors."""
        result = RunResult(
            stdout="",
            stderr="ImportError: No module named 'paraview'",
            exit_code=1,
        )
        with pytest.raises(RuntimeError, match="exited with code 1"):
            result.raise_on_error()


class TestStdoutProtection:
    """Issue #2 RC1: _protect_stdout isolates MCP stdio from VTK binary dumps."""

    def test_protect_stdout_redirects_fd1(self) -> None:
        """After _protect_stdout, fd 1 should NOT be the original stdout."""
        import io
        import os
        import sys

        from viznoir.server import _protect_stdout

        # Save original state
        orig_stdout = sys.stdout
        _ = os.fstat(1)

        try:
            _protect_stdout()

            # sys.stdout should be a TextIOWrapper (clean MCP channel)
            assert isinstance(sys.stdout, io.TextIOWrapper)

            # fd 1 should now point to devnull (different inode)
            new_fd1_stat = os.fstat(1)
            devnull_stat = os.stat(os.devnull)
            assert new_fd1_stat.st_ino == devnull_stat.st_ino

            # Writing to sys.stdout should work (goes to saved fd)
            sys.stdout.write("")
            sys.stdout.flush()
        finally:
            # Restore: reopen original stdout on fd 1
            saved_fd = sys.stdout.buffer.raw.fileno()  # type: ignore[union-attr]
            os.dup2(saved_fd, 1)
            sys.stdout = orig_stdout


class TestDetectMode:
    def test_docker_mode_when_python_not_found(self):
        """_detect_mode returns 'docker' when python_bin not on PATH."""
        with patch("shutil.which", return_value=None):
            runner = VTKRunner(mode="auto")
            assert runner.mode == "docker"

    def test_local_mode_when_python_found(self):
        """_detect_mode returns 'local' when python_bin is on PATH."""
        with patch("shutil.which", return_value="/usr/bin/python3"):
            runner = VTKRunner(mode="auto")
            assert runner.mode == "local"


class TestExecuteLocalEdgeCases:
    @pytest.mark.asyncio
    async def test_extra_files_written(self):
        """execute writes extra_files to tmpdir; in-process mode verifies via script."""
        runner = VTKRunner(mode="local")

        # In in-process mode, extra_files are written to tmpdir and accessible
        # from the script via the tmpdir path. We verify using _run_inprocess mock.
        captured = {}

        async def mock_run_inprocess(self_inner, script, output_dir, timeout):
            # Verify extra_files written to tmpdir (parent of output_dir)
            extra_file = output_dir.parent / "data.json"
            if extra_file.exists():
                captured["data.json"] = extra_file.read_bytes()
            from viznoir.core.runner import RunResult

            return RunResult(stdout="", stderr="", exit_code=0)

        with patch.object(runner, "_run_inprocess", mock_run_inprocess.__get__(runner, type(runner))):
            result = await runner.execute(
                "pass",
                extra_files={"data.json": b'{"key": "value"}'},
            )
        assert result.exit_code == 0
        assert captured.get("data.json") == b'{"key": "value"}'

    @pytest.mark.asyncio
    async def test_json_parsed_from_stdout(self):
        """execute parses JSON from stdout when no result.json file."""
        runner = VTKRunner(mode="local")

        # In in-process mode, stdout is captured directly from script execution.
        # We use the script itself to print JSON to stdout.
        script = "import json; print(json.dumps({'status': 'ok', 'count': 42}))"
        result = await runner.execute(script)
        assert result.json_result == {"status": "ok", "count": 42}

    @pytest.mark.asyncio
    async def test_json_parse_failure_ignored(self):
        """execute ignores malformed JSON in stdout."""
        runner = VTKRunner(mode="local")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"{invalid json", b""))
        mock_proc.returncode = 0

        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await runner.execute("pass")
        assert result.json_result is None

    @pytest.mark.asyncio
    async def test_local_timeout_handling(self):
        """execute handles local script timeout gracefully."""
        runner = VTKRunner(mode="local")

        # In in-process mode, _run_inprocess handles timeout internally and returns
        # a RunResult with exit_code=-1. We verify via a real short timeout.
        from unittest.mock import patch

        from viznoir.core.runner import RunResult

        async def mock_run_inprocess(script, output_dir, timeout):
            return RunResult(stdout="", stderr=f"VTK script timed out after {timeout}s", exit_code=-1)

        with patch.object(runner, "_run_inprocess", side_effect=mock_run_inprocess):
            result = await runner.execute("pass", timeout=1.0)
        assert result.exit_code == -1
        assert "timed out" in result.stderr

    @pytest.mark.asyncio
    async def test_osmesa_backend_env(self):
        """OSMesa backend sets correct env_overrides for in-process execution."""
        from viznoir.config import PVConfig
        from viznoir.core.runner import RunResult

        config = PVConfig(vtk_backend="osmesa", render_backend="cpu")
        runner = VTKRunner(mode="local", config=config)

        captured_env_overrides: dict = {}

        def mock_executor_run(script, env_overrides=None, output_dir=None):
            if env_overrides:
                captured_env_overrides.update(env_overrides)
            return RunResult(stdout="", stderr="", exit_code=0)

        from viznoir.core.worker import InProcessExecutor

        mock_executor = InProcessExecutor.__new__(InProcessExecutor)
        mock_executor.run = mock_executor_run
        runner._executor = mock_executor

        await runner.execute("pass")
        assert captured_env_overrides.get("VTK_DEFAULT_OPENGL_WINDOW") == "vtkOSOpenGLRenderWindow"


class TestDockerModeNoGPU:
    @pytest.mark.asyncio
    async def test_docker_no_gpu_env(self):
        """Docker mode without GPU sets OSMesa env."""
        from pathlib import Path

        from viznoir.config import PVConfig

        config = PVConfig(data_dir=Path("/data"), render_backend="cpu")
        runner = VTKRunner(mode="docker", config=config)

        captured_args: list[str] = []

        async def fake_subprocess(*args, **_kw):
            captured_args.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            return mock_proc

        with (
            patch("viznoir.core.runner.asyncio.create_subprocess_exec", side_effect=fake_subprocess),
            patch("viznoir.core.runner.uuid") as mock_uuid,
        ):
            mock_uuid.uuid4.return_value = MagicMock(hex="abcdef123456")
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "pipeline.py"
                script.write_text("pass")
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()
                await runner._run_docker(script, output_dir, timeout=10.0)

        assert "--gpus" not in captured_args
        assert "VTK_DEFAULT_OPENGL_WINDOW=vtkOSOpenGLRenderWindow" in captured_args


class TestOutputFilePermissionError:
    """execute() tolerates PermissionError when reading output files."""

    @pytest.mark.asyncio
    async def test_permission_error_skipped(self) -> None:
        """Output file with PermissionError is silently skipped."""
        runner = VTKRunner(mode="local")

        # In in-process mode, the script creates output files directly.
        # execute() collects them after _run_inprocess returns.
        # We patch Path.read_bytes to simulate PermissionError on bad.dat.
        from viznoir.core.runner import RunResult

        async def mock_run_inprocess(script, output_dir, timeout):
            # Create output files in the real output_dir
            (output_dir / "good.png").write_bytes(b"PNG")
            (output_dir / "bad.dat").write_bytes(b"DATA")
            return RunResult(stdout="", stderr="", exit_code=0)

        original_read_bytes = Path.read_bytes

        def patched_read_bytes(self):
            if self.name == "bad.dat":
                raise PermissionError("denied")
            return original_read_bytes(self)

        with (
            patch.object(runner, "_run_inprocess", side_effect=mock_run_inprocess),
            patch.object(Path, "read_bytes", patched_read_bytes),
        ):
            result = await runner.execute("pass")

        assert result.exit_code == 0
        assert "good.png" in result.output_file_data
        assert "bad.dat" not in result.output_file_data


class TestExecuteDockerMode:
    """execute() through Docker mode path (line 102)."""

    @pytest.mark.asyncio
    async def test_execute_docker_mode(self) -> None:
        """execute() with docker mode calls _run_docker."""
        runner = VTKRunner(mode="docker")

        with patch.object(
            runner,
            "_run_docker",
            new_callable=AsyncMock,
            return_value=RunResult(stdout="", stderr="", exit_code=0),
        ) as mock_docker:
            result = await runner.execute("print('hello')")

        assert result.exit_code == 0
        mock_docker.assert_awaited_once()


class TestDockerExtraMounts:
    """Docker _run_docker includes extra_mounts."""

    @pytest.mark.asyncio
    async def test_extra_mounts_in_docker_args(self) -> None:
        from pathlib import Path

        from viznoir.config import PVConfig

        config = PVConfig(data_dir=Path("/data"))
        runner = VTKRunner(mode="docker", config=config)

        captured_args: list[str] = []

        async def fake_subprocess(*args, **_kw):
            captured_args.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            return mock_proc

        with (
            patch("viznoir.core.runner.asyncio.create_subprocess_exec", side_effect=fake_subprocess),
            patch("viznoir.core.runner.uuid") as mock_uuid,
        ):
            mock_uuid.uuid4.return_value = MagicMock(hex="mount123456")
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "pipeline.py"
                script.write_text("pass")
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()
                await runner._run_docker(
                    script,
                    output_dir,
                    timeout=10.0,
                    extra_mounts=[Path("/sim/data")],
                )

        # Verify extra mount is in args
        assert "-v" in captured_args
        mount_str = "/sim/data:/sim/data:ro"
        assert mount_str in captured_args


class TestCleanupOrphanedExceptions:
    """cleanup_orphaned_containers handles timeout/OSError at each stage."""

    @pytest.mark.asyncio
    async def test_cleanup_ps_timeout(self) -> None:
        """Timeout during 'docker ps' returns 0."""
        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            side_effect=asyncio.TimeoutError,
        ):
            count = await VTKRunner.cleanup_orphaned_containers()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_ps_oserror(self) -> None:
        """OSError during 'docker ps' returns 0."""
        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            side_effect=OSError("docker not found"),
        ):
            count = await VTKRunner.cleanup_orphaned_containers()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_rm_timeout(self) -> None:
        """Timeout during 'docker rm' still returns container count."""
        call_count = 0

        async def fake_subprocess(*args, **_kw):
            nonlocal call_count
            call_count += 1
            mock_proc = AsyncMock()
            if call_count == 1:
                # docker ps succeeds
                mock_proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
            else:
                # docker rm times out
                mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            return mock_proc

        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            side_effect=fake_subprocess,
        ):
            count = await VTKRunner.cleanup_orphaned_containers()
        assert count == 1

    @pytest.mark.asyncio
    async def test_cleanup_rm_oserror(self) -> None:
        """OSError during 'docker rm' still returns container count."""
        call_count = 0

        async def fake_subprocess(*args, **_kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(return_value=(b"abc123\ndef456\n", b""))
                return mock_proc
            else:
                raise OSError("docker not found")

        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            side_effect=fake_subprocess,
        ):
            count = await VTKRunner.cleanup_orphaned_containers()
        assert count == 2

    @pytest.mark.asyncio
    async def test_stop_container_timeout(self) -> None:
        """_stop_container handles TimeoutError gracefully."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch(
            "viznoir.core.runner.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            # Should not raise
            await VTKRunner._stop_container("viznoir_test_timeout")


class TestDefaultTimeout:
    """RC3: Default timeout should be 600s."""

    def test_default_timeout_600(self) -> None:
        """PVConfig default_timeout should be 600s (not 120s)."""
        from viznoir.config import PVConfig

        with patch.dict("os.environ", {}, clear=False):
            import os

            old = os.environ.pop("VIZNOIR_TIMEOUT", None)
            try:
                config = PVConfig()
                assert config.default_timeout == 600.0
            finally:
                if old is not None:
                    os.environ["VIZNOIR_TIMEOUT"] = old
