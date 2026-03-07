# Reddit r/OpenFOAM Post

## Title

GUI-free post-processing: an MCP server that lets AI assistants render OpenFOAM results from the terminal

## Flair

Postprocessing

## Body

If you've ever SSH'd into a cluster, finished a run, and wished you could check results without downloading files and opening ParaView — this might interest you.

### What is it?

**viznoir** is a headless MCP server that reads `.foam` files and VTK outputs directly. AI coding assistants (Claude Code, Cursor, etc.) call its tools to render fields, cut slices, extract contours, and generate animations — all from the terminal.

### Typical workflow

You're in your terminal. Your simulation just finished.

```
> "Open ./motorBike/motorBike.foam, render the pressure field,
   then slice at y=0 to show the wake"
```

The AI loads the case, calls the render and slice tools, and returns PNG images inline. No X forwarding, no VNC, no file transfer.

### What it supports

- `.foam` file loading (reconstructed and decomposed cases)
- VTK/VTM/VTP outputs from OpenFOAM's function objects
- Field rendering with 18 colormaps (plasma, turbo, coolwarm, jet...)
- Slice, clip, contour, streamlines, surface integration
- Time-series animation (GIF/MP4)
- `inspect_data` to check available fields, mesh stats, time steps

### How it works

It's **not** a ParaView wrapper. It uses VTK's Python API directly with GPU EGL rendering — runs headless on any Linux server with an NVIDIA GPU. Also works CPU-only (OSMesa fallback).

### Setup

```bash
pip install mcp-server-viznoir
```

Add to your AI assistant's MCP config:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

That's it. Ask your AI to render your OpenFOAM results.

### Limitations (being honest)

- Validated on standard tutorials and VTK example data, not 50M-cell industrial cases yet
- No in-situ / co-processing (post-processing only)
- Single-node rendering (no parallel compositing)

If anyone runs it on a real industrial case, I'd love to hear how it goes.

- GitHub: https://github.com/kimimgo/viznoir
- Landing page: https://kimimgo.github.io/viznoir
- MIT license, 331 tests

## Posting Notes

- Flair: Postprocessing (or Tools if unavailable)
- Best time: Tue-Thu, 10:00 AM EST
- Tone: practical, understated — r/OpenFOAM values utility over hype
