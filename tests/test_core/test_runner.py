"""Tests for ParaViewRunner (no Docker or pvpython needed)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from parapilot.core.runner import ParaViewRunner, RunResult


class TestDockerContainerCleanup:
    """RC1: Docker container must be stopped on timeout, not just CLI process."""

    @pytest.mark.asyncio
    async def test_docker_timeout_calls_stop_container(self) -> None:
        """On timeout, _run_docker must call _stop_container with the container name."""
        runner = ParaViewRunner(mode="docker")

        # First call raises TimeoutError (inside wait_for), second returns normally (post-kill drain)
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=[asyncio.TimeoutError, (b"", b"")])
        mock_proc.kill = MagicMock()

        with (
            patch("parapilot.core.runner.asyncio.create_subprocess_exec", return_value=mock_proc),
            patch.object(runner, "_stop_container", new_callable=AsyncMock) as mock_stop,
            patch("parapilot.core.runner.uuid") as mock_uuid,
        ):
            mock_uuid.uuid4.return_value = MagicMock(hex="abcdef123456")
            from pathlib import Path
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "pipeline.py"
                script.write_text("pass")
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()

                result = await runner._run_docker(script, output_dir, timeout=1.0)

        assert result.exit_code == -1
        assert "timed out" in result.stderr
        mock_proc.kill.assert_called_once()
        mock_stop.assert_awaited_once_with("parapilot_abcdef123456")

    @pytest.mark.asyncio
    async def test_docker_run_includes_container_name(self) -> None:
        """docker run args must include --name parapilot_*."""
        runner = ParaViewRunner(mode="docker")

        captured_args: list[str] = []

        async def fake_subprocess(*args: str, **_kw: object) -> AsyncMock:
            captured_args.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            return mock_proc

        with (
            patch("parapilot.core.runner.asyncio.create_subprocess_exec", side_effect=fake_subprocess),
            patch("parapilot.core.runner.uuid") as mock_uuid,
        ):
            mock_uuid.uuid4.return_value = MagicMock(hex="abcdef123456")
            from pathlib import Path
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "pipeline.py"
                script.write_text("pass")
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()

                await runner._run_docker(script, output_dir, timeout=10.0)

        assert "--name" in captured_args
        name_idx = captured_args.index("--name")
        assert captured_args[name_idx + 1] == "parapilot_abcdef123456"

    @pytest.mark.asyncio
    async def test_stop_container_best_effort(self) -> None:
        """_stop_container should not raise even if docker commands fail."""
        with patch(
            "parapilot.core.runner.asyncio.create_subprocess_exec",
            side_effect=OSError("docker not found"),
        ):
            # Should not raise
            await ParaViewRunner._stop_container("parapilot_test")

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_no_containers(self) -> None:
        """cleanup_orphaned_containers returns 0 when no containers found."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "parapilot.core.runner.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            count = await ParaViewRunner.cleanup_orphaned_containers()
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
            "parapilot.core.runner.asyncio.create_subprocess_exec",
            side_effect=fake_subprocess,
        ):
            count = await ParaViewRunner.cleanup_orphaned_containers()
        assert count == 2


class TestFfmpegTimeout:
    """RC2: ffmpeg timeout must be handled gracefully."""

    @pytest.mark.asyncio
    async def test_compile_video_ffmpeg_timeout(self) -> None:
        """compile_video should return error on ffmpeg timeout, not crash."""
        from parapilot.pipeline.engine import compile_video

        # First call raises TimeoutError (inside wait_for), second returns normally (post-kill drain)
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=[asyncio.TimeoutError, (b"", b"")])
        mock_proc.kill = MagicMock()

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("parapilot.pipeline.engine.asyncio.create_subprocess_exec", return_value=mock_proc),
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

        from parapilot.server import _protect_stdout

        # Save original state
        orig_stdout = sys.stdout
        orig_fd1_stat = os.fstat(1)

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


class TestDefaultTimeout:
    """RC3: Default timeout should be 600s."""

    def test_default_timeout_600(self) -> None:
        """PVConfig default_timeout should be 600s (not 120s)."""
        from parapilot.config import PVConfig

        with patch.dict("os.environ", {}, clear=False):
            import os
            old = os.environ.pop("PARAPILOT_TIMEOUT", None)
            try:
                config = PVConfig()
                assert config.default_timeout == 600.0
            finally:
                if old is not None:
                    os.environ["PARAPILOT_TIMEOUT"] = old
