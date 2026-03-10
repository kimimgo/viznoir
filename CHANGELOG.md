# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-03-11

### Added

- `inspect_physics` MCP tool: L2 field topology analysis (vortex detection, stagnation points, gradient statistics) + L3 case context (OpenFOAM BCs, transport properties, Re computation)
- `context/` module: CaseContext data models, ContextParser protocol, GenericContextParser (mesh quality), OpenFOAMContextParser (BCs, solver info, transport properties, derived quantities)
- `engine/topology.py`: L2 field topology analyzer — vortex detection (Q/λ₂ criteria), critical point classification, centerline probe, gradient statistics
- Science Storyteller v2 pipeline: `inspect_physics` → `cinematic_render` → `compose_assets` end-to-end workflow
- CODEOWNERS file for required code review
- PR template validation (CI-enforced): Description + Test Plan sections required
- PR auto-labeling by file path (context, animation labels)

### Changed

- MCP tools: 21 → 22
- Test count: 1315 → 1439+ (97% coverage)
- CI test count guard: 1290 → 1430
- CI: added `ruff format --check` step
- README: Before/After hero section (ParaView GUI vs viznoir), domain-expert gallery with scale metrics
- Gallery captions: generic labels → domain-specific with cell/face counts

### Fixed

- `openfoam.py`: file encoding error on non-UTF8 boundary files (`read_text(errors="replace")`)
- `openfoam.py`: backup/swap files (`.orig`, `.bak`, `.swp`) incorrectly parsed as boundary conditions
- `openfoam.py`: `parse_dataset()` now raises `NotImplementedError` with clear guidance
- `server.py`: path traversal validation for `case_dir` parameter against `VIZNOIR_DATA_DIR`
- `compositor.py`: removed dead `TYPE_CHECKING` import

### Security

- Path traversal prevention strengthened for `inspect_physics` case_dir parameter
- Branch protection: required reviews (CODEOWNERS), dismiss stale reviews, conversation resolution, enforce admins

## [0.5.0] - 2026-03-08

### Added

- **Science Storyteller Pipeline**: analyze → render → compose end-to-end workflow
- `analyze_data` MCP tool: VTK dataset insight extraction (field statistics, anomaly detection, physics context, cross-field analysis, governing equation suggestion)
- `compose_assets` MCP tool: multi-asset composition with 4 layout modes (story, grid, slides, video)
- `engine/analysis.py`: field classification, exact field mapping (OpenFOAM convention), correlation analysis, fitted equations
- `anim/latex.py`: LaTeX → SVG → PNG rendering with body:color:preamble cache (cold 217ms, warm 10ms)
- `anim/compositor.py`: story/grid/slides layout rendering + ffmpeg video export (RGBA → libx264 yuv420p)
- `anim/timeline.py`: scene sequencing with prefix-sum + bisect O(log n) lookup
- `anim/transitions.py`: fade_in, fade_out, dissolve, wipe transitions (Image.blend C-level)
- `anim/easing.py`: 17 easing functions (linear, ease_in/out_quad/cubic/sine/expo/circ/back/elastic/bounce)
- GitHub Pages deployment workflow (Astro landing page)
- Branch protection: force push/delete blocked, required status checks

### Changed

- Test count: 1134 → 1315+ (97% coverage local, ~82% CI)
- MCP tools: 18 → 21
- CI test count guard: 1120 → 1290

### Fixed

- PIL.Image type hint: `from PIL.Image import Image` in TYPE_CHECKING (module vs class)
- np.linalg.norm mypy: explicit `result: np.ndarray` annotation for Any return
- LaTeX SVG cache test: conditional on `LATEX_AVAILABLE` for CI without LaTeX

## [0.3.0] - 2026-03-07

### Changed

- README.md redesigned: 224 → 101 lines, benchmark-driven "proof first" structure
- README.ko.md: matching Korean translation
- Landing page: 9 components → 5 sections (Hero, Proof, Showcase, QuickStart, Footer)
- Removed: Architecture, Features, Stats, Comparison, PluginShowcase components
- New: Proof.astro (unified stats + comparison matrix)
- Showcase: 44 images → 6 curated picks in 2x3 grid
- QuickStart: absorbed PluginShowcase, 3-step install flow

## [0.2.0] - 2026-03-07

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
- MCP Tasks support: `animate`, `split_animate`, `execute_pipeline` as async background tasks (FastMCP 3.x, backward-compatible with 2.x)
- `pip install mcp-server-viznoir[tasks]` for FastMCP 3.x with MCP Tasks
- 8 path traversal security tests: symlink escape, null byte injection, prefix attack
- Dockerfile.cpu for CPU-only (OSMesa) deployment without GPU
- MkDocs Material API documentation site (16 pages)
- Thermal analysis workflow example (`examples/thermal_analysis.json`)
- JOSS paper draft (`paper/paper.md`)
- Structured logging framework (`VIZNOIR_LOG_LEVEL` env var)
- Custom exception hierarchy (`ViznoirError`, `FileFormatError`, etc.)
- Render window auto-regeneration (every 100 renders) to prevent GPU memory leaks
- Python 3.11/3.13 CI test matrix
- Codecov coverage reporting
- `smithery.yaml` for MCP registry registration
- Property-based testing with Hypothesis (11 fuzz tests for path traversal, colormaps, Pydantic models)
- SECURITY.md with responsible disclosure policy
- `.pre-commit-config.yaml` (ruff + mypy + pre-commit-hooks)
- OpenSSF Scorecard CI workflow
- PLY/OBJ/STL integration tests (real VTK I/O roundtrip)
- Troubleshooting guide (docs/troubleshooting.md, 10 common issues)
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- `__main__.py` for `python -m viznoir` support
- Blue to Red Rainbow and X Ray colormaps (16 → 18 colormaps)
- Colormap resource enhanced with field-type recommendations

### Changed

- Test count: 310 → 1134 (99% coverage)
- CI coverage threshold: 75% → 80%
- File format support: 26 → 50+ (via meshio fallback)
- CI matrix: Python 3.10/3.12 → 3.10/3.11/3.12/3.13

### Fixed

- postfx.py: narrow exception handling — catch specific VTK errors instead of bare `Exception`
- readers.py: narrow meshio fallback exception to avoid masking `MemoryError`/`KeyboardInterrupt`
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
- Mutation testing framework (mutmut) for test quality verification
- Module-level resource/prompt registration (no `main()` call required)
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
- Path traversal prevention when `VIZNOIR_DATA_DIR` is set
- Landing page (Astro 5 + Tailwind) with interactive showcase gallery

[Unreleased]: https://github.com/kimimgo/viznoir/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/kimimgo/viznoir/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/kimimgo/viznoir/compare/v0.3.0...v0.5.0
[0.3.0]: https://github.com/kimimgo/viznoir/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/kimimgo/viznoir/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kimimgo/viznoir/releases/tag/v0.1.0
