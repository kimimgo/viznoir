"""Pipeline Engine — compile and execute PipelineDefinition."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

from parapilot.core.compiler import ScriptCompiler
from parapilot.core.output import OutputHandler, PipelineResult
from parapilot.core.registry import get_filter, get_reader
from parapilot.core.runner import ParaViewRunner
from parapilot.pipeline.models import PipelineDefinition

# ProgrammableFilter is disabled by default (arbitrary code execution risk).
# Set PARAPILOT_ALLOW_PROGRAMMABLE=1 to enable it.
_ALLOW_PROGRAMMABLE = os.getenv("PARAPILOT_ALLOW_PROGRAMMABLE", "0") == "1"


def validate_pipeline(pipeline: PipelineDefinition) -> list[str]:
    """Validate a pipeline definition. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    # Validate source file format
    try:
        get_reader(pipeline.source.file)
    except ValueError as e:
        errors.append(str(e))

    # Validate each filter step
    for i, step in enumerate(pipeline.pipeline):
        if step.filter == "ProgrammableFilter" and not _ALLOW_PROGRAMMABLE:
            errors.append(
                f"Step {i}: ProgrammableFilter is disabled for security. "
                "Set PARAPILOT_ALLOW_PROGRAMMABLE=1 to enable."
            )
            continue
        try:
            schema = get_filter(step.filter)
            param_defs = schema["params"]
            for key, defn in param_defs.items():
                if defn.get("required") and key not in step.params:
                    errors.append(f"Step {i} ({step.filter}): missing required param '{key}'")
        except KeyError as e:
            errors.append(f"Step {i}: {e}")

    # Validate output
    out = pipeline.output
    if out.type == "image" and out.render is None:
        errors.append("Output type 'image' requires 'render' definition")
    if out.type == "animation" and out.animation is None:
        errors.append("Output type 'animation' requires 'animation' definition")
    if out.type == "export" and out.export_format is None:
        errors.append("Output type 'export' requires 'export_format'")
    if out.type == "split_animation":
        if out.split_animation is None:
            errors.append("Output type 'split_animation' requires 'split_animation' definition")
        else:
            sa = out.split_animation
            render_count = 0
            for i, pane in enumerate(sa.panes):
                if pane.row < 0 or pane.row >= sa.layout.rows:
                    errors.append(f"Pane {i}: row {pane.row} out of range [0, {sa.layout.rows})")
                if pane.col < 0 or pane.col >= sa.layout.cols:
                    errors.append(f"Pane {i}: col {pane.col} out of range [0, {sa.layout.cols})")
                if pane.type == "render":
                    if pane.render_pane is None:
                        errors.append(f"Pane {i}: type 'render' requires 'render_pane'")
                    else:
                        render_count += 1
                elif pane.type == "graph":
                    if pane.graph_pane is None:
                        errors.append(f"Pane {i}: type 'graph' requires 'graph_pane'")
            if render_count == 0:
                errors.append("split_animation requires at least one render pane")

    return errors


async def execute_split_animation(
    definition: PipelineDefinition,
    runner: ParaViewRunner,
    compiler: ScriptCompiler | None = None,
    output_handler: OutputHandler | None = None,
) -> PipelineResult:
    """Execute a split-pane animation pipeline (two-phase).

    Phase 1: pvpython renders individual pane frames + extracts stats.
    Phase 2: Compositor composes frames and generates GIF.
    """
    import json as _json

    from parapilot.core.compositor import Compositor

    compiler = compiler or ScriptCompiler()
    output_handler = output_handler or OutputHandler()

    # 1. Validate
    errors = validate_pipeline(definition)
    if errors:
        raise ValueError(f"Invalid pipeline: {'; '.join(errors)}")

    split_anim = definition.output.split_animation
    if split_anim is None:
        raise ValueError("split_animation definition is required")

    # 2. Compile & Execute (Phase 1 — pvpython)
    script = compiler.compile(definition)
    run_result = await runner.execute(script)
    run_result.raise_on_error()

    # 3. Parse result.json for frame_count
    result_data: dict[str, object] = {}
    if run_result.json_result and isinstance(run_result.json_result, dict):
        result_data = run_result.json_result

    raw_frame_count = result_data.get("frame_count", 0)
    frame_count = int(raw_frame_count) if isinstance(raw_frame_count, (int, float, str)) else 0

    # Parse effective_fps (from frame deduplication)
    raw_effective_fps = result_data.get("effective_fps")
    effective_fps: float | None = None
    if isinstance(raw_effective_fps, (int, float)):
        effective_fps = float(raw_effective_fps)

    # 4. Parse stats.json
    stats: dict[str, object] = {}
    stats_bytes = run_result.output_file_data.get("stats.json")
    if stats_bytes:
        stats = _json.loads(stats_bytes.decode("utf-8"))

    # 5. Compose (Phase 2 — PIL + matplotlib)
    compositor = Compositor(split_anim)
    composed_bytes, gif_bytes = compositor.compose_all(
        run_result.output_file_data, stats, frame_count, effective_fps=effective_fps
    )

    return PipelineResult(
        output_type="split_animation",
        json_data={
            "type": "split_animation",
            "frame_count": frame_count,
            "composed_frame_count": len(composed_bytes),
            "gif_size": len(gif_bytes) if gif_bytes else 0,
            "fps": split_anim.fps,
            "speed_factor": split_anim.speed_factor,
        },
        image_bytes=gif_bytes,
        raw=run_result,
    )


async def compile_video(
    frame_data: dict[str, bytes],
    fps: float,
    output_format: str = "mp4",
    quality: int = 23,
    text_overlay: str | None = None,
) -> tuple[bytes | None, str | None]:
    """Compile PNG frames into video using ffmpeg.

    Uses create_subprocess_exec (array args, no shell) for safety.

    Returns:
        Tuple of (video_bytes, error_message). If ffmpeg is unavailable,
        returns (None, "ffmpeg not found").
    """
    if not shutil.which("ffmpeg"):
        return None, "ffmpeg not found — install ffmpeg to enable video output"

    # Sort frame files by name
    frame_files = sorted(
        (name, data) for name, data in frame_data.items()
        if name.endswith(".png") and "frame_" in name
    )
    if not frame_files:
        return None, "No frame files found"

    with tempfile.TemporaryDirectory(prefix="parapilot_video_") as tmpdir:
        tmp = Path(tmpdir)

        # Write frames to disk
        for name, data in frame_files:
            (tmp / name).write_bytes(data)

        # Determine output extension and codec
        ext = output_format
        codec_args: list[str] = []
        if output_format == "mp4":
            codec_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast"]
        elif output_format == "webm":
            codec_args = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p"]
        elif output_format == "gif":
            codec_args = []  # ffmpeg default
            ext = "gif"

        output_path = tmp / f"output.{ext}"

        # Build ffmpeg command as argument array (no shell injection risk)
        cmd: list[str] = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(tmp / "frame_%06d.png"),
        ]

        # Text overlay (sanitized for ffmpeg drawtext filter)
        if text_overlay:
            safe_text = text_overlay.replace("'", "\\'").replace(":", "\\:")
            vf = (
                f"drawtext=text='{safe_text}':fontsize=28:fontcolor=white"
                ":x=20:y=20:shadowcolor=black:shadowx=1:shadowy=1"
            )
            cmd.extend(["-vf", vf])

        cmd.extend(codec_args)
        cmd.extend(["-crf", str(quality)])
        cmd.append(str(output_path))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return None, "ffmpeg timed out after 300s"

        if proc.returncode != 0:
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")[:500]
            return None, f"ffmpeg failed: {stderr_str}"

        if output_path.exists():
            return output_path.read_bytes(), None

        return None, "ffmpeg produced no output file"


async def execute_pipeline(
    definition: PipelineDefinition,
    runner: ParaViewRunner,
    compiler: ScriptCompiler | None = None,
    output_handler: OutputHandler | None = None,
) -> PipelineResult:
    """Full pipeline execution with optional video compilation.

    1. Validate the definition
    2. Compile to pvpython script
    3. Execute via ParaViewRunner
    4. Parse results via OutputHandler
    5. (Optional) Compile video from animation frames
    """
    compiler = compiler or ScriptCompiler()
    output_handler = output_handler or OutputHandler()

    # 1. Validate
    errors = validate_pipeline(definition)
    if errors:
        raise ValueError(f"Invalid pipeline: {'; '.join(errors)}")

    # 2. Compile
    script = compiler.compile(definition)

    # 3. Execute (file_path already validated at server layer)
    run_result = await runner.execute(script)

    # 4. Parse
    result = output_handler.parse(run_result, definition.output.type)

    # 5. Video compilation for animation output
    anim = definition.output.animation
    if (
        result.output_type == "animation"
        and anim is not None
        and anim.output_format != "frames"
        and run_result.output_file_data
    ):
        # Use effective_fps from result if available, otherwise requested fps
        effective_fps = float(anim.fps)
        if result.json_data and "effective_fps" in result.json_data:
            effective_fps = float(result.json_data["effective_fps"])

        video_bytes, video_error = await compile_video(
            run_result.output_file_data,
            fps=effective_fps,
            output_format=anim.output_format,
            quality=anim.video_quality,
            text_overlay=anim.text_overlay,
        )

        if result.json_data is None:
            result.json_data = {}
        if video_bytes:
            result.json_data["video_format"] = anim.output_format
            result.json_data["video_size_bytes"] = len(video_bytes)
            result.image_bytes = video_bytes
        elif video_error:
            result.json_data["video_error"] = video_error

    return result
