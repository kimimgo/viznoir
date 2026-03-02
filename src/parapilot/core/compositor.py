"""Compositor — compose split-pane frames from individual pane images and graph data."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from parapilot.pipeline.models import SplitAnimationDef

# Lazy imports for optional dependencies
_PIL_AVAILABLE: bool | None = None
_MPL_AVAILABLE: bool | None = None


def _check_pillow() -> None:
    global _PIL_AVAILABLE
    if _PIL_AVAILABLE is None:
        try:
            import PIL  # noqa: F401

            _PIL_AVAILABLE = True
        except ImportError:
            _PIL_AVAILABLE = False
    if not _PIL_AVAILABLE:
        raise ImportError(
            "pillow is required for split_animate. "
            "Install with: pip install 'parapilot[composite]'"
        )


def _check_matplotlib() -> None:
    global _MPL_AVAILABLE
    if _MPL_AVAILABLE is None:
        try:
            import matplotlib  # noqa: F401

            _MPL_AVAILABLE = True
        except ImportError:
            _MPL_AVAILABLE = False
    if not _MPL_AVAILABLE:
        raise ImportError(
            "matplotlib is required for split_animate graph panes. "
            "Install with: pip install 'parapilot[composite]'"
        )


class Compositor:
    """Compose split-pane animation frames from render images and stats data."""

    def __init__(self, split_anim: SplitAnimationDef) -> None:
        _check_pillow()
        self.split_anim = split_anim
        self.layout = split_anim.layout
        self.total_width = split_anim.resolution[0]
        self.total_height = split_anim.resolution[1]

        # Compute per-cell dimensions
        gap = self.layout.gap
        self.cell_width = (self.total_width - gap * (self.layout.cols - 1)) // self.layout.cols
        self.cell_height = (self.total_height - gap * (self.layout.rows - 1)) // self.layout.rows

    def compose_all(
        self,
        pane_frame_data: dict[str, bytes],
        stats: dict[str, Any],
        frame_count: int,
        effective_fps: float | None = None,
    ) -> tuple[list[bytes], bytes | None]:
        """Compose all frames and optionally generate a GIF.

        Returns:
            Tuple of (list of composed PNG bytes, GIF bytes or None).
        """
        from PIL import Image as PILImage

        composed_frames: list[PILImage.Image] = []
        composed_bytes: list[bytes] = []

        # Identify render and graph panes
        render_panes = [p for p in self.split_anim.panes if p.type == "render"]
        graph_panes = [p for p in self.split_anim.panes if p.type == "graph"]

        has_graphs = len(graph_panes) > 0
        if has_graphs:
            _check_matplotlib()

        timesteps = stats.get("timesteps", [])

        for frame_idx in range(frame_count):
            render_images: dict[tuple[int, int], PILImage.Image] = {}
            graph_images: dict[tuple[int, int], PILImage.Image] = {}

            # Load render pane images
            for i, pane in enumerate(render_panes):
                key = f"pane_{i}_frame_{frame_idx:06d}.png"
                if key in pane_frame_data:
                    img = PILImage.open(io.BytesIO(pane_frame_data[key]))
                    render_images[(pane.row, pane.col)] = img

            # Generate graph pane images
            for pane in graph_panes:
                if pane.graph_pane is not None:
                    graph_img = self._render_graph_frame(
                        pane.graph_pane,
                        stats,
                        timesteps,
                        frame_idx,
                        self.cell_width,
                        self.cell_height,
                    )
                    graph_images[(pane.row, pane.col)] = graph_img

            composed = self._compose_single_frame(render_images, graph_images)
            composed_frames.append(composed)

            buf = io.BytesIO()
            composed.save(buf, format="PNG")
            composed_bytes.append(buf.getvalue())

        gif_bytes: bytes | None = None
        if self.split_anim.gif and composed_frames:
            gif_fps = effective_fps if effective_fps else self.split_anim.fps
            gif_bytes = self._generate_gif(
                composed_frames, gif_fps, self.split_anim.gif_loop
            )

        return composed_bytes, gif_bytes

    def _render_graph_frame(
        self,
        graph_pane: Any,
        stats: dict[str, Any],
        timesteps: list[float],
        current_idx: int,
        width: int,
        height: int,
    ) -> Any:
        """Render a single graph frame using matplotlib."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from PIL import Image as PILImage

        dpi = 100
        fig_w = width / dpi
        fig_h = height / dpi
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)

        field_stats = stats.get("fields", {})
        colors_cycle = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for i, series in enumerate(graph_pane.series):
            field_data = field_stats.get(series.field, {})
            values = field_data.get(series.stat, [])
            if not values or not timesteps:
                continue

            label = series.label or f"{series.field} ({series.stat})"
            color = series.color or colors_cycle[i % len(colors_cycle)]
            # Plot up to current timestep
            plot_ts = timesteps[: current_idx + 1]
            plot_vals = values[: current_idx + 1]
            ax.plot(plot_ts, plot_vals, color=color, label=label, linewidth=1.5)

            # Mark current point
            if current_idx < len(values) and current_idx < len(timesteps):
                ax.plot(
                    timesteps[current_idx],
                    values[current_idx],
                    "o",
                    color=color,
                    markersize=6,
                )

        # Vertical line at current timestep
        if current_idx < len(timesteps):
            ax.axvline(x=timesteps[current_idx], color="red", linestyle="--", alpha=0.7)

        # Set x-axis range to full range
        if timesteps:
            ax.set_xlim(timesteps[0], timesteps[-1])

        # Set y-axis range if specified
        if graph_pane.y_range:
            ax.set_ylim(graph_pane.y_range[0], graph_pane.y_range[1])

        if graph_pane.title:
            ax.set_title(graph_pane.title, fontsize=10)
        ax.set_xlabel("Time [s]", fontsize=8)
        if graph_pane.y_label:
            ax.set_ylabel(graph_pane.y_label, fontsize=8)
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return PILImage.open(buf)

    def _compose_single_frame(
        self,
        render_images: dict[tuple[int, int], Any],
        graph_images: dict[tuple[int, int], Any],
    ) -> Any:
        """Compose a single frame by placing pane images on a grid canvas."""
        from PIL import Image as PILImage
        from PIL import ImageDraw, ImageFont

        canvas = PILImage.new("RGB", (self.total_width, self.total_height), (255, 255, 255))
        gap = self.layout.gap

        all_images = {**render_images, **graph_images}

        for (row, col), img in all_images.items():
            x = col * (self.cell_width + gap)
            y = row * (self.cell_height + gap)
            _lanczos = getattr(PILImage, "Resampling", PILImage).LANCZOS
            resized = img.resize((self.cell_width, self.cell_height), _lanczos)
            canvas.paste(resized, (x, y))

        # Draw pane titles
        draw = ImageDraw.Draw(canvas)
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except (OSError, IOError):
            font = ImageFont.load_default()

        for pane in self.split_anim.panes:
            title = None
            if pane.type == "render" and pane.render_pane and pane.render_pane.title:
                title = pane.render_pane.title
            elif pane.type == "graph" and pane.graph_pane and pane.graph_pane.title:
                title = None  # Graph title is drawn by matplotlib

            if title:
                x = pane.col * (self.cell_width + gap) + 8
                y = pane.row * (self.cell_height + gap) + 4
                # Shadow for readability
                draw.text((x + 1, y + 1), title, fill=(0, 0, 0), font=font)
                draw.text((x, y), title, fill=(255, 255, 255), font=font)

        return canvas

    def _generate_gif(self, frames: list[Any], fps: float | int, loop: int = 0) -> bytes:
        """Generate a GIF from composed frames."""
        buf = io.BytesIO()
        duration_ms = max(1, int(1000 / fps))
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=loop,
            optimize=True,
        )
        return buf.getvalue()
