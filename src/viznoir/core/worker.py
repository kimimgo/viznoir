"""In-process script execution — eliminates subprocess overhead."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from viznoir.core.runner import RunResult


class InProcessExecutor:
    """Execute Python/VTK scripts in the current process.

    Each run() call:
    1. Creates a temporary output directory
    2. Sets VIZNOIR_OUTPUT_DIR in os.environ
    3. Compiles and executes the script with captured stdout/stderr
    4. Collects output files into RunResult
    """

    def run(
        self,
        script: str,
        env_overrides: dict[str, str] | None = None,
        output_dir: Path | None = None,
    ) -> RunResult:
        """Execute a script string in-process and return RunResult."""
        managed = output_dir is None
        tmpdir_ctx: tempfile.TemporaryDirectory[str] | None = (
            tempfile.TemporaryDirectory(prefix="viznoir_ip_", ignore_cleanup_errors=True) if managed else None
        )
        effective_output_dir: Path

        try:
            if managed and tmpdir_ctx is not None:
                tmpdir = tmpdir_ctx.__enter__()
                effective_output_dir = Path(tmpdir) / "output"
                effective_output_dir.mkdir()
            else:
                assert output_dir is not None
                effective_output_dir = output_dir

            # Save and set environment
            saved_env: dict[str, str | None] = {}
            env_vars = {"VIZNOIR_OUTPUT_DIR": str(effective_output_dir)}
            if env_overrides:
                env_vars.update(env_overrides)

            for key, val in env_vars.items():
                saved_env[key] = os.environ.get(key)
                os.environ[key] = val

            # Reset VTK render window singleton before each in-process run
            # to prevent state leakage between consecutive executions.
            if "viznoir.engine.renderer" in sys.modules:
                try:
                    sys.modules["viznoir.engine.renderer"].cleanup()
                except Exception:  # noqa: BLE001
                    pass

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            exit_code = 0

            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    compiled = compile(script, "<pipeline>", "exec")
                    exec(compiled, {"__name__": "__main__"})  # noqa: S102
            except SystemExit as e:
                exit_code = e.code if isinstance(e.code, int) else 1
            except Exception:
                exit_code = 1
                stderr_buf.write(traceback.format_exc())
            finally:
                for key, orig_val in saved_env.items():
                    if orig_val is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = orig_val

            # Collect output files
            result = RunResult(
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
                exit_code=exit_code,
            )
            for f in effective_output_dir.rglob("*"):
                if f.is_file():
                    result.output_files.append(f)
                    try:
                        result.output_file_data[f.name] = f.read_bytes()
                    except (PermissionError, OSError):
                        pass

            # Parse result.json if present
            json_file = effective_output_dir / "result.json"
            if json_file.exists():
                result.json_result = json.loads(json_file.read_text(encoding="utf-8"))

            return result
        finally:
            if tmpdir_ctx is not None:
                tmpdir_ctx.__exit__(None, None, None)
