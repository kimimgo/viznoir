# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 5 new MCP tools: `cinematic_render`, `compare`, `probe_timeseries`, `batch_render`, `preview_3d` (total: 18)
- 1 new MCP resource: `capabilities` (total: 11)
- Cinematic rendering engine: PCA auto-camera, PBR materials, SSAO, FXAA, 3-point lighting, 5 quality presets
- `compare` tool: side-by-side, overlay, and difference modes for comparing datasets
- `preview_3d` tool: glTF/glB export with interactive three.js viewer
- `batch_render` tool: render multiple fields/timesteps in one call
- `probe_timeseries` tool: extract field values at a point across all timesteps
- meshio fallback reader for 50+ additional mesh formats
- 5 new VTK filters: SmoothMesh, ProbePoint, CleanPolyData, Shrink, Tube
- HTTP/SSE transport mode (`--transport sse|streamable-http`)
- Dockerfile.cpu for CPU-only (OSMesa) deployment without GPU
- MkDocs Material API documentation site (16 pages)
- Thermal analysis workflow example (`examples/thermal_analysis.json`)
- JOSS paper draft (`paper/paper.md`)
- Structured logging framework (`PARAPILOT_LOG_LEVEL` env var)
- Custom exception hierarchy (`ParapilotError`, `FileFormatError`, etc.)
- Render window auto-regeneration (every 100 renders) to prevent GPU memory leaks
- Python 3.11/3.13 CI test matrix
- Codecov coverage reporting
- `smithery.yaml` for MCP registry registration

### Changed

- Test count: 310 → 826 (83% coverage)
- File format support: 26 → 50+ (via meshio fallback)
- CI matrix: Python 3.10/3.12 → 3.10/3.11/3.12/3.13

### Fixed

- Contour: empty output guard with data range diagnostics
- Streamlines: auto seed points from dataset bounds
- Slice/clip: auto origin from dataset center
- Renderer: reject 0-point datasets in `_resolve_renderable`
- PNG extraction: O(n) byte-by-byte copy replaced with numpy bulk copy

## [0.1.0] - 2026-03-04

### Added

- 13 MCP tools: `inspect_data`, `render`, `slice`, `contour`, `clip`, `streamlines`, `plot_over_line`, `extract_stats`, `integrate_surface`, `animate`, `split_animate`, `pv_isosurface`, `execute_pipeline`
- 10 MCP resources: formats, filters, colormaps, cameras, case-presets, pipelines (CFD/FEA/split-animate), capabilities, version
- 3 MCP prompts for guided post-processing workflows
- Pipeline DSL with Pydantic models (`SourceDef`, `FilterStep`, `RenderDef`, `OutputDef`)
- VTK direct API engine — no ParaView installation required
- Headless GPU rendering via EGL (`VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow`)
- CPU fallback via OSMesa for non-GPU environments
- 26+ file format support (VTK, VTU, VTP, VTS, VTR, VTI, VTM, STL, OBJ, PLY, OpenFOAM, EnSight, CGNS, Exodus, XDMF, PVD, and more)
- Docker image with GPU EGL support for containerized deployment
- 310 pytest tests with async support (`asyncio_mode = "auto"`)
- CI pipeline: ruff lint + mypy type check + pytest (Python 3.10, 3.12)
- 14 built-in colormaps (plasma, turbo, viridis, inferno, jet, coolwarm, grayscale, etc.)
- Volume rendering support (`representation="volume"` via `vtkSmartVolumeMapper`)
- Automatic seed point generation for streamlines
- Auto-center origin for slice and clip operations
- Empty output guard with data range diagnostics for contour
- `_protect_stdout()` to shield MCP JSON-RPC stream from VTK C-level stdout pollution
- Path traversal prevention when `PARAPILOT_DATA_DIR` is set
- Landing page (Astro 5 + Tailwind) with interactive showcase gallery

[Unreleased]: https://github.com/kimimgo/parapilot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kimimgo/parapilot/releases/tag/v0.1.0
