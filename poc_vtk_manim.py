#!/usr/bin/env python3
"""viznoir + Manim Integration PoC

Demonstrates: VTK cinematic render + Manim LaTeX/equation overlay + composition
Output: /tmp/viznoir-manim-poc/
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.environ.setdefault("VTK_DEFAULT_OPENGL_WINDOW", "vtkEGLRenderWindow")

from io import BytesIO
from pathlib import Path

OUTPUT_DIR = Path("/tmp/viznoir-manim-poc")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# Step 1: VTK Cinematic Render (viznoir engine)
# ============================================================

def render_vtk_scene() -> bytes:
    """Render VTK wavelet isosurface with viznoir cinematic engine."""
    import vtk

    from viznoir.engine.filters import contour
    from viznoir.engine.renderer import RenderConfig
    from viznoir.engine.renderer_cine import CinematicConfig, cinematic_render

    # Generate wavelet data (built-in VTK test source)
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    src.Update()

    # Extract isosurface at value=150
    iso_data = contour(src.GetOutput(), array_name="RTData", values=[150.0])

    # Cinematic render
    rc = RenderConfig(
        width=1920,
        height=1080,
        colormap="viridis",
        array_name="RTData",
        show_scalar_bar=False,
        background=(0.06, 0.06, 0.10),
    )

    config = CinematicConfig(
        render=rc,
        quality="cinematic",
        lighting_preset="cinematic",
        background_preset="dark_gradient",
        auto_camera=True,
        fill_ratio=0.65,
        metallic=0.2,
        roughness=0.35,
        ground_plane=True,
        ssao=True,
        fxaa=True,
    )

    return cinematic_render(iso_data, config)


# ============================================================
# Step 2: Manim Equation Render (transparent PNG)
# ============================================================

def render_manim_equation() -> "Image":
    """Render LaTeX equation using Manim's Tex system.

    Falls back to matplotlib mathtext if Manim Tex fails (missing dvisvgm).
    """
    from PIL import Image

    # Try Manim Tex first
    try:
        return _render_with_manim()
    except Exception as e:
        print(f"  Manim Tex failed ({e}), falling back to matplotlib mathtext")
        return _render_with_matplotlib()


def _render_with_manim() -> "Image":
    """Use Manim's Tex renderer for equation."""
    import tempfile

    from manim import MathTex, config, tempconfig
    from PIL import Image

    with tempconfig({
        "media_dir": str(OUTPUT_DIR / "manim_media"),
        "quality": "high_quality",
        "format": "png",
        "transparent": True,
        "frame_width": 14,
        "frame_height": 2.5,
        "pixel_width": 1920,
        "pixel_height": 340,
    }):
        # Navier-Stokes equation (spaces around }} to avoid Manim brace splitting)
        eq = MathTex(
            r"\rho \left( \frac{\partial \vec{u} }{\partial t}"
            r"+ \left( \vec{u} \cdot \nabla \right) \vec{u} \right)"
            r"= -\nabla p + \mu \, \nabla^2 \vec{u}",
            font_size=72,
            color="#FFFFFF",
        )

        # Render to file
        from manim import Scene

        class EquationScene(Scene):
            def construct(self):
                self.camera.background_color = "#00000000"  # transparent
                self.add(eq)

        scene = EquationScene()
        scene.render()

        # Find rendered file
        img_path = list((OUTPUT_DIR / "manim_media").rglob("*.png"))
        if img_path:
            return Image.open(img_path[0]).convert("RGBA")

    raise RuntimeError("Manim render produced no output")


def _render_with_matplotlib() -> "Image":
    """Fallback: matplotlib mathtext for equation rendering."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    fig, ax = plt.subplots(figsize=(16, 2.5), dpi=120)
    fig.patch.set_alpha(0.0)
    ax.set_alpha(0.0)
    ax.axis("off")

    # Navier-Stokes equation
    eq_text = (
        r"$\rho \left( \frac{\partial \mathbf{u}}{\partial t} "
        r"+ (\mathbf{u} \cdot \nabla) \mathbf{u} \right) "
        r"= -\nabla p + \mu \nabla^2 \mathbf{u}$"
    )
    ax.text(
        0.5, 0.5, eq_text,
        transform=ax.transAxes,
        fontsize=36,
        color="white",
        ha="center", va="center",
    )

    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


# ============================================================
# Step 3: Manim Easing Functions Demo
# ============================================================

def render_easing_demo() -> "Image":
    """Show Manim's rate_functions applied to opacity animation."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image

    try:
        from manim import rate_functions
        easings = {
            "smooth": rate_functions.smooth,
            "ease_in_out_sine": rate_functions.ease_in_out_sine,
            "there_and_back": rate_functions.there_and_back,
            "rush_into": rate_functions.rush_into,
            "rush_from": rate_functions.rush_from,
        }
    except ImportError:
        # Minimal fallback
        easings = {
            "smooth": lambda t: 3*t**2 - 2*t**3,
            "ease_in_out": lambda t: t**2 * (3 - 2*t),
        }

    t = np.linspace(0, 1, 200)

    fig, ax = plt.subplots(figsize=(8, 3), dpi=120)
    fig.patch.set_facecolor("#0F0F1A")
    ax.set_facecolor("#0F0F1A")

    colors = ["#00D4AA", "#FF6B6B", "#4ECDC4", "#FFE66D", "#A78BFA"]
    for (name, func), color in zip(easings.items(), colors):
        values = [func(ti) for ti in t]
        ax.plot(t, values, label=name, color=color, linewidth=2)

    ax.set_xlabel("t", color="white", fontsize=12)
    ax.set_ylabel("α(t)", color="white", fontsize=12)
    ax.set_title("Manim Rate Functions → viznoir Animation Easing", color="white", fontsize=14)
    ax.legend(fontsize=9, facecolor="#1A1A2E", edgecolor="#333", labelcolor="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#333")
    ax.grid(True, alpha=0.15, color="white")

    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


# ============================================================
# Step 4: Composite — VTK + Equation + Title
# ============================================================

def composite_final(vtk_png: bytes, equation_img, easing_img) -> Path:
    """Composite VTK render + equation overlay + title panel."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    # Load VTK render
    vtk_img = Image.open(BytesIO(vtk_png)).convert("RGBA")
    W, H = vtk_img.size

    # Create overlay layer
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # --- Title panel (top-left) ---
    title_h = 80
    draw.rounded_rectangle(
        [(30, 20), (700, 20 + title_h)],
        radius=12,
        fill=(15, 15, 25, 200),
    )
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        title_font = ImageFont.load_default()
        sub_font = title_font
    draw.text((50, 30), "viznoir", font=title_font, fill=(0, 212, 170, 255))
    draw.text((195, 38), "VTK Cinematic + Manim Integration PoC", font=sub_font, fill=(200, 200, 210, 230))

    # --- Equation panel (bottom) ---
    eq_resized = equation_img.resize(
        (min(equation_img.width, W - 100), min(equation_img.height, 120)),
        Image.Resampling.LANCZOS,
    )
    eq_x = (W - eq_resized.width) // 2
    eq_y = H - eq_resized.height - 80

    # Semi-transparent panel behind equation
    panel_pad = 20
    draw.rounded_rectangle(
        [
            (eq_x - panel_pad, eq_y - panel_pad),
            (eq_x + eq_resized.width + panel_pad, eq_y + eq_resized.height + panel_pad),
        ],
        radius=12,
        fill=(10, 10, 20, 180),
    )

    # Label above equation
    draw.text(
        (eq_x, eq_y - 35),
        "Navier-Stokes Equation",
        font=sub_font,
        fill=(0, 212, 170, 200),
    )

    # --- Easing chart (bottom-right) ---
    easing_resized = easing_img.resize((420, 160), Image.Resampling.LANCZOS)
    easing_x = W - easing_resized.width - 30
    easing_y = 30

    overlay.paste(easing_resized, (easing_x, easing_y), easing_resized)

    # --- Watermark ---
    draw.text(
        (W - 250, H - 30),
        "viznoir v0.3.0 | VTK 9.5 | Manim 0.20",
        font=sub_font if sub_font else title_font,
        fill=(120, 120, 140, 150),
    )

    # Composite: VTK base + overlay + equation
    result = Image.alpha_composite(vtk_img, overlay)
    result.paste(eq_resized, (eq_x, eq_y), eq_resized)

    # Save
    out_path = OUTPUT_DIR / "viznoir_manim_poc.png"
    result.convert("RGB").save(out_path, "PNG", quality=95)
    return out_path


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("viznoir + Manim Integration PoC")
    print("=" * 60)

    print("\n[1/4] VTK Cinematic Render...")
    vtk_png = render_vtk_scene()
    vtk_path = OUTPUT_DIR / "01_vtk_cinematic.png"
    vtk_path.write_bytes(vtk_png)
    print(f"  -> {vtk_path} ({len(vtk_png):,} bytes)")

    print("\n[2/4] Manim Equation Render...")
    equation_img = render_manim_equation()
    eq_path = OUTPUT_DIR / "02_manim_equation.png"
    equation_img.save(eq_path)
    print(f"  -> {eq_path} ({equation_img.size})")

    print("\n[3/4] Manim Easing Functions...")
    easing_img = render_easing_demo()
    easing_path = OUTPUT_DIR / "03_easing_functions.png"
    easing_img.save(easing_path)
    print(f"  -> {easing_path} ({easing_img.size})")

    print("\n[4/4] Composite Final Image...")
    final_path = composite_final(vtk_png, equation_img, easing_img)
    print(f"  -> {final_path}")

    print("\n" + "=" * 60)
    print(f"All outputs in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
