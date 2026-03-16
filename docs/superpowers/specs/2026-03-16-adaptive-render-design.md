# Adaptive Render Resolution — Design Spec

**Date:** 2026-03-16
**Status:** Approved (spec review passed round 3)
**Branch:** feat/adaptive-render-v2 (from main)

## Problem

1. Every MCP image tool defaults to 1920x1080, producing 316KB base64 per call. AI agents consume this as context. A 10-render session wastes 3.2MB on images alone.
2. Current adaptive render (feat/adaptive-render-benchmark) hardcodes resolution mapping in server.py with Japanese comments, a width/height edge case bug, and inconsistent tool coverage.
3. streamlines tool fails on cell-only vector data (no auto cell-to-point conversion).
4. PNG encoding is 93% of render time (31ms of 33ms at 1080p) with no compression control.

## Solution: Config-Driven Render Profiles

### New module: `core/profiles.py` (~60 LOC)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RenderProfile:
    """Resolution + encoding settings for a single render call."""
    width: int
    height: int
    png_compress_level: int  # 0-9 (0=fastest, 9=smallest)
    label: str

PROFILES: dict[str, RenderProfile] = {
    "analyze":  RenderProfile(854,  480,  6, "analyze"),
    "preview":  RenderProfile(1280, 720,  6, "preview"),
    "publish":  RenderProfile(1920, 1080, 9, "publish"),
}

def resolve_profile(
    purpose: str = "analyze",
    width: int | None = None,
    height: int | None = None,
) -> RenderProfile:
    """Resolve a RenderProfile from purpose preset + optional overrides.

    Rules:
    - Both width and height provided: custom profile (full override)
    - Neither provided: use purpose preset
    - Only one provided: raise ValueError (aspect ratio protection)
    """
    if (width is None) != (height is None):
        raise ValueError(
            f"Specify both width and height, or neither. Got width={width}, height={height}"
        )
    if width is not None and height is not None:
        if not (1 <= width <= 8192 and 1 <= height <= 8192):
            raise ValueError(
                f"width and height must be 1-8192. Got {width}x{height}"
            )
        base = PROFILES.get(purpose, PROFILES["analyze"])
        return RenderProfile(width, height, base.png_compress_level, "custom")
    profile = PROFILES.get(purpose)
    if profile is None:
        raise ValueError(f"Unknown purpose '{purpose}'. Available: {list(PROFILES)}")
    return profile
```

### Changes to `engine/renderer.py`

1. Add `png_compress_level: int = 6` to `RenderConfig`.
2. Change `_capture_png(rw)` → `_capture_png(rw, compress_level: int = 6)`.
3. In `_capture_png()`, call `writer.SetCompressionLevel(compress_level)` on vtkPNGWriter.
4. **Update ALL 3 call sites** of `_capture_png(rw)` to pass `self._config.png_compress_level`:
   - `VTKRenderer.render()` empty-dataset early return (line ~148)
   - `VTKRenderer.render()` normal return (line ~213)
   - `VTKRenderer.render_multiple()` (line ~356)
   - Note: `render_to_png()` delegates to `VTKRenderer.render()` — no separate change needed.

```python
# RenderConfig addition
@dataclass
class RenderConfig:
    ...
    png_compress_level: int = 6  # 0-9

# _capture_png change
def _capture_png(rw, compress_level: int = 6) -> bytes:
    ...
    writer = vtk.vtkPNGWriter()
    writer.SetCompressionLevel(compress_level)
    ...
```

**Note:** `engine/renderer_cine.py` has its own PNG capture path. Compression level plumbing for cinematic render is out of scope for v1 — cinematic output is publication-quality by design (high compression is appropriate).

### Changes to `engine/filters.py`

Auto cell-to-point conversion for filters that require point data.

```python
def _auto_cell_to_point(dataset, array_name: str):
    """Convert cell data to point data if array exists only in cell data."""
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    if pd.GetArray(array_name) is not None:
        return dataset  # already point data
    if cd.GetArray(array_name) is None:
        return dataset  # not in cell data either
    c2p = vtk.vtkCellDataToPointData()
    c2p.SetInputData(dataset)
    c2p.Update()
    return c2p.GetOutput()
```

Applied to: `stream_tracer()`, `glyph()`.

### Changes to `server.py`

1. **Delete** `_PURPOSE_RESOLUTION` dict and `_resolve_size()` function.
2. **Import** `resolve_profile` from `core.profiles`.
3. **Apply** `purpose` parameter to 7 image-returning tools (all get `purpose: Literal[...] = "analyze"`, `width: int | None = None`, `height: int | None = None`):
   - render, slice, contour, clip, streamlines, compare, batch_render
4. **Not changed**:
   - `cinematic_render` — has own quality preset system
   - `volume_render` — internally delegates to `cinematic_render_impl` which controls resolution via quality preset. Adding `purpose` would conflict with `quality`. Excluded.
5. **Fix `compare_impl`**: Remove hardcoded `(width or 1920) // 2` and `(height or 1080)` fallbacks in `tools/compare.py` line ~66. After server.py changes, `compare` tool passes `profile.width`/`profile.height` (always integers), so the `or` fallbacks are dead code and should be removed for clarity.

Tool signature pattern (other parameters unchanged):
```python
async def render(
    ...,  # file_path, field_name, association, colormap, camera, scalar_range
    purpose: Literal["analyze", "preview", "publish"] = "analyze",
    width: int | None = None,
    height: int | None = None,
    ...,  # timestep, blocks, output_filename
) -> Image:
    profile = resolve_profile(purpose, width, height)
    result = await render_impl(..., width=profile.width, height=profile.height)
```

### Test Plan

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_core/test_profiles.py` (new) | ~8 | resolve_profile: purpose presets, custom override, one-sided error, unknown purpose |
| `tests/test_engine/test_filters.py` (add) | ~3 | _auto_cell_to_point: cell-only, point-exists, missing field |
| `tests/test_engine/test_renderer.py` (add) | ~2 | RenderConfig.png_compress_level field round-trip (no VTK needed); actual SetCompressionLevel call tested only locally (CI skips GPU tests via `*_vtk.py` pattern) |
| existing server tests | ~0 change | purpose defaults to "analyze", existing tests pass (width/height now None) |

### File Change Summary

| File | Action | LOC |
|------|--------|-----|
| `core/profiles.py` | New | ~60 |
| `engine/renderer.py` | Modify | ~15 |
| `engine/filters.py` | Modify | ~25 |
| `server.py` | Modify | ~40 |
| `tools/compare.py` | Modify (remove fallback) | ~5 |
| `tests/test_core/test_profiles.py` | New | ~50 |
| `tests/test_engine/test_filters.py` | Modify | ~20 |
| **Total** | | **~215** |

### Out of Scope

- Dual registry unification (PascalCase vs snake_case) — separate issue
- PIL-based PNG encoding — benchmarked but deferred (vtkPNGWriter compression level is sufficient)
- Context budget tracking (auto-downgrade after N images) — v0.8.0 roadmap
- cinematic_render changes — already has quality presets

### Migration / Backward Compatibility

- `width: int = 1920` → `width: int | None = None` — MCP clients that explicitly pass width+height still work.
- `purpose` defaults to `"analyze"` (480p) — breaking change in default resolution. This is intentional: AI analysis does not need 1080p. Users wanting 1080p pass `purpose="publish"` or explicit width/height.
- No changes to internal `render_impl` / `slice_impl` signatures — they still receive `width: int, height: int`.

### Performance Impact

| Metric | Before (1080p default) | After (480p default) |
|--------|----------------------|---------------------|
| Render time | 61 ms | 17 ms |
| PNG size | 243 KB | 77 KB |
| Base64 context | 316 KB | 100 KB |
| 10-render session | 3.2 MB context | 1.0 MB context |
