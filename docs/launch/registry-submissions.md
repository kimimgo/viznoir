# MCP Registry Submissions Guide

> viznoir v0.1.0 launch — 5 registries

## Project Info (Copy-Paste Ready)

| Field | Value |
|-------|-------|
| Name | viznoir |
| PyPI | mcp-server-viznoir |
| Description | Headless CAE post-processing MCP server for AI coding assistants |
| Long Description | Visualize CFD/FEA simulation results through 13 tools — render, slice, contour, clip, streamlines, animate, and more. VTK-based headless rendering, 50+ mesh formats, no ParaView required. |
| GitHub | https://github.com/kimimgo/viznoir |
| Landing Page | https://kimimgo.github.io/viznoir |
| License | MIT |
| Install | `pip install mcp-server-viznoir` |
| Categories | Science, Engineering, Visualization, Simulation, CAE, CFD, FEA |
| Stats | 13 tools, 10 resources, 3 prompts, 331 tests |

---

## 1. awesome-mcp-servers (GitHub, 82K+ stars)

- **Repo**: https://github.com/punkpeye/awesome-mcp-servers
- **Method**: Fork → Edit README.md → PR

### Steps

1. Fork `punkpeye/awesome-mcp-servers`
2. Add entry under **Science & Research** section (or most relevant category)
3. Submit PR

### Entry Text (1-line)

```markdown
- [viznoir](https://github.com/kimimgo/viznoir) - Headless VTK post-processing for CFD/FEA simulations. 13 tools: render, slice, contour, clip, streamlines, animate. 50+ mesh formats.
```

### PR Title

```
Add viznoir — CAE post-processing MCP server
```

### PR Body

```markdown
## viznoir

Headless CAE post-processing MCP server for AI coding assistants.

- **13 tools**: render, slice, contour, clip, streamlines, animate, plot_over_line, integrate_surface, extract_stats, inspect_data, mesh convert/analyze, execute_pipeline
- **10 resources**: format lists, colormap catalog, server capabilities
- **VTK-based**: Direct VTK API, no ParaView dependency
- **50+ mesh formats** via meshio (OpenFOAM, CGNS, Exodus, Gmsh, STL, etc.)
- **Headless rendering**: GPU (EGL) or CPU (OSMesa)
- **331 tests**, MIT license

GitHub: https://github.com/kimimgo/viznoir
Landing: https://kimimgo.github.io/viznoir
PyPI: https://pypi.org/project/mcp-server-viznoir/
```

---

## 2. Smithery.ai (2,880+ servers)

- **URL**: https://smithery.ai
- **Method**: CLI publish via `smithery.yaml` (already exists in project root)

### smithery.yaml Status

Already configured in project root with:
- name, description, vendor, sourceUrl, homepage, license
- 8 tags: vtk, cfd, cae, visualization, simulation, post-processing, headless-rendering, engineering
- stdio startCommand with configSchema (VIZNOIR_DATA_DIR, OUTPUT_DIR, RENDER_BACKEND)

### Publish Command

```bash
# Install Smithery CLI (if not installed)
npm install -g @smithery/cli

# Publish from project root
cd /home/imgyu/workspace/02_active/dev/kimtech
npx @smithery/cli publish
```

### Verification

After publish, check: `https://smithery.ai/server/viznoir`

---

## 3. MCP.so (18,126+ servers)

- **URL**: https://mcp.so/submit (or https://mcp.so/server/submit)
- **Method**: Web form submission

### Form Fields

| Field | Value |
|-------|-------|
| Server Name | viznoir |
| Description | Headless CAE post-processing MCP server for AI coding assistants. Visualize CFD/FEA simulation results through 13 tools — render, slice, contour, clip, streamlines, animate, and more. |
| GitHub URL | https://github.com/kimimgo/viznoir |
| Website | https://kimimgo.github.io/viznoir |
| Install Command | pip install mcp-server-viznoir |
| Categories | Science, Engineering, Data Visualization |
| Tags | vtk, cfd, cae, simulation, visualization, post-processing |
| License | MIT |

---

## 4. Glama.ai (18,091+ servers)

- **URL**: https://glama.ai/mcp/servers/submit
- **Method**: Web form — submit GitHub URL, auto-parses metadata

### Form Fields

| Field | Value |
|-------|-------|
| GitHub Repository URL | https://github.com/kimimgo/viznoir |
| Name | viznoir |
| Short Description | Headless CAE post-processing MCP server for AI coding assistants |
| Long Description | Visualize CFD/FEA simulation results through 13 tools — render, slice, contour, clip, streamlines, animate, and more. VTK-based headless rendering with GPU (EGL) or CPU (OSMesa) support. 50+ mesh formats via meshio. No ParaView dependency required. |
| Categories | Science & Research, Engineering, Data Visualization |
| Install | pip install mcp-server-viznoir |
| Website | https://kimimgo.github.io/viznoir |

---

## 5. PulseMCP (8,600+ servers)

- **URL**: https://www.pulsemcp.com/submit
- **Method**: Web form submission

### Form Fields

| Field | Value |
|-------|-------|
| Server Name | viznoir |
| Description | Headless CAE post-processing MCP server for AI coding assistants. 13 tools for CFD/FEA visualization: render, slice, contour, clip, streamlines, animate. VTK-based, 50+ mesh formats, GPU/CPU headless rendering. |
| GitHub URL | https://github.com/kimimgo/viznoir |
| Homepage | https://kimimgo.github.io/viznoir |
| Install | pip install mcp-server-viznoir |
| Category | Science & Research |
| License | MIT |

---

## Submission Checklist

- [ ] PyPI v0.1.0 published (prerequisite for all)
- [ ] awesome-mcp-servers PR submitted
- [ ] Smithery.ai published via CLI
- [ ] MCP.so form submitted
- [ ] Glama.ai form submitted
- [ ] PulseMCP form submitted
- [ ] All 5 listings verified live

## MCP Config (for registry verification)

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir",
      "env": {
        "VIZNOIR_RENDER_BACKEND": "auto"
      }
    }
  }
}
```

## uvx Config (alternative)

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "uvx",
      "args": ["mcp-server-viznoir"],
      "env": {
        "VIZNOIR_RENDER_BACKEND": "auto"
      }
    }
  }
}
```
