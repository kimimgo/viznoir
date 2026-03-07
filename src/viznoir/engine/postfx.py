"""Post-processing effects — SSAO, FXAA for VTK renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from viznoir.logging import get_logger

if TYPE_CHECKING:
    import vtk

logger = get_logger("postfx")


@dataclass
class PostFXConfig:
    """Configuration for post-processing effects."""

    ssao: bool = False
    ssao_radius: float | None = None  # auto-scaled from scene if None
    ssao_bias: float | None = None
    ssao_kernel_size: int = 128
    ssao_blur: bool = True

    fxaa: bool = False
    fxaa_subpixel_blend: float = 0.75
    fxaa_contrast_threshold: float = 0.125


def apply_ssao(
    renderer: vtk.vtkRenderer,
    scene_size: float,
    *,
    radius: float | None = None,
    bias: float | None = None,
    kernel_size: int = 128,
    blur: bool = True,
) -> bool:
    """Enable Screen-Space Ambient Occlusion (SSAO) on a renderer.

    SSAO adds contact shadows where surfaces meet, greatly improving depth
    perception in scientific visualizations.

    Args:
        renderer: VTK renderer (must be added to a render window before calling).
        scene_size: Approximate scene diameter (used to auto-scale radius/bias).
        radius: SSAO sampling radius. Auto-scaled from scene_size if None.
        bias: SSAO depth bias. Auto-scaled from scene_size if None.
        kernel_size: Number of SSAO samples (higher = better quality, slower).
        blur: Apply blur to smooth SSAO noise.

    Returns:
        True if SSAO was successfully applied, False if VTK lacks support.
    """
    try:
        import vtk

        if not hasattr(vtk, "vtkSSAOPass"):
            logger.warning("vtkSSAOPass not available in this VTK build")
            return False

        basic_passes = vtk.vtkRenderStepsPass()
        ssao_pass = vtk.vtkSSAOPass()

        # Auto-scale parameters from scene geometry
        r = radius if radius is not None else 0.1 * scene_size
        b = bias if bias is not None else 0.001 * scene_size

        ssao_pass.SetRadius(r)
        ssao_pass.SetBias(b)
        ssao_pass.SetKernelSize(kernel_size)
        if blur:
            ssao_pass.BlurOn()
        else:
            ssao_pass.BlurOff()

        ssao_pass.SetDelegatePass(basic_passes)
        renderer.SetPass(ssao_pass)

        logger.debug("SSAO enabled: radius=%.4f, bias=%.4f, kernel=%d", r, b, kernel_size)
        return True

    except (AttributeError, RuntimeError, TypeError):
        logger.warning("Failed to enable SSAO", exc_info=True)
        return False


def apply_fxaa(
    renderer: vtk.vtkRenderer,
    *,
    subpixel_blend: float = 0.75,
    contrast_threshold: float = 0.125,
) -> bool:
    """Enable Fast Approximate Anti-Aliasing (FXAA) on a renderer.

    FXAA smooths jagged edges in the final image with minimal performance cost.

    Args:
        renderer: VTK renderer.
        subpixel_blend: Sub-pixel blend limit (0.0–1.0). Higher = smoother.
        contrast_threshold: Edge detection threshold. Lower = more edges smoothed.

    Returns:
        True if FXAA was successfully applied.
    """
    try:
        renderer.SetUseFXAA(True)
        opts = renderer.GetFXAAOptions()
        if opts is not None:
            opts.SetSubpixelBlendLimit(subpixel_blend)
            opts.SetRelativeContrastThreshold(contrast_threshold)
        logger.debug("FXAA enabled: subpixel=%.2f, threshold=%.3f", subpixel_blend, contrast_threshold)
        return True
    except (AttributeError, RuntimeError, TypeError):
        logger.warning("Failed to enable FXAA", exc_info=True)
        return False


def apply_postfx(
    renderer: vtk.vtkRenderer,
    config: PostFXConfig,
    scene_size: float = 1.0,
) -> None:
    """Apply all configured post-processing effects to a renderer.

    Args:
        renderer: VTK renderer.
        config: PostFX configuration.
        scene_size: Approximate scene diameter for SSAO auto-scaling.
    """
    if config.ssao:
        apply_ssao(
            renderer,
            scene_size,
            radius=config.ssao_radius,
            bias=config.ssao_bias,
            kernel_size=config.ssao_kernel_size,
            blur=config.ssao_blur,
        )

    if config.fxaa:
        apply_fxaa(
            renderer,
            subpixel_blend=config.fxaa_subpixel_blend,
            contrast_threshold=config.fxaa_contrast_threshold,
        )
