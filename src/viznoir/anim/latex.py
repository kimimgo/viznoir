"""viznoir.anim.latex — LaTeX → SVG → PNG rendering pipeline.

Uses the classic Manim-style pipeline: latex → DVI → dvisvgm → SVG,
then cairosvg for rasterization to PNG with transparent background.

Fallback: matplotlib mathtext when LaTeX is not installed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


# ---------------------------------------------------------------------------
# LaTeX availability detection
# ---------------------------------------------------------------------------

def _has_latex() -> bool:
    """Check if latex and dvisvgm are available on PATH."""
    return shutil.which("latex") is not None and shutil.which("dvisvgm") is not None


def _has_cairosvg() -> bool:
    """Check if cairosvg is importable."""
    try:
        import cairosvg  # noqa: F401
        return True
    except ImportError:
        return False


LATEX_AVAILABLE = _has_latex()
CAIROSVG_AVAILABLE = _has_cairosvg()


# ---------------------------------------------------------------------------
# LaTeX template
# ---------------------------------------------------------------------------

_LATEX_TEMPLATE = r"""\documentclass[preview,border=1pt]{standalone}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{xcolor}
%(preamble)s
\begin{document}
\color[HTML]{%(color)s}
%(body)s
\end{document}
"""


# ---------------------------------------------------------------------------
# Core pipeline: LaTeX → DVI → SVG → PNG
# ---------------------------------------------------------------------------

def _latex_to_dvi(tex_source: str, work_dir: Path) -> Path:
    """Compile LaTeX source to DVI."""
    tex_file = work_dir / "formula.tex"
    tex_file.write_text(tex_source)

    result = subprocess.run(
        ["latex", "-interaction=nonstopmode", "-halt-on-error", str(tex_file)],
        cwd=work_dir,
        capture_output=True,
        timeout=30,
    )
    dvi_file = work_dir / "formula.dvi"
    if not dvi_file.exists():
        raise RuntimeError(
            f"LaTeX compilation failed:\n{result.stdout.decode(errors='replace')[-500:]}"
        )
    return dvi_file


def _dvi_to_svg(dvi_file: Path, work_dir: Path) -> str:
    """Convert DVI to SVG string via dvisvgm."""
    svg_file = work_dir / "formula.svg"

    result = subprocess.run(
        [
            "dvisvgm",
            "--no-fonts",       # convert fonts to paths (portable)
            "--exact-bbox",     # tight bounding box
            "-o", str(svg_file),
            str(dvi_file),
        ],
        cwd=work_dir,
        capture_output=True,
        timeout=30,
    )
    if not svg_file.exists():
        raise RuntimeError(
            f"dvisvgm failed:\n{result.stderr.decode(errors='replace')}"
        )
    return svg_file.read_text()


def _colorize_svg(svg_text: str, color: str) -> str:
    """Override fill color in SVG paths to the requested color."""
    # dvisvgm outputs paths with fill='currentColor' or explicit black
    # Replace all fill colors with the target color
    svg_text = re.sub(
        r"fill='[^']*'",
        f"fill='#{color}'",
        svg_text,
    )
    svg_text = re.sub(
        r'fill="[^"]*"',
        f'fill="#{color}"',
        svg_text,
    )
    return svg_text


def _svg_to_png(svg_text: str, scale: float = 3.0) -> bytes:
    """Rasterize SVG to PNG bytes via cairosvg."""
    import cairosvg

    return cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        scale=scale,
        background_color="transparent",
    )


# ---------------------------------------------------------------------------
# Fallback: matplotlib mathtext
# ---------------------------------------------------------------------------

def _render_mathtext(tex_string: str, font_size: float, color: str) -> "Image":
    """Fallback renderer using matplotlib mathtext."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image as PILImage

    fig, ax = plt.subplots(figsize=(12, 2), dpi=150)
    fig.patch.set_alpha(0.0)
    ax.set_alpha(0.0)
    ax.axis("off")

    # Wrap in $ if not already
    if not tex_string.startswith("$"):
        tex_string = f"${tex_string}$"

    ax.text(
        0.5, 0.5, tex_string,
        transform=ax.transAxes,
        fontsize=font_size * 0.6,  # matplotlib pts differ from LaTeX
        color=f"#{color}",
        ha="center", va="center",
    )

    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return PILImage.open(buf).convert("RGBA")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_latex(
    tex_string: str,
    *,
    font_size: float = 48,
    color: str = "FFFFFF",
    preamble: str = "",
    scale: float = 3.0,
) -> "Image":
    """Render LaTeX string to a PIL Image with transparent background.

    Parameters
    ----------
    tex_string : str
        LaTeX math expression. Can include $ delimiters or not.
        Supports full LaTeX: \\underbrace, \\frac, \\mathbf, etc.
    font_size : float
        Base font size in pt (used for fallback renderer).
    color : str
        Hex color without '#' (e.g., "FFFFFF" for white, "00D4AA" for teal).
    preamble : str
        Additional LaTeX preamble (extra \\usepackage, etc.).
    scale : float
        Rasterization scale factor (3.0 = high-res, good for 1080p).

    Returns
    -------
    PIL.Image.Image
        RGBA image with transparent background.
    """
    from PIL import Image as PILImage

    # Strip $ delimiters for the LaTeX document body
    body = tex_string.strip()
    if body.startswith("$$") and body.endswith("$$"):
        body = body[2:-2]
    elif body.startswith("$") and body.endswith("$"):
        body = body[1:-1]

    # Wrap in display math
    body = f"\\[{body}\\]"

    if LATEX_AVAILABLE and CAIROSVG_AVAILABLE:
        tex_source = _LATEX_TEMPLATE % {
            "preamble": preamble,
            "color": color.lstrip("#"),
            "body": body,
        }

        with tempfile.TemporaryDirectory(prefix="viznoir-latex-") as tmp:
            work_dir = Path(tmp)
            dvi = _latex_to_dvi(tex_source, work_dir)
            svg_text = _dvi_to_svg(dvi, work_dir)
            svg_text = _colorize_svg(svg_text, color.lstrip("#"))
            png_bytes = _svg_to_png(svg_text, scale=scale)

        buf = BytesIO(png_bytes)
        return PILImage.open(buf).convert("RGBA")

    # Fallback
    return _render_mathtext(tex_string, font_size, color.lstrip("#"))


def render_latex_lines(
    lines: list[tuple[str, str]],
    *,
    scale: float = 3.0,
    preamble: str = "",
    spacing: int = 20,
) -> "Image":
    """Render multiple LaTeX expressions, each with its own color, stacked vertically.

    Parameters
    ----------
    lines : list of (tex_string, color) tuples
        Each entry is a LaTeX expression and its hex color.
    scale : float
        Rasterization scale factor.
    preamble : str
        Additional LaTeX preamble.
    spacing : int
        Vertical pixel spacing between lines.

    Returns
    -------
    PIL.Image.Image
        RGBA image with all lines stacked vertically.
    """
    from PIL import Image as PILImage

    images = [
        render_latex(tex, color=col, scale=scale, preamble=preamble)
        for tex, col in lines
    ]

    total_width = max(img.width for img in images)
    total_height = sum(img.height for img in images) + spacing * (len(images) - 1)

    canvas = PILImage.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    y = 0
    for img in images:
        # Center horizontally
        x = (total_width - img.width) // 2
        canvas.paste(img, (x, y), img)
        y += img.height + spacing

    return canvas
