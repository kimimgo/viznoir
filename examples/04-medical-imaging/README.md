# Example 04: Medical Imaging — CT / MRI Visualization

**Domain**: Medical Imaging (CT, MRI, PET)
**Typical data**: VTI volumes (converted from DICOM), NIfTI exports
**Key fields**: `RTData` (density/intensity), `scalars` (generic scalar)

## Overview

This workflow demonstrates volume rendering and cinematic-quality rendering of medical scan data. The clip step exposes a cross-sectional brain section without destructing the volume.

```
inspect_data → volume_render (density) → clip (brain section) → cinematic_render (publication)
```

## Test Dataset

viznoir ships with a wavelet VTI (`tests/fixtures/`) that mimics a medical scalar volume. For real data, convert DICOM slices to VTI using `meshio` or `vtk.vtkDICOMImageReader`.

## Step 1: Inspect Volume Metadata

```json
{
  "tool": "inspect_data",
  "arguments": {
    "file_path": "/data/medical/brain_phantom.vti"
  }
}
```

Note the scalar field name (often `RTData`, `Scalars`, or `ImageScalars`), voxel spacing, and intensity range.

## Step 2: Volume Render — Density / Intensity

```json
{
  "tool": "volume_render",
  "arguments": {
    "file_path": "/data/medical/brain_phantom.vti",
    "field_name": "RTData",
    "colormap": "CT Bone",
    "purpose": "preview"
  }
}
```

For CT bone visualization use `CT Bone`. For soft tissue use `CT Muscle` or `Grayscale`. See `viznoir://colormaps` for medical presets.

## Step 3: Clip — Reveal Internal Structure

```json
{
  "tool": "clip",
  "arguments": {
    "file_path": "/data/medical/brain_phantom.vti",
    "field_name": "RTData",
    "origin": [0.0, 0.0, 0.0],
    "normal": [0.0, 0.0, 1.0],
    "colormap": "Grayscale",
    "purpose": "preview"
  }
}
```

The axial clip (z-normal) reveals a cross-sectional slice through the brain. Adjust `origin[2]` to navigate through different axial levels.

## Step 4: Cinematic Render — Publication Quality

```json
{
  "tool": "cinematic_render",
  "arguments": {
    "file_path": "/data/medical/brain_phantom.vti",
    "field_name": "RTData",
    "colormap": "CT Bone",
    "lighting": "studio",
    "camera": "isometric",
    "purpose": "publish",
    "output_filename": "brain_ct_publication.png"
  }
}
```

`cinematic_render` applies 3-point lighting, SSAO ambient occlusion, FXAA anti-aliasing, and auto-framing. Output is 1080p at `purpose: "publish"`.

## Tips

- For MRI data, `Grayscale` or `X Ray` colormaps produce the most clinically familiar appearance.
- Use `viznoir://cinematic` to browse lighting presets: `studio`, `dramatic`, `publication`, `outdoor`.
- Use `viznoir://cameras` for camera position presets (axial, coronal, sagittal views map to standard orthographic views).
- Combine `clip` with `cinematic_render` via `execute_pipeline` for a clipped cinematic render in one pass.
