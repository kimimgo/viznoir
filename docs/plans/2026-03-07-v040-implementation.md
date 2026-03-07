# viznoir v0.4.0 — Core Power Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** VTK native 성능 최적화 + Volume Rendering MCP tool + Manim easing 흡수로 v0.4.0 Core Power 완성

**Architecture:** Worker Pool은 cinematic_render_impl의 `run_in_executor` 패턴을 일반화합니다.
Volume Rendering은 이미 존재하는 `renderer.py:_render_volume()`에 transfer function 프리셋을 추가하고 MCP tool로 노출합니다.
Easing은 `camera_path.py`의 4종 기존 함수를 `anim/easing.py`로 확장(17종)하고 역참조를 연결합니다.

**Tech Stack:** Python 3.10+, VTK 9.4+, concurrent.futures, pytest, asyncio

**Design Doc:** `docs/plans/2026-03-07-viznoir-redesign-vtk-manim.md`

**NOTE:** Parallel Projection은 이미 완전 구현됨 (`CameraConfig.parallel_projection`, `CameraDef.orthographic`,
`apply_camera()` at camera.py:135-149). Phase 1에서 제외.

---

## Task 1: Worker Pool — In-Process Pipeline Execution

현재 모든 파이프라인 실행이 `VTKRunner._run_local()` at runner.py:134-180 에서
`asyncio.create_subprocess_exec(python, script.py)`로 매 호출마다 Python 프로세스 + VTK 모듈 초기화 (500ms-2s).
`cinematic_render_impl` (tools/cinematic.py:83-84)은 이미 `run_in_executor(None, _run)` 패턴으로 in-process 실행 중.
이 패턴을 일반화.

**Files:**
- Create: `src/viznoir/core/worker.py`
- Modify: `src/viznoir/core/runner.py:58-180`
- Test: `tests/test_core/test_worker.py`

### Step 1: Write the failing tests for WorkerPool

```python
# tests/test_core/test_worker.py
"""Tests for core/worker.py — in-process VTK pipeline execution."""

from __future__ import annotations

import pytest

from viznoir.core.worker import InProcessExecutor


class TestInProcessExecutor:
    def test_execute_simple_script(self):
        """Script that writes a result file."""
        executor = InProcessExecutor()
        script = (
            "import json, os\n"
            "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
            "with open(os.path.join(out, 'result.json'), 'w') as f:\n"
            "    json.dump({'status': 'ok'}, f)\n"
        )
        result = executor.run(script)
        assert result.exit_code == 0
        assert "result.json" in result.output_file_data

    def test_execute_script_with_error(self):
        """Script that raises should return non-zero exit_code."""
        executor = InProcessExecutor()
        script = "raise RuntimeError('boom')"
        result = executor.run(script)
        assert result.exit_code != 0
        assert "boom" in result.stderr

    def test_captures_stdout(self):
        executor = InProcessExecutor()
        script = "print('hello from worker')"
        result = executor.run(script)
        assert "hello from worker" in result.stdout

    def test_output_dir_set_in_env(self):
        executor = InProcessExecutor()
        script = (
            "import os\n"
            "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
            "assert os.path.isdir(out)\n"
            "with open(os.path.join(out, 'test.txt'), 'w') as f:\n"
            "    f.write('ok')\n"
        )
        result = executor.run(script)
        assert result.exit_code == 0
        assert "test.txt" in result.output_file_data

    def test_isolation_between_runs(self):
        """Each run should have its own output directory."""
        executor = InProcessExecutor()
        script1 = (
            "import os\n"
            "with open(os.path.join(os.environ['VIZNOIR_OUTPUT_DIR'], 'a.txt'), 'w') as f:\n"
            "    f.write('a')\n"
        )
        script2 = (
            "import os\n"
            "with open(os.path.join(os.environ['VIZNOIR_OUTPUT_DIR'], 'b.txt'), 'w') as f:\n"
            "    f.write('b')\n"
        )
        r1 = executor.run(script1)
        r2 = executor.run(script2)
        assert "a.txt" in r1.output_file_data
        assert "b.txt" in r2.output_file_data
        assert "a.txt" not in r2.output_file_data
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_core/test_worker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'viznoir.core.worker'`

### Step 3: Implement InProcessExecutor

```python
# src/viznoir/core/worker.py
"""In-process script execution — eliminates subprocess overhead."""

from __future__ import annotations

import io
import json
import os
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
        tmpdir_ctx = (
            tempfile.TemporaryDirectory(prefix="viznoir_ip_", ignore_cleanup_errors=True)
            if managed
            else None
        )

        try:
            if managed:
                tmpdir = tmpdir_ctx.__enter__()
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()

            # Save and set environment
            saved_env: dict[str, str | None] = {}
            env_vars = {"VIZNOIR_OUTPUT_DIR": str(output_dir)}
            if env_overrides:
                env_vars.update(env_overrides)

            for key, val in env_vars.items():
                saved_env[key] = os.environ.get(key)
                os.environ[key] = val

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            exit_code = 0

            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    code = compile(script, "<pipeline>", "exec")
                    exec(code, {"__name__": "__main__"})  # noqa: S102
            except SystemExit as e:
                exit_code = e.code if isinstance(e.code, int) else 1
            except Exception:
                exit_code = 1
                stderr_buf.write(traceback.format_exc())
            finally:
                for key, val in saved_env.items():
                    if val is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = val

            # Collect output files
            result = RunResult(
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
                exit_code=exit_code,
            )
            for f in output_dir.rglob("*"):
                if f.is_file():
                    result.output_files.append(f)
                    try:
                        result.output_file_data[f.name] = f.read_bytes()
                    except (PermissionError, OSError):
                        pass

            # Parse result.json if present
            json_file = output_dir / "result.json"
            if json_file.exists():
                result.json_result = json.loads(
                    json_file.read_text(encoding="utf-8")
                )

            return result
        finally:
            if tmpdir_ctx is not None:
                tmpdir_ctx.__exit__(None, None, None)
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_core/test_worker.py -v`
Expected: All 5 tests PASS

### Step 5: Integrate InProcessExecutor into VTKRunner

Modify `src/viznoir/core/runner.py`:

1. Add import: `from viznoir.core.worker import InProcessExecutor`
2. In `VTKRunner.__init__` (after line 63), add: `self._executor: InProcessExecutor | None = None`
3. Add new method `_run_inprocess()` after `_run_local()`:

```python
    async def _run_inprocess(self, script: str, output_dir: Path, timeout: float) -> RunResult:
        """Execute script in-process via InProcessExecutor."""
        import asyncio

        if self._executor is None:
            from viznoir.core.worker import InProcessExecutor
            self._executor = InProcessExecutor()

        env_overrides: dict[str, str] = {}
        if self.config.data_dir:
            env_overrides["VIZNOIR_DATA_DIR"] = str(self.config.data_dir)

        vtk_backend = self.config.vtk_backend
        if vtk_backend == "auto":
            vtk_backend = "egl" if self.config.use_gpu else "osmesa"
        if vtk_backend == "egl":
            env_overrides["VTK_DEFAULT_OPENGL_WINDOW"] = "vtkEGLRenderWindow"
            env_overrides["VTK_DEFAULT_EGL_DEVICE_INDEX"] = str(self.config.gpu_device)
        elif vtk_backend == "osmesa":
            env_overrides["VTK_DEFAULT_OPENGL_WINDOW"] = "vtkOSOpenGLRenderWindow"

        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(
                None, self._executor.run, script, env_overrides, output_dir
            ),
            timeout=timeout,
        )
```

4. In `execute()` method (line 99), update local mode to use in-process:

```python
            if self.mode == "local":
                result = await self._run_inprocess(script, output_dir, timeout)
```

Keep `_run_local()` renamed to `_run_subprocess()` as fallback.

### Step 6: Write integration test

Add to `tests/test_core/test_worker.py`:

```python
class TestVTKRunnerInProcess:
    @pytest.mark.asyncio
    async def test_local_mode_uses_inprocess(self):
        from pathlib import Path
        from viznoir.config import PVConfig
        from viznoir.core.runner import VTKRunner

        config = PVConfig(output_dir=Path("/tmp/viznoir-test"))
        runner = VTKRunner(config=config, mode="local")

        script = (
            "import json, os\n"
            "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
            "with open(os.path.join(out, 'result.json'), 'w') as f:\n"
            "    json.dump({'answer': 42}, f)\n"
        )
        result = await runner.execute(script)
        assert result.ok
        assert result.json_result == {"answer": 42}
```

### Step 7: Run all runner tests

Run: `pytest tests/test_core/test_worker.py tests/test_core/test_runner.py -v`
Expected: All PASS

### Step 8: Commit

```bash
git add src/viznoir/core/worker.py tests/test_core/test_worker.py
git add -u src/viznoir/core/runner.py
git commit -m "feat: add InProcessExecutor for subprocess-free pipeline execution"
```

---

## Task 2: Volume Rendering — Transfer Function Presets + MCP Tool

`renderer.py:_render_volume()` (lines 214-285) already exists with hardcoded opacity ramp.
Add transfer function presets and expose as `volume_render` MCP tool.

**Files:**
- Create: `src/viznoir/engine/transfer_functions.py`
- Create: `src/viznoir/tools/volume.py`
- Modify: `src/viznoir/engine/renderer.py:23-42,259-264` (add transfer_preset field, use preset)
- Modify: `src/viznoir/server.py` (register volume_render tool)
- Test: `tests/test_engine/test_transfer_functions.py`
- Test: `tests/test_tools/test_volume_tool.py`

### Step 1: Write failing tests for transfer function presets

```python
# tests/test_engine/test_transfer_functions.py
"""Tests for transfer function presets."""

from __future__ import annotations

import pytest

from viznoir.engine.transfer_functions import (
    TRANSFER_PRESETS,
    build_opacity_function,
    list_presets,
)


class TestTransferPresets:
    def test_list_presets_returns_sorted(self):
        presets = list_presets()
        assert presets == sorted(presets)
        assert len(presets) >= 5

    def test_known_presets_exist(self):
        presets = list_presets()
        for name in ["ct_bone", "ct_tissue", "mri_brain", "thermal", "generic"]:
            assert name in presets, f"Missing preset: {name}"

    @pytest.mark.parametrize("preset_name", list(TRANSFER_PRESETS.keys()))
    def test_each_preset_has_required_keys(self, preset_name):
        preset = TRANSFER_PRESETS[preset_name]
        assert "opacity_points" in preset
        assert "description" in preset
        points = preset["opacity_points"]
        assert len(points) >= 2
        for val, opacity in points:
            assert 0.0 <= val <= 1.0
            assert 0.0 <= opacity <= 1.0


class TestBuildOpacityFunction:
    def test_returns_vtk_piecewise(self):
        import vtk
        otf = build_opacity_function("generic", scalar_range=(0.0, 100.0))
        assert isinstance(otf, vtk.vtkPiecewiseFunction)

    def test_custom_range_maps_correctly(self):
        otf = build_opacity_function("generic", scalar_range=(10.0, 50.0))
        assert otf.GetSize() >= 2

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="no_such_preset"):
            build_opacity_function("no_such_preset", scalar_range=(0.0, 1.0))
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_engine/test_transfer_functions.py -v`
Expected: FAIL with `ModuleNotFoundError`

### Step 3: Implement transfer function presets

```python
# src/viznoir/engine/transfer_functions.py
"""Transfer function presets for volume rendering."""

from __future__ import annotations

from typing import Any

import vtk

TRANSFER_PRESETS: dict[str, dict[str, Any]] = {
    "generic": {
        "description": "General-purpose ramp — transparent low, opaque high",
        "opacity_points": [
            (0.0, 0.0),
            (0.2, 0.0),
            (0.4, 0.05),
            (1.0, 0.5),
        ],
    },
    "ct_bone": {
        "description": "CT scan — bones opaque, soft tissue transparent",
        "opacity_points": [
            (0.0, 0.0),
            (0.3, 0.0),
            (0.5, 0.0),
            (0.7, 0.1),
            (0.85, 0.6),
            (1.0, 0.9),
        ],
    },
    "ct_tissue": {
        "description": "CT scan — soft tissue visible, bones semi-transparent",
        "opacity_points": [
            (0.0, 0.0),
            (0.15, 0.0),
            (0.3, 0.15),
            (0.5, 0.3),
            (0.7, 0.1),
            (1.0, 0.05),
        ],
    },
    "mri_brain": {
        "description": "MRI brain — mid-range intensities highlighted",
        "opacity_points": [
            (0.0, 0.0),
            (0.1, 0.0),
            (0.3, 0.1),
            (0.5, 0.4),
            (0.7, 0.3),
            (0.9, 0.1),
            (1.0, 0.0),
        ],
    },
    "thermal": {
        "description": "Thermal/CFD — smooth gradient for temperature fields",
        "opacity_points": [
            (0.0, 0.02),
            (0.25, 0.05),
            (0.5, 0.15),
            (0.75, 0.35),
            (1.0, 0.6),
        ],
    },
    "isosurface_like": {
        "description": "Sharp band — mimics isosurface at a narrow range",
        "opacity_points": [
            (0.0, 0.0),
            (0.45, 0.0),
            (0.48, 0.8),
            (0.52, 0.8),
            (0.55, 0.0),
            (1.0, 0.0),
        ],
    },
}


def list_presets() -> list[str]:
    """Return sorted list of available transfer function preset names."""
    return sorted(TRANSFER_PRESETS.keys())


def build_opacity_function(
    preset_name: str,
    scalar_range: tuple[float, float],
    opacity_scale: float = 1.0,
) -> vtk.vtkPiecewiseFunction:
    """Build vtkPiecewiseFunction from a named preset."""
    if preset_name not in TRANSFER_PRESETS:
        raise KeyError(f"Unknown transfer function preset: {preset_name}")

    preset = TRANSFER_PRESETS[preset_name]
    lo, hi = scalar_range
    span = hi - lo

    otf = vtk.vtkPiecewiseFunction()
    for rel_val, opacity in preset["opacity_points"]:
        otf.AddPoint(lo + rel_val * span, opacity * opacity_scale)

    return otf
```

### Step 4: Run tests

Run: `pytest tests/test_engine/test_transfer_functions.py -v`
Expected: All PASS

### Step 5: Commit

```bash
git add src/viznoir/engine/transfer_functions.py tests/test_engine/test_transfer_functions.py
git commit -m "feat: add transfer function presets for volume rendering"
```

### Step 6: Integrate presets into renderer and add volume tool

**renderer.py:** Add `transfer_preset: str = "generic"` to `RenderConfig` dataclass (after line ~35).
In `_render_volume()` lines 259-264, replace hardcoded otf:
```python
        from .transfer_functions import build_opacity_function
        otf = build_opacity_function(self._config.transfer_preset, (lo, hi), self._config.opacity)
```

**tools/volume.py:** Create thin wrapper around `cinematic_render_impl`:

```python
# src/viznoir/tools/volume.py
"""volume_render tool — volume rendering with transfer function presets."""

from __future__ import annotations

from viznoir.core.runner import VTKRunner
from viznoir.engine.transfer_functions import TRANSFER_PRESETS


async def volume_render_impl(
    file_path: str,
    runner: VTKRunner,
    *,
    field_name: str | None = None,
    transfer_preset: str = "generic",
    colormap: str = "viridis",
    quality: str = "standard",
    lighting: str | None = "cinematic",
    background: str | None = "dark_gradient",
    width: int | None = None,
    height: int | None = None,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    output_filename: str = "volume.png",
) -> bytes:
    """Render volumetric data with transfer function presets. Returns PNG bytes."""
    if transfer_preset not in TRANSFER_PRESETS:
        raise KeyError(f"Unknown transfer function preset: {transfer_preset}")

    from viznoir.tools.cinematic import cinematic_render_impl

    return await cinematic_render_impl(
        file_path, runner,
        field_name=field_name, colormap=colormap,
        quality=quality, lighting=lighting, background=background,
        width=width, height=height, scalar_range=scalar_range,
        timestep=timestep, output_filename=output_filename,
    )
```

**server.py:** Register `volume_render` MCP tool (after cinematic_render, ~line 650):

```python
@mcp.tool()
async def volume_render(
    file_path: str,
    field_name: str | None = None,
    transfer_preset: str = "generic",
    colormap: str = "viridis",
    quality: str = "standard",
    lighting: str | None = "cinematic",
    background: str | None = "dark_gradient",
    width: int | None = None,
    height: int | None = None,
    scalar_range: list[float] | None = None,
    timestep: float | str | None = None,
    output_filename: str = "volume.png",
) -> Image:
    """Volume render 3D data (CT, MRI, CFD fields) with transfer function presets.

    Presets: generic, ct_bone, ct_tissue, mri_brain, thermal, isosurface_like

    Args:
        file_path: Path to volumetric data (VTI, VTK structured grid, etc.)
        field_name: Scalar field to render, None for active scalars
        transfer_preset: Opacity preset (ct_bone, ct_tissue, mri_brain, thermal, generic, isosurface_like)
        colormap: Color map preset
        quality: Render quality (draft/standard/cinematic/ultra/publication)
        lighting: Lighting preset
        background: Background preset
        width: Image width in pixels
        height: Image height in pixels
        scalar_range: [min, max] for color scale
        timestep: Specific timestep, "latest", or None
        output_filename: Output filename
    """
    file_path = _validate_file_path(file_path)
    logger.debug("tool.volume_render: file=%s preset=%s", file_path, transfer_preset)
    t0 = time.monotonic()
    from viznoir.tools.volume import volume_render_impl

    png_bytes = await volume_render_impl(
        file_path, _runner,
        field_name=field_name, transfer_preset=transfer_preset,
        colormap=colormap, quality=quality, lighting=lighting,
        background=background, width=width, height=height,
        scalar_range=scalar_range, timestep=timestep,
        output_filename=output_filename,
    )
    logger.debug("tool.volume_render: done in %.2fs", time.monotonic() - t0)
    if png_bytes:
        return Image(data=png_bytes, format="png")
    raise RuntimeError("Volume rendering failed: no image produced")
```

### Step 7: Write volume tool test

```python
# tests/test_tools/test_volume_tool.py
"""Tests for volume_render MCP tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVolumeRenderImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.volume.cinematic_render_impl")
    async def test_calls_cinematic(self, mock_cine):
        from viznoir.tools.volume import volume_render_impl

        mock_cine.return_value = b"fake-png"
        runner = MagicMock()

        result = await volume_render_impl(
            file_path="/data/head.vti",
            runner=runner,
            field_name="scalars",
            transfer_preset="ct_bone",
        )
        assert result == b"fake-png"
        mock_cine.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_preset_raises(self):
        from viznoir.tools.volume import volume_render_impl

        runner = MagicMock()
        with pytest.raises(KeyError, match="no_such"):
            await volume_render_impl(
                file_path="/data/head.vti",
                runner=runner,
                transfer_preset="no_such",
            )
```

### Step 8: Run tests

Run: `pytest tests/test_tools/test_volume_tool.py tests/test_engine/test_transfer_functions.py -v`
Expected: All PASS

### Step 9: Commit

```bash
git add src/viznoir/tools/volume.py tests/test_tools/test_volume_tool.py
git add -u src/viznoir/engine/renderer.py src/viznoir/server.py
git commit -m "feat: add volume_render MCP tool with 6 transfer function presets"
```

---

## Task 3: Easing Functions — Expand & Unify

기존 `camera_path.py:33-59`의 4종 easing을 `anim/easing.py`로 확장(17종, Manim rate_functions 기반).
`EASING_FUNCTIONS` dict를 새 모듈에서 import하여 하위 호환 유지.

**Files:**
- Create: `src/viznoir/anim/__init__.py`
- Create: `src/viznoir/anim/easing.py`
- Modify: `src/viznoir/engine/camera_path.py:29-59` (import 교체)
- Test: `tests/test_anim/__init__.py`
- Test: `tests/test_anim/test_easing.py`

### Step 1: Write failing tests

```python
# tests/test_anim/__init__.py (empty file)
```

```python
# tests/test_anim/test_easing.py
"""Tests for anim/easing.py — Manim-inspired easing functions."""

from __future__ import annotations

import pytest

from viznoir.anim.easing import EASING_FUNCTIONS, smooth


class TestEasingEndpoints:
    """All easing functions must satisfy f(0)=0."""

    @pytest.mark.parametrize("name", list(EASING_FUNCTIONS.keys()))
    def test_f0_equals_0(self, name):
        func = EASING_FUNCTIONS[name]
        assert func(0.0) == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.parametrize(
        "name",
        [n for n in EASING_FUNCTIONS if n != "there_and_back"],
    )
    def test_f1_equals_1(self, name):
        """f(1)=1 for all except there_and_back (which returns to 0)."""
        func = EASING_FUNCTIONS[name]
        assert func(1.0) == pytest.approx(1.0, abs=1e-10)


class TestEasingCount:
    def test_at_least_17_functions(self):
        assert len(EASING_FUNCTIONS) >= 17

    def test_all_callable(self):
        for name, func in EASING_FUNCTIONS.items():
            assert callable(func), f"{name} is not callable"


class TestEasingBehavior:
    def test_smooth_is_slow_at_endpoints(self):
        assert smooth(0.01) < 0.01
        assert smooth(0.99) > 0.99

    def test_ease_in_sine_slow_start(self):
        from viznoir.anim.easing import ease_in_sine
        assert ease_in_sine(0.1) < 0.1

    def test_ease_out_sine_slow_end(self):
        from viznoir.anim.easing import ease_out_sine
        assert ease_out_sine(0.9) > 0.9

    def test_there_and_back_returns_to_zero(self):
        from viznoir.anim.easing import there_and_back
        assert there_and_back(0.0) == pytest.approx(0.0)
        assert there_and_back(0.5) == pytest.approx(1.0, abs=0.05)
        assert there_and_back(1.0) == pytest.approx(0.0, abs=1e-10)

    def test_rush_into_accelerating(self):
        from viznoir.anim.easing import rush_into
        assert rush_into(0.5) < 0.5

    def test_rush_from_decelerating(self):
        from viznoir.anim.easing import rush_from
        assert rush_from(0.5) > 0.5

    def test_linear_identity(self):
        from viznoir.anim.easing import linear
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert linear(t) == pytest.approx(t)

    def test_double_smooth_stronger(self):
        from viznoir.anim.easing import double_smooth
        assert double_smooth(0.01) < smooth(0.01)


class TestBackwardsCompatibility:
    def test_camera_path_easing_still_works(self):
        from viznoir.engine.camera_path import EASING_FUNCTIONS as cam_easings
        assert "linear" in cam_easings
        assert "ease_in" in cam_easings
        assert "ease_out" in cam_easings
        assert "ease_in_out" in cam_easings
        assert "smooth" in cam_easings
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_anim/test_easing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'viznoir.anim'`

### Step 3: Implement 17 easing functions

```python
# src/viznoir/anim/__init__.py
"""viznoir.anim — animation primitives (easing, timeline, transitions)."""
```

```python
# src/viznoir/anim/easing.py
"""Easing functions for animation — inspired by Manim rate_functions.

All functions: f(0) = 0, f(1) = 1, with varying interpolation curves.
Exception: there_and_back returns to 0 at t=1.

Reference: github.com/ManimCommunity/manim  manim/utils/rate_functions.py
"""

from __future__ import annotations

import math
from typing import Callable


def linear(t: float) -> float:
    """Constant speed."""
    return t


def smooth(t: float) -> float:
    """Smooth ease-in-out (smoothstep)."""
    return t * t * (3.0 - 2.0 * t)


def double_smooth(t: float) -> float:
    """Extra-smooth — applies smooth twice."""
    if t < 0.5:
        return smooth(2.0 * t) / 2.0
    return (smooth(2.0 * t - 1.0) + 1.0) / 2.0


def ease_in_sine(t: float) -> float:
    """Sine-based slow start."""
    return 1.0 - math.cos(t * math.pi / 2.0)


def ease_out_sine(t: float) -> float:
    """Sine-based slow end."""
    return math.sin(t * math.pi / 2.0)


def ease_in_out_sine(t: float) -> float:
    """Sine-based slow start and end."""
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out."""
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out."""
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


def ease_in_cubic(t: float) -> float:
    """Cubic ease-in."""
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out."""
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_in_expo(t: float) -> float:
    """Exponential ease-in."""
    return 0.0 if t == 0.0 else 2.0 ** (10.0 * t - 10.0)


def ease_out_expo(t: float) -> float:
    """Exponential ease-out."""
    return 1.0 if t == 1.0 else 1.0 - 2.0 ** (-10.0 * t)


def there_and_back(t: float) -> float:
    """Go to 1.0 at t=0.5, return to 0.0 at t=1.0 (ping-pong)."""
    return smooth(2.0 * t) if t < 0.5 else smooth(2.0 * (1.0 - t))


def rush_into(t: float) -> float:
    """Accelerating — slow start, fast end."""
    return 2.0 * smooth(t / 2.0)


def rush_from(t: float) -> float:
    """Decelerating — fast start, slow end."""
    return 2.0 * smooth(t / 2.0 + 0.5) - 1.0


EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "linear": linear,
    "smooth": smooth,
    "double_smooth": double_smooth,
    "ease_in": ease_in_quad,
    "ease_out": ease_out_quad,
    "ease_in_out": ease_in_out_cubic,
    "ease_in_sine": ease_in_sine,
    "ease_out_sine": ease_out_sine,
    "ease_in_out_sine": ease_in_out_sine,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
    "ease_in_expo": ease_in_expo,
    "ease_out_expo": ease_out_expo,
    "there_and_back": there_and_back,
    "rush_into": rush_into,
    "rush_from": rush_from,
}
```

### Step 4: Run tests

Run: `pytest tests/test_anim/test_easing.py -v`
Expected: All PASS (except backwards compat test — camera_path not yet updated)

### Step 5: Commit easing module

```bash
git add src/viznoir/anim/__init__.py src/viznoir/anim/easing.py
git add tests/test_anim/__init__.py tests/test_anim/test_easing.py
git commit -m "feat: add 17 Manim-inspired easing functions (viznoir.anim.easing)"
```

### Step 6: Wire camera_path.py to new easing module

Modify `src/viznoir/engine/camera_path.py`:

**Replace lines 29-59** (the 4 local `_ease_*` functions + `EASING_FUNCTIONS` dict) with:

```python
# ---------------------------------------------------------------------------
# Easing functions — delegated to viznoir.anim.easing
# ---------------------------------------------------------------------------

from viznoir.anim.easing import (
    EASING_FUNCTIONS,
    ease_in_quad as _ease_in,
    ease_in_out_cubic as _ease_in_out,
    ease_out_quad as _ease_out,
    linear as _ease_linear,
)
```

This keeps the private `_ease_*` names available for any internal references
while delegating to the canonical `viznoir.anim.easing` module.

### Step 7: Run backwards compatibility tests

Run: `pytest tests/test_engine/test_camera_path.py tests/test_anim/test_easing.py -v`
Expected: All PASS

### Step 8: Commit

```bash
git add -u src/viznoir/engine/camera_path.py
git commit -m "refactor: unify easing — camera_path delegates to viznoir.anim.easing"
```

---

## Task 4: Update Documentation & Metrics

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/plans/2026-03-07-viznoir-redesign-vtk-manim.md`

### Step 1: Update CLAUDE.md

- Key Metrics: Tools 18 → 19
- Architecture: add `anim/` and `core/worker.py` to tree
- Note parallel projection already implemented

### Step 2: Update design doc

- Mark Parallel Projection as "DONE (pre-existing)"
- Update Phase 1 checklist

### Step 3: Commit

```bash
git add CLAUDE.md docs/plans/2026-03-07-viznoir-redesign-vtk-manim.md
git commit -m "docs: update for v0.4.0 — 19 tools, anim package, worker pool"
```

---

## Task 5: Full Test Suite Verification

### Step 1: Lint

Run: `ruff check src/ tests/`
Expected: 0 errors

### Step 2: Type check

Run: `mypy src/viznoir/ --ignore-missing-imports`
Expected: 0 errors

### Step 3: Full test suite

Run: `pytest --cov=viznoir --cov-report=term-missing -q`
Expected: 1134+ existing tests pass + ~25 new tests pass, coverage >= 80%

### Step 4: Fix any issues and commit

```bash
git add -u
git commit -m "fix: resolve lint and type issues for v0.4.0"
```

---

## Summary

| Task | Component | New Files | Modified Files | New Tests |
|------|-----------|-----------|----------------|-----------|
| 1 | Worker Pool | `core/worker.py` | `core/runner.py` | ~6 |
| 2 | Volume Render | `engine/transfer_functions.py`, `tools/volume.py` | `engine/renderer.py`, `server.py` | ~6 |
| 3 | Easing | `anim/__init__.py`, `anim/easing.py` | `engine/camera_path.py` | ~13 |
| 4 | Docs | — | `CLAUDE.md`, design doc | — |
| 5 | Verify | — | — | Full suite |

**Total commits:** ~7
**New tests:** ~25
**New LOC:** ~400
