#!/usr/bin/env python3
"""Generate showcase renders for the landing page.

Uses official VTK example datasets from pyvista/vtk-data repository.
Each render runs in a separate subprocess to ensure clean VTK state.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUT_DIR = PROJECT_ROOT / "www" / "public" / "showcase"
DATA_DIR = Path("/tmp/vtk-showcase")

# Base URL for pyvista/vtk-data
VTK_DATA_URL = "https://raw.githubusercontent.com/pyvista/vtk-data/master/Data"

# Files to download
DATA_FILES = [
    "dragon.ply",
    "head.vti",
    "office.binary.vtk",
    "carotid.vtk",
    "Armadillo.ply",
    "ironProt.vtk",
]

# Each render is a standalone Python snippet executed in its own process.

RENDERS: dict[str, str] = {
    # 1. Geometry: Stanford Dragon with Elevation (FEATURED)
    "dragon": textwrap.dedent("""\
        import vtk
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkPLYReader()
        reader.SetFileName(DATA_DIR + '/dragon.ply')
        reader.Update()

        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(reader.GetOutput())
        norms.ComputePointNormalsOn()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = reader.GetOutput().GetBounds()
        elev.SetLowPoint(0, b[2], 0)
        elev.SetHighPoint(0, b[3], 0)
        elev.Update()

        cam = CameraConfig(position=(0.12, 0.22, 0.20), focal_point=(-0.02, 0.12, -0.04), view_up=(0, 1, 0))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='plasma', array_name='Elevation',
            show_scalar_bar=False,
        )
        PNG = render_to_png(elev.GetOutput(), cfg, cam)
    """),

    # 2. Medical: CT skull isosurface with Inferno + Elevation
    "ct_head_contour": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import apply_filter
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(DATA_DIR + '/head.vti')
        reader.Update()
        data = reader.GetOutput()

        contoured = apply_filter(data, 'contour', array_name='Scalars_', values=[1200])
        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(contoured)
        norms.ComputePointNormalsOn()
        norms.SplittingOff()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = contoured.GetBounds()
        elev.SetLowPoint(0, 0, b[4])
        elev.SetHighPoint(0, 0, b[5])
        elev.Update()

        cam = CameraConfig(position=(350, 350, 180), focal_point=(128, 128, 93), view_up=(0, 0, 1))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='inferno', array_name='Elevation',
            show_scalar_bar=True, scalar_bar_title='Elevation',
        )
        PNG = render_to_png(elev.GetOutput(), cfg, cam)
    """),

    # 3. Flow: Carotid blood flow streamlines with tubes
    "streamlines": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import streamlines
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkStructuredPointsReader()
        reader.SetFileName(DATA_DIR + '/carotid.vtk')
        reader.Update()
        data = reader.GetOutput()

        lines = streamlines(
            data, array_name='vectors',
            seed_point1=(120, 90, 15), seed_point2=(150, 120, 35),
            num_seeds=80, integration_direction='both',
        )

        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(lines)
        calc.AddVectorArrayName('vectors')
        calc.SetFunction('mag(vectors)')
        calc.SetResultArrayName('VelocityMag')
        calc.Update()

        tube = vtk.vtkTubeFilter()
        tube.SetInputConnection(calc.GetOutputPort())
        tube.SetRadius(0.3)
        tube.SetNumberOfSides(12)
        tube.CappingOn()
        tube.Update()

        cam = CameraConfig(position=(180, 80, 60), focal_point=(137, 104, 23), view_up=(0, 0, 1))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='turbo', array_name='VelocityMag',
            show_scalar_bar=True, scalar_bar_title='Velocity Magnitude',
        )
        PNG = render_to_png(tube.GetOutput(), cfg, cam)
    """),

    # 4. Geometry: Armadillo clipped at X-plane
    "armadillo_clip": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import clip_plane
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkPLYReader()
        reader.SetFileName(DATA_DIR + '/Armadillo.ply')
        reader.Update()

        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(reader.GetOutput())
        norms.ComputePointNormalsOn()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = reader.GetOutput().GetBounds()
        elev.SetLowPoint(0, b[2], 0)
        elev.SetHighPoint(0, b[3], 0)
        elev.Update()

        clipped = clip_plane(elev.GetOutput(), origin=(5, 0, 0), normal=(1, 0, 0))
        cam = CameraConfig(position=(-180, 60, 180), focal_point=(0, 20, 0), view_up=(0, 1, 0))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='viridis', array_name='Elevation',
            show_scalar_bar=True, scalar_bar_title='Elevation',
        )
        PNG = render_to_png(clipped, cfg, cam)
    """),

    # 5. CFD: office room airflow streamlines
    "office_flow": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import streamlines
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkStructuredGridReader()
        reader.SetFileName(DATA_DIR + '/office.binary.vtk')
        reader.ReadAllVectorsOn()
        reader.ReadAllScalarsOn()
        reader.Update()
        data = reader.GetOutput()

        lines = streamlines(
            data, array_name='vectors',
            seed_point1=(0.5, 0.5, 0.5), seed_point2=(4.0, 4.0, 2.0),
            num_seeds=120, integration_direction='both',
        )

        calc = vtk.vtkArrayCalculator()
        calc.SetInputData(lines)
        calc.AddVectorArrayName('vectors')
        calc.SetFunction('mag(vectors)')
        calc.SetResultArrayName('VelocityMag')
        calc.Update()

        tube = vtk.vtkTubeFilter()
        tube.SetInputConnection(calc.GetOutputPort())
        tube.SetRadius(0.02)
        tube.SetNumberOfSides(8)
        tube.CappingOn()
        tube.Update()

        cam = CameraConfig(position=(8, 8, 6), focal_point=(2.25, 2.25, 1.25), view_up=(0, 0, 1))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='turbo', array_name='VelocityMag',
            show_scalar_bar=True, scalar_bar_title='Velocity (m/s)',
        )
        PNG = render_to_png(tube.GetOutput(), cfg, cam)
    """),

    # 6. Medical: head CT axial slice
    "ct_head_slice": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import apply_filter
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(DATA_DIR + '/head.vti')
        reader.Update()

        sliced = apply_filter(reader.GetOutput(), 'slice', origin=[128, 128, 93], normal=[0, 0, 1])
        cam = CameraConfig(position=(128, 128, 400), focal_point=(128, 128, 93), view_up=(0, 1, 0))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='grayscale', array_name='Scalars_',
            show_scalar_bar=True, scalar_bar_title='CT Density',
        )
        PNG = render_to_png(sliced, cfg, cam)
    """),

    # 7. Molecular: Iron Protein electron density isosurfaces
    "ironprot": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import apply_filter
        from parapilot.engine.renderer import RenderConfig, render_to_png
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkStructuredPointsReader()
        reader.SetFileName(DATA_DIR + '/ironProt.vtk')
        reader.Update()

        contoured = apply_filter(reader.GetOutput(), 'contour', array_name='scalars', values=[80, 150])

        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(contoured)
        norms.ComputePointNormalsOn()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = contoured.GetBounds()
        elev.SetLowPoint(0, b[2], 0)
        elev.SetHighPoint(0, b[3], 0)
        elev.Update()

        cam = CameraConfig(position=(90, 70, 110), focal_point=(34, 34, 34), view_up=(0, 1, 0))
        cfg = RenderConfig(
            width=1920, height=1080, background=(0.04, 0.04, 0.06),
            colormap='plasma', array_name='Elevation',
            show_scalar_bar=True, scalar_bar_title='Electron Density',
        )
        PNG = render_to_png(elev.GetOutput(), cfg, cam)
    """),
}


# ---------------------------------------------------------------------------
# Orbit GIF animations — camera rotates 360° around subject
# Each snippet must set: DATA (vtk dataset), CFG (RenderConfig), CAM_CENTER,
# CAM_RADIUS, CAM_HEIGHT, VIEW_UP
# ---------------------------------------------------------------------------

ORBIT_RENDERS: dict[str, str] = {
    # Dragon orbit — plasma + elevation, no scalar bar for cleaner animation
    "dragon_orbit": textwrap.dedent("""\
        import vtk
        from parapilot.engine.renderer import RenderConfig
        from parapilot.engine.camera import CameraConfig

        reader = vtk.vtkPLYReader()
        reader.SetFileName(DATA_DIR + '/dragon.ply')
        reader.Update()

        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(reader.GetOutput())
        norms.ComputePointNormalsOn()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = reader.GetOutput().GetBounds()
        elev.SetLowPoint(0, b[2], 0)
        elev.SetHighPoint(0, b[3], 0)
        elev.Update()

        DATA = elev.GetOutput()
        CFG = RenderConfig(
            width=480, height=270, background=(0.04, 0.04, 0.06),
            colormap='plasma', array_name='Elevation',
            show_scalar_bar=False,
        )
        # Center on model, orbit in XZ plane
        cx = (b[0] + b[1]) / 2
        cy = (b[2] + b[3]) / 2
        cz = (b[4] + b[5]) / 2
        CAM_CENTER = (cx, cy, cz)
        CAM_RADIUS = 0.25
        CAM_HEIGHT = cy + 0.08
        VIEW_UP = (0, 1, 0)
    """),

    # CT skull orbit — inferno + elevation
    "ct_skull_orbit": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import apply_filter
        from parapilot.engine.renderer import RenderConfig

        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(DATA_DIR + '/head.vti')
        reader.Update()

        contoured = apply_filter(reader.GetOutput(), 'contour', array_name='Scalars_', values=[1200])
        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(contoured)
        norms.ComputePointNormalsOn()
        norms.SplittingOff()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = contoured.GetBounds()
        elev.SetLowPoint(0, 0, b[4])
        elev.SetHighPoint(0, 0, b[5])
        elev.Update()

        DATA = elev.GetOutput()
        CFG = RenderConfig(
            width=480, height=270, background=(0.04, 0.04, 0.06),
            colormap='inferno', array_name='Elevation',
            show_scalar_bar=False,
        )
        cx, cy, cz = 128, 128, 93
        CAM_CENTER = (cx, cy, cz)
        CAM_RADIUS = 280
        CAM_HEIGHT = cz + 60
        VIEW_UP = (0, 0, 1)
    """),

    # Iron protein orbit — plasma + elevation
    "ironprot_orbit": textwrap.dedent("""\
        import vtk
        from parapilot.engine.filters import apply_filter
        from parapilot.engine.renderer import RenderConfig

        reader = vtk.vtkStructuredPointsReader()
        reader.SetFileName(DATA_DIR + '/ironProt.vtk')
        reader.Update()

        contoured = apply_filter(reader.GetOutput(), 'contour', array_name='scalars', values=[80, 150])

        norms = vtk.vtkPolyDataNormals()
        norms.SetInputData(contoured)
        norms.ComputePointNormalsOn()
        norms.Update()

        elev = vtk.vtkElevationFilter()
        elev.SetInputConnection(norms.GetOutputPort())
        b = contoured.GetBounds()
        elev.SetLowPoint(0, b[2], 0)
        elev.SetHighPoint(0, b[3], 0)
        elev.Update()

        DATA = elev.GetOutput()
        CFG = RenderConfig(
            width=480, height=270, background=(0.04, 0.04, 0.06),
            colormap='plasma', array_name='Elevation',
            show_scalar_bar=False,
        )
        cx = (b[0] + b[1]) / 2
        cy = (b[2] + b[3]) / 2
        cz = (b[4] + b[5]) / 2
        CAM_CENTER = (cx, cy, cz)
        CAM_RADIUS = 80
        CAM_HEIGHT = cy + 20
        VIEW_UP = (0, 1, 0)
    """),
}


def download_data() -> bool:
    """Download example data files from pyvista/vtk-data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True
    for fname in DATA_FILES:
        target = DATA_DIR / fname
        if target.exists() and target.stat().st_size > 0:
            print(f"  {fname}: cached ({target.stat().st_size // 1024}KB)")
            continue
        url = f"{VTK_DATA_URL}/{fname}"
        print(f"  {fname}: downloading...", end=" ", flush=True)
        result = subprocess.run(
            ["curl", "-sLo", str(target), url],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0 or not target.exists():
            print("FAIL")
            all_ok = False
        else:
            print(f"OK ({target.stat().st_size // 1024}KB)")
    return all_ok


def run_render(name: str, code: str) -> bool:
    """Run a render in an isolated subprocess."""
    import os

    preamble = (
        f"import sys, io, os\n"
        f"os.environ['VTK_DEFAULT_OPENGL_WINDOW'] = 'vtkEGLRenderWindow'\n"
        f"sys.path.insert(0, {str(PROJECT_ROOT / 'src')!r})\n"
        f"DATA_DIR = {str(DATA_DIR)!r}\n\n"
    )
    postamble = (
        "\n# Save optimized 960x540 (PNG + WebP)\n"
        "from PIL import Image\n"
        f"out_png = {str(OUT_DIR)!r} + '/{name}.png'\n"
        f"out_webp = {str(OUT_DIR)!r} + '/{name}.webp'\n"
        "img = Image.open(io.BytesIO(PNG))\n"
        "resized = img.resize((960, 540), Image.LANCZOS)\n"
        "resized.save(out_png, 'PNG', optimize=True)\n"
        "resized.save(out_webp, 'WEBP', quality=85, method=6)\n"
        "import os\n"
        "png_kb = os.path.getsize(out_png) // 1024\n"
        "webp_kb = os.path.getsize(out_webp) // 1024\n"
        "print(f'{png_kb}KB png / {webp_kb}KB webp')\n"
    )
    wrapper = preamble + code + postamble

    env = {**os.environ, "VTK_DEFAULT_OPENGL_WINDOW": "vtkEGLRenderWindow"}
    env.pop("DISPLAY", None)  # Force EGL, avoid GLX attempts

    result = subprocess.run(
        [sys.executable, "-c", wrapper],
        capture_output=True, text=True, timeout=120,
        env=env,
    )

    if result.returncode != 0:
        err = result.stderr.strip().splitlines()[-1] if result.stderr else "unknown"
        print(f"  FAIL: {err}")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"    {line}")
        return False

    size = result.stdout.strip()
    print(f"  {name}.png: {size}")
    return True


def run_orbit_render(name: str, code: str) -> bool:
    """Run an orbit GIF render in an isolated subprocess.

    User code must set: DATA, CFG, CAM_CENTER, CAM_RADIUS, CAM_HEIGHT, VIEW_UP.
    This function renders 24 frames rotating 360° and saves GIF + animated WebP.
    """
    import os

    n_frames = 24
    fps = 8

    preamble = (
        f"import sys, io, os, math\n"
        f"os.environ['VTK_DEFAULT_OPENGL_WINDOW'] = 'vtkEGLRenderWindow'\n"
        f"sys.path.insert(0, {str(PROJECT_ROOT / 'src')!r})\n"
        f"DATA_DIR = {str(DATA_DIR)!r}\n\n"
    )
    postamble = textwrap.dedent(f"""\

        # --- Orbit rendering loop ---
        from parapilot.engine.renderer import render_to_png
        from parapilot.engine.camera import CameraConfig
        from PIL import Image

        n_frames = {n_frames}
        fps = {fps}
        frames = []

        for fi in range(n_frames):
            angle = 2 * math.pi * fi / n_frames
            if VIEW_UP == (0, 0, 1):
                pos = (
                    CAM_CENTER[0] + CAM_RADIUS * math.cos(angle),
                    CAM_CENTER[1] + CAM_RADIUS * math.sin(angle),
                    CAM_HEIGHT,
                )
            else:
                pos = (
                    CAM_CENTER[0] + CAM_RADIUS * math.cos(angle),
                    CAM_HEIGHT,
                    CAM_CENTER[2] + CAM_RADIUS * math.sin(angle),
                )
            cam = CameraConfig(position=pos, focal_point=CAM_CENTER, view_up=VIEW_UP)
            png_bytes = render_to_png(DATA, CFG, cam)
            frames.append(Image.open(io.BytesIO(png_bytes)))

        # Save optimized GIF (128-color palette)
        out_gif = {str(OUT_DIR)!r} + '/{name}.gif'
        duration_ms = max(1, int(1000 / fps))
        palette = [f.convert('RGB').quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in frames]
        palette[0].save(
            out_gif, format='GIF', save_all=True,
            append_images=palette[1:], duration=duration_ms,
            loop=0, optimize=True,
        )

        # Save animated WebP (much smaller)
        out_webp = {str(OUT_DIR)!r} + '/{name}.webp'
        rgb = [f.convert('RGB') for f in frames]
        rgb[0].save(
            out_webp, format='WEBP', save_all=True,
            append_images=rgb[1:], duration=duration_ms,
            loop=0, quality=70, method=4,
        )

        gif_kb = os.path.getsize(out_gif) // 1024
        webp_kb = os.path.getsize(out_webp) // 1024
        print(f'{{gif_kb}}KB gif / {{webp_kb}}KB webp ({{n_frames}} frames @ {{fps}}fps)')
    """)
    wrapper = preamble + code + postamble

    env = {**os.environ, "VTK_DEFAULT_OPENGL_WINDOW": "vtkEGLRenderWindow"}
    env.pop("DISPLAY", None)

    result = subprocess.run(
        [sys.executable, "-c", wrapper],
        capture_output=True, text=True, timeout=300,
        env=env,
    )

    if result.returncode != 0:
        err = result.stderr.strip().splitlines()[-1] if result.stderr else "unknown"
        print(f"  FAIL: {err}")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"    {line}")
        return False

    size = result.stdout.strip()
    print(f"  {name}: {size}")
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(DATA_FILES)} example datasets...\n")
    download_data()

    print(f"\nGenerating {len(RENDERS)} showcase renders (isolated subprocess per render)...\n")

    success = 0
    for i, (name, code) in enumerate(RENDERS.items(), 1):
        print(f"[{i}/{len(RENDERS)}] {name}")
        if run_render(name, code):
            success += 1

    print(f"\nGenerating {len(ORBIT_RENDERS)} orbit animations...\n")

    anim_success = 0
    for i, (name, code) in enumerate(ORBIT_RENDERS.items(), 1):
        print(f"[{i}/{len(ORBIT_RENDERS)}] {name}")
        if run_orbit_render(name, code):
            anim_success += 1

    total = success + anim_success
    total_expected = len(RENDERS) + len(ORBIT_RENDERS)
    print(f"\nDone: {total}/{total_expected} ({success} renders + {anim_success} animations) saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
