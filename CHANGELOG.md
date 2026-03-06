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
- Per-block styling for multiblock datasets (`render_multiblock()`)
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

- Test count: 310 → 1070 (99% coverage, 1 uncovered line)
- File format support: 26 → 50+ (via meshio fallback)
- CI matrix: Python 3.10/3.12 → 3.10/3.11/3.12/3.13

### Fixed

- Contour: empty output guard with data range diagnostics
- Streamlines: auto seed points from dataset bounds
- Slice/clip: auto origin from dataset center
- Renderer: reject 0-point datasets in `_resolve_renderable`
- PNG extraction: O(n) byte-by-byte copy replaced with numpy bulk copy
- CI: lint/type check separated into parallel job for faster feedback
- CI: VTK headless test skip mechanism (3-layer defense: conftest set + `*_vtk.py` pattern + env var)

### Added (CI/CD & Quality)

- 5 quality gates: G1 ruff, G2 mypy strict, G3 pytest×4 Python, G4 coverage 75%+, G5 CodeQL+pip-audit
- `security.yml`: CodeQL analysis + pip-audit dependency scanning
- `pr-quality.yml`: auto-labeling by size (XS/S/M/L/XL) and file path
- `dependency-review.yml`: license + vulnerability check on PR dependencies
- `release-drafter.yml`: auto-generated release notes from PR labels
- `stale.yml`: auto-close inactive issues (60d) and PRs (30d)
- `auto-merge.yml`: auto-merge dependabot PRs after CI passes
- `welcome.yml`: welcome message for first-time contributors
- Branch protection: 4 required CI checks, dismiss stale reviews
- `.pre-commit-config.yaml`: ruff, mypy, gitleaks, trailing-whitespace
- `CODEOWNERS`: @kimimgo as default reviewer
- Contributor recognition tiers in CONTRIBUTING.md
- MCP protocol compliance test suite (14 tests)
- Performance benchmark framework (`benchmarks/bench_render.py`)
- Social preview image (1280×640) for GitHub
- Launch posts: HN, Reddit (3 subs), Twitter, LinkedIn, Discord drafts
- Aerodynamics and structural FEA workflow examples
- sdist excludes non-source files (251MB → 192KB package size)
- Dependabot: github-actions ecosystem for automatic action version updates

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
