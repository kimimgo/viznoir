"""ParaViewRunner — execute pvpython scripts and collect results."""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from parapilot.config import PVConfig


@dataclass
class RunResult:
    """Result of a pvpython script execution."""

    stdout: str
    stderr: str
    exit_code: int
    output_files: list[Path] = field(default_factory=list)
    output_file_data: dict[str, bytes] = field(default_factory=dict)
    json_result: dict[str, Any] | list[Any] | None = None

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    @property
    def is_cleanup_crash(self) -> bool:
        """Detect VisRTX/VTK cleanup crash (rendering succeeded but exit crashed).

        Pattern: non-zero exit + output files exist + known crash signatures in stderr.
        """
        if self.exit_code == 0 or not self.output_file_data:
            return False
        crash_sigs = (
            "free(): invalid pointer", "double free",
            "munmap_chunk", "vtkXOpenGLRenderWindow",
        )
        return any(sig in self.stderr for sig in crash_sigs)

    def raise_on_error(self) -> None:
        if not self.ok and not self.is_cleanup_crash:
            raise RuntimeError(
                f"pvpython exited with code {self.exit_code}.\nstderr: {self.stderr}"
            )


class ParaViewRunner:
    """Execute pvpython scripts locally or via Docker (GPU EGL / CPU OSMesa)."""

    def __init__(self, config: PVConfig | None = None, mode: str = "auto"):
        self.config = config or PVConfig()
        self.mode = self._detect_mode() if mode == "auto" else mode

    def _detect_mode(self) -> str:
        """'local' if pvpython is available, otherwise 'docker'."""
        if shutil.which(self.config.pvpython_bin):
            return "local"
        return "docker"

    async def execute(
        self,
        script: str,
        timeout: float | None = None,
        extra_files: dict[str, bytes] | None = None,
        extra_mounts: list[str] | None = None,
    ) -> RunResult:
        """Run a pvpython script and return the result.

        Args:
            extra_mounts: Additional host directories to mount read-only
                in Docker mode (each mounted at same path inside container).
        """
        timeout = timeout or self.config.default_timeout

        with tempfile.TemporaryDirectory(prefix="parapilot_", ignore_cleanup_errors=True) as tmpdir:
            tmp = Path(tmpdir)
            script_path = tmp / "pipeline.py"
            script_path.write_text(script, encoding="utf-8")

            if extra_files:
                for name, data in extra_files.items():
                    (tmp / name).write_bytes(data)

            output_dir = tmp / "output"
            output_dir.mkdir()

            if self.mode == "local":
                result = await self._run_local(script_path, output_dir, timeout)
            else:
                result = await self._run_docker(
                    script_path, output_dir, timeout,
                    extra_mounts=extra_mounts or [],
                )

            # Collect output files and read them into memory before tempdir cleanup
            result.output_files = [
                f for f in output_dir.rglob("*") if f.is_file()
            ]
            for f in result.output_files:
                try:
                    result.output_file_data[f.name] = f.read_bytes()
                except (PermissionError, OSError):
                    pass

            # Try to parse JSON from a result file or stdout
            json_file = output_dir / "result.json"
            if json_file.exists():
                result.json_result = json.loads(json_file.read_text(encoding="utf-8"))
            elif result.stdout.strip().startswith(("{", "[")):
                try:
                    result.json_result = json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass

            return result

    async def _run_local(
        self, script_path: Path, output_dir: Path, timeout: float
    ) -> RunResult:
        """Execute pvpython directly via subprocess (GPU EGL or CPU OSMesa)."""
        import os

        env = {
            **os.environ,
            "PARAPILOT_OUTPUT_DIR": str(output_dir),
            "PARAPILOT_DATA_DIR": str(self.config.data_dir),
        }

        # Force offscreen rendering — prevent VTK X11 cleanup crash
        env["VTK_DEFAULT_RENDER_WINDOW_OFFSCREEN"] = "1"

        # GPU (EGL) rendering: set device index for headless EGL
        if self.config.use_gpu:
            env["VTK_DEFAULT_EGL_DEVICE_INDEX"] = str(self.config.gpu_device)
            # Remove DISPLAY to avoid GLX attempts — force EGL path
            env.pop("DISPLAY", None)

        proc = await asyncio.create_subprocess_exec(
            self.config.pvpython_bin,
            "--force-offscreen-rendering",
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return RunResult(stdout="", stderr=f"pvpython timed out after {timeout}s", exit_code=-1)

        return RunResult(
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            exit_code=proc.returncode or 0,
        )

    async def _run_docker(
        self,
        script_path: Path,
        output_dir: Path,
        timeout: float,
        extra_mounts: list[str] | None = None,
    ) -> RunResult:
        """Execute pvpython inside a Docker container (GPU EGL or CPU OSMesa)."""
        import os

        tmpdir = script_path.parent
        container_name = f"parapilot_{uuid.uuid4().hex[:12]}"

        args = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--user", f"{os.getuid()}:{os.getgid()}",
        ]

        # GPU mode: expose NVIDIA GPU to container
        if self.config.use_gpu:
            args.extend(["--gpus", "all"])
            args.extend(["-e", f"VTK_DEFAULT_EGL_DEVICE_INDEX={self.config.gpu_device}"])
            args.extend(["-e", "NVIDIA_VISIBLE_DEVICES=all"])
            args.extend(["-e", "NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics"])

        args.extend([
            "-v", f"{tmpdir}:/work:ro",
            "-v", f"{output_dir}:/output",
            "-v", f"{self.config.data_dir.resolve()}:/data:ro",
            "-e", "PARAPILOT_OUTPUT_DIR=/output",
            "-e", "PARAPILOT_DATA_DIR=/data",
        ])
        # Extra host directories mounted at same path inside container
        for mount_dir in (extra_mounts or []):
            args.extend(["-v", f"{mount_dir}:{mount_dir}:ro"])
        args.extend([
            self.config.docker_image,
            self.config.pvpython_bin, "--force-offscreen-rendering", "/work/pipeline.py",
        ])

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            # Kill the actual Docker container (proc.kill only kills the CLI)
            await self._stop_container(container_name)
            return RunResult(
                stdout="", stderr=f"Docker pvpython timed out after {timeout}s", exit_code=-1
            )

        return RunResult(
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            exit_code=proc.returncode or 0,
        )

    @staticmethod
    async def _stop_container(name: str) -> None:
        """Stop and remove a Docker container by name (best-effort)."""
        for cmd in (["docker", "stop", "-t", "5", name], ["docker", "rm", "-f", name]):
            try:
                p = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(p.communicate(), timeout=15)
            except (asyncio.TimeoutError, OSError):
                pass

    @staticmethod
    async def cleanup_orphaned_containers() -> int:
        """Stop any orphaned parapilot_* containers. Returns count removed."""
        try:
            p = await asyncio.create_subprocess_exec(
                "docker", "ps", "-q", "--filter", "name=parapilot_",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(p.communicate(), timeout=10)
        except (asyncio.TimeoutError, OSError):
            return 0
        ids = stdout.decode().strip().split()
        if not ids:
            return 0
        try:
            rm = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", *ids,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(rm.communicate(), timeout=30)
        except (asyncio.TimeoutError, OSError):
            pass
        return len(ids)
