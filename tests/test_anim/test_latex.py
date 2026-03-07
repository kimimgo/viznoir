"""Tests for viznoir.anim.latex — LaTeX → SVG → PNG pipeline."""

from __future__ import annotations

import pytest
from PIL import Image

from viznoir.anim.latex import (
    CAIROSVG_AVAILABLE,
    LATEX_AVAILABLE,
    _colorize_svg,
    _has_cairosvg,
    _has_latex,
    render_latex,
    render_latex_lines,
)

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


class TestDetection:
    def test_has_latex_returns_bool(self):
        assert isinstance(_has_latex(), bool)

    def test_has_cairosvg_returns_bool(self):
        assert isinstance(_has_cairosvg(), bool)

    def test_module_level_flags(self):
        assert isinstance(LATEX_AVAILABLE, bool)
        assert isinstance(CAIROSVG_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# SVG colorization
# ---------------------------------------------------------------------------


class TestColorizeSvg:
    def test_single_quote_fill(self):
        svg = "<path fill='#000000' d='M0 0'/>"
        result = _colorize_svg(svg, "FF6B6B")
        assert "fill='#FF6B6B'" in result

    def test_double_quote_fill(self):
        svg = '<path fill="#000000" d="M0 0"/>'
        result = _colorize_svg(svg, "00D4AA")
        assert 'fill="#00D4AA"' in result

    def test_multiple_paths(self):
        svg = "<path fill='#000' d='M0'/><path fill='#111' d='M1'/>"
        result = _colorize_svg(svg, "FFFFFF")
        assert result.count("#FFFFFF") == 2


# ---------------------------------------------------------------------------
# Full pipeline (requires latex + dvisvgm + cairosvg)
# ---------------------------------------------------------------------------

needs_latex = pytest.mark.skipif(
    not (LATEX_AVAILABLE and CAIROSVG_AVAILABLE),
    reason="latex/dvisvgm/cairosvg not available",
)


@needs_latex
class TestRenderLatex:
    def test_simple_equation(self):
        img = render_latex(r"E = mc^2", color="FFFFFF")
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"
        assert img.width > 0 and img.height > 0

    def test_navier_stokes(self):
        eq = (
            r"\rho \left( \frac{\partial \mathbf{u}}{\partial t} "
            r"+ (\mathbf{u} \cdot \nabla) \mathbf{u} \right) "
            r"= -\nabla p + \mu \nabla^2 \mathbf{u} + \mathbf{f}"
        )
        img = render_latex(eq, color="FFFFFF")
        assert img.width > 100

    def test_underbrace(self):
        """The whole point — underbrace must work (unlike matplotlib)."""
        eq = r"\underbrace{F = ma}_{\text{Newton's 2nd Law}}"
        img = render_latex(eq, color="00D4AA")
        assert img.width > 50

    def test_color_parameter(self):
        img = render_latex(r"x^2", color="FF6B6B")
        assert isinstance(img, Image.Image)

    def test_dollar_delimiters_stripped(self):
        img1 = render_latex(r"$x^2$", color="FFFFFF")
        img2 = render_latex(r"x^2", color="FFFFFF")
        # Both should produce valid images
        assert img1.width > 0
        assert img2.width > 0

    def test_display_math_delimiters(self):
        img = render_latex(r"$$\sum_{i=0}^{n} i$$", color="FFFFFF")
        assert img.width > 0

    def test_custom_preamble(self):
        img = render_latex(
            r"\mathbb{R}^n",
            color="FFFFFF",
            preamble=r"\usepackage{mathrsfs}",
        )
        assert img.width > 0

    def test_scale_affects_size(self):
        img_small = render_latex(r"x", color="FFFFFF", scale=1.0)
        img_large = render_latex(r"x", color="FFFFFF", scale=4.0)
        assert img_large.width > img_small.width

    def test_transparent_background(self):
        img = render_latex(r"y = x", color="FFFFFF")
        # Check corners are transparent
        assert img.getpixel((0, 0))[3] == 0  # alpha channel

    def test_complex_equation(self):
        """Full Navier-Stokes with underbrace term decomposition."""
        eq = (
            r"\underbrace{\rho \frac{D\mathbf{u}}{Dt}}_{\text{Inertia}}"
            r"= \underbrace{-\nabla p}_{\text{Pressure}}"
            r"+ \underbrace{\mu \nabla^2 \mathbf{u}}_{\text{Viscosity}}"
            r"+ \underbrace{\mathbf{f}}_{\text{Body force}}"
        )
        img = render_latex(eq, color="FFFFFF")
        assert img.width > 200


@needs_latex
class TestRenderLatexLines:
    def test_two_colored_lines(self):
        lines = [
            (r"E = mc^2", "FFFFFF"),
            (r"F = ma", "FF6B6B"),
        ]
        img = render_latex_lines(lines)
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"

    def test_height_increases_with_lines(self):
        one = render_latex_lines([(r"x", "FFFFFF")])
        two = render_latex_lines([(r"x", "FFFFFF"), (r"y", "FF0000")])
        assert two.height > one.height

    def test_width_matches_widest(self):
        lines = [
            (r"x", "FFFFFF"),
            (r"\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}", "00D4AA"),
        ]
        img = render_latex_lines(lines)
        wide = render_latex(lines[1][0], color=lines[1][1])
        assert img.width == wide.width


# ---------------------------------------------------------------------------
# Fallback (matplotlib mathtext)
# ---------------------------------------------------------------------------


class TestFallback:
    def test_mathtext_fallback(self):
        from unittest.mock import patch

        from viznoir.anim import latex as latex_mod

        with patch.object(latex_mod, "LATEX_AVAILABLE", False):
            img = render_latex(r"x^2 + y^2 = r^2", color="FFFFFF")
            assert isinstance(img, Image.Image)
            assert img.mode == "RGBA"
