"""OutputHandler — parse pvpython execution results into structured responses."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from parapilot.core.runner import RunResult


@dataclass
class PipelineResult:
    """Structured result of a pipeline execution."""

    output_type: str  # image, data, csv, animation, export, inspect
    json_data: dict[str, Any] | None = None
    image_bytes: bytes | None = None
    image_base64: str | None = None
    file_path: str | None = None
    raw: RunResult | None = None

    @property
    def ok(self) -> bool:
        return self.raw is not None and self.raw.ok


def _to_json_data(raw: dict[str, Any] | list[Any] | None) -> dict[str, Any] | None:
    """Normalize json_result to dict for PipelineResult.json_data."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    return {"data": raw}


class OutputHandler:
    """Parse RunResult into PipelineResult based on output type."""

    def parse(self, run_result: RunResult, output_type: str) -> PipelineResult:
        """Route to the appropriate parser based on output type."""
        run_result.raise_on_error()

        if output_type == "image":
            return self._parse_image(run_result)
        elif output_type in ("data", "csv"):
            return self._parse_data(run_result)
        elif output_type == "animation":
            return self._parse_animation(run_result)
        elif output_type == "export":
            return self._parse_export(run_result)
        elif output_type == "split_animation":
            return self._parse_split_animation(run_result)
        elif output_type == "inspect":
            return self._parse_data(run_result)
        elif output_type == "multi":
            return self._parse_multi(run_result)
        else:
            return PipelineResult(
                output_type=output_type,
                json_data=_to_json_data(run_result.json_result),
                raw=run_result,
            )

    def _parse_image(self, run_result: RunResult) -> PipelineResult:
        """Find the rendered PNG, read it, encode as base64."""
        image_bytes = None
        image_b64 = None
        image_path = None

        # Try in-memory data first (temp dir may already be cleaned up)
        for name, data in run_result.output_file_data.items():
            if any(name.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg")):
                image_bytes = data
                image_b64 = base64.b64encode(data).decode("ascii")
                image_path = name
                break

        # Fallback to file on disk
        if image_bytes is None:
            image_file = self._find_file(run_result, [".png", ".jpg", ".jpeg"])
            if image_file and image_file.exists():
                image_bytes = image_file.read_bytes()
                image_b64 = base64.b64encode(image_bytes).decode("ascii")
                image_path = str(image_file)

        return PipelineResult(
            output_type="image",
            json_data=_to_json_data(run_result.json_result),
            image_bytes=image_bytes,
            image_base64=image_b64,
            file_path=image_path,
            raw=run_result,
        )

    def _parse_data(self, run_result: RunResult) -> PipelineResult:
        """Return parsed JSON data."""
        return PipelineResult(
            output_type="data",
            json_data=_to_json_data(run_result.json_result),
            raw=run_result,
        )

    def _parse_animation(self, run_result: RunResult) -> PipelineResult:
        """Return animation metadata (frames directory, count)."""
        json_data = _to_json_data(run_result.json_result)
        frames_dir = json_data.get("frames_dir") if json_data else None
        return PipelineResult(
            output_type="animation",
            json_data=json_data,
            file_path=frames_dir,
            raw=run_result,
        )

    def _parse_export(self, run_result: RunResult) -> PipelineResult:
        """Return exported file path."""
        json_data = _to_json_data(run_result.json_result)
        export_path = None
        if json_data and "path" in json_data:
            export_path = str(json_data["path"])
        else:
            for f in run_result.output_files:
                if f.suffix in (".vtk", ".vtu", ".vtp", ".stl", ".ply", ".csv"):
                    export_path = str(f)
                    break

        return PipelineResult(
            output_type="export",
            json_data=json_data,
            file_path=export_path,
            raw=run_result,
        )

    def _parse_split_animation(self, run_result: RunResult) -> PipelineResult:
        """Return split animation metadata (phase 1 results)."""
        json_data = _to_json_data(run_result.json_result)
        return PipelineResult(
            output_type="split_animation",
            json_data=json_data,
            raw=run_result,
        )

    def _parse_multi(self, run_result: RunResult) -> PipelineResult:
        """Parse multi-output (image + data)."""
        result = self._parse_image(run_result)
        result.output_type = "multi"
        return result

    def _find_file(self, run_result: RunResult, extensions: list[str]) -> Path | None:
        """Find the first output file matching the given extensions."""
        for f in run_result.output_files:
            if f.suffix.lower() in extensions and f.is_file():
                return f
        return None
