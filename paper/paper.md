---
title: 'viznoir: Headless CAE Post-Processing through AI Coding Assistants'
tags:
  - Python
  - VTK
  - CFD
  - CAE
  - MCP
  - post-processing
  - visualization
authors:
  - name: Imgyu Kim
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 6 March 2026
bibliography: paper.bib
---

# Summary

`viznoir` is a headless post-processing server for computational
engineering simulations (CFD, FEA, thermal analysis) that enables AI
coding assistants to generate publication-quality visualizations through
natural language. It implements the Model Context Protocol (MCP)
[@modelcontextprotocol], exposing 18 tools for rendering, slicing,
contouring, animation, and quantitative data extraction from simulation
results. By operating entirely without a graphical user interface,
`viznoir` bridges the gap between large language models (LLMs) and the
VTK-based scientific visualization ecosystem [@schroeder2006vtk].

# Statement of Need

Post-processing simulation results is a critical bottleneck in
computational engineering workflows. Tools such as ParaView
[@ahrens2005paraview] and VisIt [@childs2012visit] provide powerful
visualization capabilities but require manual GUI interaction, which
limits their integration with automated pipelines and AI assistants.

The emergence of AI coding assistants (Claude Code, Cursor, Windsurf)
has created demand for programmatic post-processing that can be driven
by natural language. However, existing MCP servers for scientific
visualization [@llnl_paraview_mcp] are tied to GUI-attached ParaView
sessions, cannot run in containerized environments, and lack automated
testing.

`viznoir` addresses these limitations by providing:

1. **Headless rendering** via VTK's EGL (GPU) and OSMesa (CPU) backends,
   enabling deployment in Docker containers, CI pipelines, and cloud
   environments without display servers.
2. **Physics-aware defaults** that automatically select appropriate
   colormaps, camera angles, and representations based on field names
   and dataset geometry.
3. **A pipeline DSL** for composing multi-step filter chains as
   declarative JSON, enabling reproducible visualization workflows.
4. **Comprehensive testing** with 1048 automated tests covering 99% of
   the codebase.

# Architecture

`viznoir` is structured in three layers (\autoref{fig:architecture}):

- **MCP Server Layer** (`server.py`): Registers 18 tools, 11 resources,
  and 3 prompts with the FastMCP framework [@fastmcp].
- **Pipeline Layer** (`core/`): Compiles Pydantic-validated pipeline
  definitions into VTK Python scripts, executes them via subprocess or
  Docker, and parses output artifacts.
- **Engine Layer** (`engine/`): Provides direct VTK API functions for
  reading 50+ file formats, applying 20 filter types, and rendering
  with cinematic quality (PBR materials, SSAO, FXAA, 3-point lighting).

The separation of compilation and execution enables dual-mode operation:
local subprocess execution for development, and GPU-accelerated Docker
containers for production deployment.

# Key Features

**Format support.** Native VTK readers handle OpenFOAM (`.foam`),
VTK XML (`.vtu`, `.vtp`, `.vts`, `.vti`), STL, CGNS, Exodus II,
EnSight, and XDMF. A meshio fallback [@schlomer2022meshio] extends
support to 50+ additional formats including Abaqus, Gmsh, and ANSYS.

**Cinematic rendering.** The `cinematic_render` tool produces
publication-quality images with PCA-based automatic camera positioning,
physically-based rendering (PBR) materials, screen-space ambient
occlusion (SSAO), and fast approximate anti-aliasing (FXAA).

**Split-pane animation.** The `split_animate` tool generates
synchronized multi-view GIF animations combining 3D renders with
time-series graphs, enabling visual correlation of spatial and temporal
phenomena.

**Comparison workflows.** The `compare` tool supports side-by-side,
overlay, and difference modes for comparing simulation results across
parameter studies or against experimental data.

# Availability

`viznoir` is available on PyPI as `mcp-server-viznoir` and as
Docker images for both GPU (EGL) and CPU-only (OSMesa) deployment.
Source code, documentation, and issue tracker are hosted at
[github.com/kimimgo/viznoir](https://github.com/kimimgo/viznoir).

# Acknowledgements

The author thanks the VTK [@schroeder2006vtk] and FastMCP [@fastmcp]
communities for their foundational open-source contributions.

# References
