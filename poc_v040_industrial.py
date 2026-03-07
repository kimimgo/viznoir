#!/usr/bin/env python3
"""viznoir v0.4.0 — Industrial Workflow PoC (3Blue1Brown style).

Demonstrates the full viznoir pipeline with real LaTeX rendering,
cinematic VTK visualization, and engineer's insight storytelling.

Output: /tmp/viznoir-v040-poc/viznoir_v040_industrial.png (1920x1080)
"""

from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Config
# ============================================================

OUTPUT_DIR = Path("/tmp/viznoir-v040-poc")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 3Blue1Brown palette
BG_COLOR = (0x1C, 0x1C, 0x2E)          # dark blue-black
ACCENT_TEAL = "#00D4AA"
ACCENT_CORAL = "#FF6B6B"
ACCENT_GOLD = "#FFE66D"
ACCENT_MINT = "#A8E6CF"
TEXT_WHITE = "#FFFFFF"
TEXT_DIM = "#8892B0"

CANVAS_W, CANVAS_H = 1920, 1080


# ============================================================
# Helpers
# ============================================================

def _try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _try_font_bold(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return _try_font(size)


# ============================================================
# Step 1: VTK Dataset
# ============================================================

def create_dataset():
    """Create a wavelet dataset for visualization."""
    import vtk
    src = vtk.vtkRTAnalyticSource()
    src.SetWholeExtent(-16, 16, -16, 16, -16, 16)
    src.Update()
    return src.GetOutput()


# ============================================================
# Step 2: Cinematic Renders
# ============================================================

def render_isosurface(dataset) -> bytes:
    from viznoir.engine.renderer import RenderConfig
    from viznoir.engine.renderer_cine import cinematic_render, CinematicConfig
    render = RenderConfig(width=640, height=480, array_name="RTData")
    config = CinematicConfig(render=render, lighting_preset="cinematic", ground_plane=True)

    # Apply contour filter
    import vtk
    contour = vtk.vtkContourFilter()
    contour.SetInputData(dataset)
    contour.SetValue(0, 150.0)
    contour.Update()
    return cinematic_render(contour.GetOutput(), config)


def render_slice(dataset) -> bytes:
    from viznoir.engine.renderer import RenderConfig
    from viznoir.engine.renderer_cine import cinematic_render, CinematicConfig
    render = RenderConfig(width=640, height=480, array_name="RTData")
    config = CinematicConfig(render=render, lighting_preset="cinematic")

    import vtk
    plane = vtk.vtkPlane()
    plane.SetOrigin(0, 0, 0)
    plane.SetNormal(0, 0, 1)
    cutter = vtk.vtkCutter()
    cutter.SetInputData(dataset)
    cutter.SetCutFunction(plane)
    cutter.Update()
    return cinematic_render(cutter.GetOutput(), config)


def render_volume(dataset) -> bytes:
    from viznoir.engine.renderer import RenderConfig
    from viznoir.engine.renderer_cine import cinematic_render, CinematicConfig
    render = RenderConfig(
        width=640, height=480, array_name="RTData",
        representation="volume", transfer_preset="thermal",
    )
    config = CinematicConfig(render=render, lighting_preset="cinematic")
    return cinematic_render(dataset, config)


# ============================================================
# Step 3: LaTeX Equations (real LaTeX → dvisvgm → SVG → PNG)
# ============================================================

def render_equations() -> tuple[Image.Image, Image.Image]:
    """Render the main equation and insight decomposition."""
    from viznoir.anim.latex import render_latex

    # Main equation — clean white
    main_eq = (
        r"\rho \left( \frac{\partial \mathbf{u}}{\partial t} "
        r"+ (\mathbf{u} \cdot \nabla) \mathbf{u} \right) "
        r"= -\nabla p + \mu \nabla^2 \mathbf{u} + \mathbf{f}"
    )
    main_img = render_latex(main_eq, color="FFFFFF", scale=3.0)

    # Insight decomposition — colored underbrace (THE feature)
    insight_eq = (
        r"\underbrace{\rho \frac{D\mathbf{u}}{Dt}}_{\text{Inertia}}"
        r"= \underbrace{-\nabla p}_{\text{Pressure}}"
        r"+ \underbrace{\mu \nabla^2 \mathbf{u}}_{\text{Viscosity}}"
        r"+ \underbrace{\mathbf{f}}_{\text{Body force}}"
    )
    insight_img = render_latex(insight_eq, color="00D4AA", scale=3.0)

    return main_img, insight_img


# ============================================================
# Step 4: Easing Chart
# ============================================================

def render_easing_chart() -> Image.Image:
    """Plot representative easing functions — 3b1b style dark chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from viznoir.anim.easing import EASING_FUNCTIONS

    selected = ["linear", "smooth", "ease_in_out_sine", "ease_in_out_cubic",
                 "ease_in_expo", "there_and_back", "rush_into"]
    colors = ["#8892B0", "#00D4AA", "#FF6B6B", "#FFE66D",
              "#A8E6CF", "#C084FC", "#38BDF8"]

    t = np.linspace(0, 1, 200)

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
    fig.patch.set_facecolor("#1C1C2E")
    ax.set_facecolor("#1C1C2E")

    for name, color in zip(selected, colors):
        fn = EASING_FUNCTIONS[name]
        y = [fn(ti) for ti in t]
        ax.plot(t, y, color=color, linewidth=2, label=name, alpha=0.9)

    ax.legend(loc="upper left", fontsize=7, framealpha=0.3,
              facecolor="#1C1C2E", edgecolor="#333", labelcolor="white")
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.1, 1.15)
    ax.tick_params(colors="#8892B0", labelsize=7)
    for spine in ax.spines.values():
        spine.set_color("#333")
    ax.set_xlabel("t", color="#8892B0", fontsize=9)
    ax.set_ylabel("f(t)", color="#8892B0", fontsize=9)

    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


# ============================================================
# Step 5: InProcessExecutor Benchmark
# ============================================================

def demo_inprocess_executor():
    from viznoir.core.worker import InProcessExecutor

    executor = InProcessExecutor()
    script = (
        "import json, os, math\n"
        "results = {'pi': math.pi, 'status': 'computed_in_process'}\n"
        "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
        "with open(os.path.join(out, 'result.json'), 'w') as f:\n"
        "    json.dump(results, f)\n"
    )
    executor.run(script)  # warm up

    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        result = executor.run(script)
        times.append(time.perf_counter() - t0)
        assert result.exit_code == 0

    return np.mean(times) * 1000


# ============================================================
# Step 6: Composite Dashboard (3Blue1Brown style)
# ============================================================

def composite_dashboard(
    iso_png: bytes,
    slice_png: bytes,
    vol_png: bytes,
    main_eq: Image.Image,
    insight_eq: Image.Image,
    easing_img: Image.Image,
    executor_ms: float,
) -> Path:
    """Compose a 1920x1080 dashboard in 3Blue1Brown aesthetic."""
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (*BG_COLOR, 255))
    draw = ImageDraw.Draw(canvas)

    font_title = _try_font_bold(36)
    font_sub = _try_font(18)
    font_small = _try_font(14)
    font_label = _try_font_bold(16)

    # --- Title bar ---
    draw.text((40, 24), "viznoir", fill=ACCENT_TEAL, font=_try_font_bold(42))
    draw.text((210, 36), "v0.4.0 — Industrial CFD Post-Processing", fill=TEXT_DIM, font=font_sub)

    # Thin separator
    draw.line([(40, 80), (CANVAS_W - 40, 80)], fill="#333", width=1)

    # --- Row 1: Three VTK renders (y=100) ---
    renders = [
        (iso_png, "Isosurface (RTData=150)", "PBR + SSAO + FXAA + ground plane"),
        (slice_png, "Cross-Section (Z=0)", "Slice filter + cinematic lighting"),
        (vol_png, "Volume Render", "Thermal transfer function + ray casting"),
    ]

    panel_w, panel_h = 560, 340
    for i, (png_bytes, title, desc) in enumerate(renders):
        x = 40 + i * (panel_w + 30)
        y = 100

        # Render image
        img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        img = img.resize((panel_w, int(panel_w * img.height / img.width)), Image.LANCZOS)
        # Crop to panel height
        if img.height > panel_h - 50:
            crop_y = (img.height - (panel_h - 50)) // 2
            img = img.crop((0, crop_y, img.width, crop_y + panel_h - 50))

        canvas.paste(img, (x, y), img)

        # Label below
        draw.text((x, y + panel_h - 42), title, fill=TEXT_WHITE, font=font_label)
        draw.text((x, y + panel_h - 22), desc, fill=TEXT_DIM, font=font_small)

    # --- Row 2: Equations (y=470) ---
    draw.line([(40, 460), (CANVAS_W - 40, 460)], fill="#333", width=1)
    draw.text((40, 472), "Governing Equation — Navier-Stokes (Incompressible)", fill=ACCENT_TEAL, font=font_sub)

    # Main equation — centered
    eq_y = 510
    if main_eq.width > CANVAS_W - 80:
        ratio = (CANVAS_W - 80) / main_eq.width
        main_eq = main_eq.resize((int(main_eq.width * ratio), int(main_eq.height * ratio)), Image.LANCZOS)
    eq_x = (CANVAS_W - main_eq.width) // 2
    canvas.paste(main_eq, (eq_x, eq_y), main_eq)

    # Insight equation — below, teal colored
    insight_y = eq_y + main_eq.height + 15
    if insight_eq.width > CANVAS_W - 80:
        ratio = (CANVAS_W - 80) / insight_eq.width
        insight_eq = insight_eq.resize((int(insight_eq.width * ratio), int(insight_eq.height * ratio)), Image.LANCZOS)
    ins_x = (CANVAS_W - insight_eq.width) // 2
    canvas.paste(insight_eq, (ins_x, insight_y), insight_eq)

    # --- Row 3: Easing + Metrics (y=750) ---
    draw.line([(40, 740), (CANVAS_W - 40, 740)], fill="#333", width=1)

    # Easing chart — left side
    easing_target_w = 900
    if easing_img.width > 0:
        ratio = easing_target_w / easing_img.width
        easing_resized = easing_img.resize(
            (int(easing_img.width * ratio), int(easing_img.height * ratio)), Image.LANCZOS
        )
    else:
        easing_resized = easing_img
    canvas.paste(easing_resized, (40, 755), easing_resized)

    # Metrics cards — right side
    cards_x = 1000
    card_y = 760

    metrics = [
        ("19", "MCP Tools", ACCENT_TEAL),
        ("20", "Easing Functions", ACCENT_GOLD),
        (f"{executor_ms:.1f}ms", "InProcess Executor", ACCENT_CORAL),
        ("1134", "Tests (99% cov)", ACCENT_MINT),
        ("6", "Transfer Presets", "#C084FC"),
    ]

    for val, label, color in metrics:
        draw.text((cards_x, card_y), val, fill=color, font=_try_font_bold(28))
        draw.text((cards_x + 120, card_y + 6), label, fill=TEXT_DIM, font=font_small)
        card_y += 52

    # Footer
    draw.text(
        (40, CANVAS_H - 30),
        "viznoir — VTK is all you need. Cinema-quality science visualization for AI agents.",
        fill="#555", font=font_small,
    )
    draw.text(
        (CANVAS_W - 300, CANVAS_H - 30),
        "github.com/kimimgo/viznoir",
        fill="#555", font=font_small,
    )

    out_path = OUTPUT_DIR / "viznoir_v040_industrial.png"
    canvas.save(str(out_path))
    return out_path


# ============================================================
# Main
# ============================================================

def main():
    t_total = time.perf_counter()
    print("=" * 70)
    print("  viznoir v0.4.0 — Industrial Workflow PoC (3Blue1Brown style)")
    print("=" * 70)

    print("\n[1/6] Creating dataset (wavelet 32³)...")
    t0 = time.perf_counter()
    dataset = create_dataset()
    print(f"  -> {dataset.GetNumberOfPoints():,} points in {time.perf_counter()-t0:.2f}s")

    print("\n[2/6] Cinematic renders (isosurface + slice + volume)...")
    t0 = time.perf_counter()
    iso_png = render_isosurface(dataset)
    (OUTPUT_DIR / "01_isosurface.png").write_bytes(iso_png)
    print(f"  -> isosurface: {len(iso_png):,} bytes")

    slice_png = render_slice(dataset)
    (OUTPUT_DIR / "02_slice.png").write_bytes(slice_png)
    print(f"  -> slice: {len(slice_png):,} bytes")

    vol_png = render_volume(dataset)
    (OUTPUT_DIR / "03_volume.png").write_bytes(vol_png)
    print(f"  -> volume: {len(vol_png):,} bytes")
    print(f"  -> all renders in {time.perf_counter()-t0:.2f}s")

    print("\n[3/6] LaTeX equations (latex → dvisvgm → SVG → PNG)...")
    t0 = time.perf_counter()
    main_eq, insight_eq = render_equations()
    main_eq.save(OUTPUT_DIR / "04_main_equation.png")
    insight_eq.save(OUTPUT_DIR / "05_insight_equation.png")
    print(f"  -> main: {main_eq.size}, insight: {insight_eq.size}")
    print(f"  -> real LaTeX with \\underbrace in {time.perf_counter()-t0:.2f}s")

    print("\n[4/6] Easing functions chart...")
    t0 = time.perf_counter()
    easing_img = render_easing_chart()
    easing_img.save(OUTPUT_DIR / "06_easing.png")
    print(f"  -> 7 of 20 functions in {time.perf_counter()-t0:.2f}s")

    print("\n[5/6] InProcessExecutor benchmark...")
    executor_ms = demo_inprocess_executor()
    print(f"  -> avg {executor_ms:.1f}ms/call (10 runs)")

    print("\n[6/6] Compositing dashboard (3Blue1Brown style)...")
    t0 = time.perf_counter()
    final_path = composite_dashboard(
        iso_png, slice_png, vol_png,
        main_eq, insight_eq, easing_img, executor_ms,
    )
    print(f"  -> {final_path} in {time.perf_counter()-t0:.2f}s")

    total = time.perf_counter() - t_total
    print("\n" + "=" * 70)
    print(f"  Complete in {total:.1f}s — All outputs in: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
