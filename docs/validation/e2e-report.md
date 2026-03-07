# viznoir E2E Validation Report

**Date**: 2026-03-05 20:48:53
**Validator**: automated (docs/validation/test_e2e.py)

## Test Environment

| Component | Version |
|-----------|---------|
| Python | 3.12.12 |
| VTK | 9.5.2 |
| PyVista | 0.46.5 |
| OS | Linux 5.15.0-161-generic |
| GPU | RTX 4090 24GB (EGL headless) |
| Render Backend | gpu |

## Test Datasets

| Dataset | Path | Description |
|---------|------|-------------|
| wavelet | wavelet.vtk | Structured grid, RTData scalar field |
| sphere | sphere.vtk | Polygonal mesh, elevation scalar |
| flow | flow.vtk | Structured grid, velocity vectors + speed scalar |
| uniform | uniform.vti | Uniform image data, random scalar |

## Results Summary

| Metric | Value |
|--------|-------|
| Total Tests | 19 |
| Passed | 18 |
| Failed | 0 |
| Skipped | 1 |
| **Success Rate** | **100.0%** |
| Avg Render Time | 0.57s |

## Detailed Results

| # | Tool | Dataset | Time(s) | Output Size | Status | Notes |
|---|------|---------|---------|-------------|--------|-------|
| 1 | inspect_data | wavelet | 0.49 | 411B | **PASS** |  |
| 2 | render | wavelet | 0.62 | 188,428B | **PASS** |  |
| 3 | render (colormap) | sphere | 0.64 | 116,032B | **PASS** |  |
| 4 | slice (auto-origin) | wavelet | 0.62 | 132,425B | **PASS** |  |
| 5 | slice (explicit) | uniform | 0.63 | 289,547B | **PASS** |  |
| 6 | contour (valid iso) | wavelet | 0.59 | 153,903B | **PASS** |  |
| 7 | contour (out-of-range) | wavelet | - | - | **PASS** | Correctly rejected: VTK script exited with code 1.
stderr: Traceback (most recen |
| 8 | clip (auto-origin) | wavelet | 0.77 | 157,105B | **PASS** |  |
| 9 | clip (invert) | wavelet | 0.61 | 168,863B | **PASS** |  |
| 10 | streamlines (auto-seed) | flow | 0.60 | 68,899B | **PASS** |  |
| 11 | streamlines (explicit) | flow | 0.63 | 74,876B | **PASS** |  |
| 12 | plot_over_line | wavelet | 0.61 | 2,369B | **PASS** |  |
| 13 | extract_stats | wavelet | 0.44 | 159B | **PASS** |  |
| 14 | integrate_surface | sphere | 0.45 | 39B | **PASS** |  |
| 15 | animate (orbit/gif) | wavelet | 0.90 | 800,991B | **PASS** |  |
| 16 | execute_pipeline | wavelet | 0.73 | 136,308B | **PASS** |  |
| 17 | execute_pipeline (threshold) | wavelet | 0.74 | 177,210B | **PASS** |  |
| 18 | pv_isosurface | N/A | - | - | **SKIP** | Requires DualSPHysics Docker image + bi4 data — skipped in E2E validation |
| 19 | split_animate (frames) | wavelet | 0.89 | 8B | **PASS** | frames=8, composed=8 |

## Issues Found

No issues found.

## Output Files

All output files saved to `/tmp/viznoir_test/output/`:

- [x] `render_wavelet.png` (188,428B)
- [x] `render_sphere_viridis.png` (116,032B)
- [x] `slice_wavelet_auto.png` (132,425B)
- [x] `slice_uniform_explicit.png` (289,547B)
- [x] `contour_wavelet_valid.png` (153,903B)
- [x] `clip_wavelet_auto.png` (157,105B)
- [x] `clip_wavelet_invert.png` (168,863B)
- [x] `streamlines_flow_auto.png` (68,899B)
- [x] `streamlines_flow_explicit.png` (74,876B)
- [x] `animate_orbit.gif` (800,991B)
- [x] `pipeline_slice.png` (136,308B)
- [x] `pipeline_threshold.png` (177,210B)

## Performance Summary

| Category | Count | Avg Time(s) |
|----------|-------|-------------|
| Rendering (render/slice/contour/clip/streamlines) | 10 | 0.57 |
| Data extraction (stats/plot_over_line/integrate) | 3 | 0.50 |
| Animation | 2 | 0.90 |

## Reproduction

```bash
cd /home/imgyu/workspace/02_active/dev/kimtech
pip install -e ".[dev]"
python docs/validation/test_e2e.py
```
