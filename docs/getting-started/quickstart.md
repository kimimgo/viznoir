# Quick Start

## MCP Client Configuration

Add viznoir to your MCP client's configuration:

```json
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir"
    }
  }
}
```

## Basic Workflow

### 1. Inspect your data

```
> "Inspect the cavity.foam file and tell me what fields are available"
```

The `inspect_data` tool returns bounds, point/cell arrays with ranges, timestep info, and multiblock structure.

### 2. Render a field

```
> "Render the pressure field from cavity.foam with a Viridis colormap"
```

### 3. Create a slice

```
> "Create a horizontal slice through the cavity at z=0.05 showing velocity"
```

### 4. Extract statistics

```
> "What are the min/max/mean pressure values?"
```

### 5. Create an animation

```
> "Animate the pressure field over all timesteps as a GIF"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VIZNOIR_DATA_DIR` | None | Restrict file access to this directory |
| `VIZNOIR_OUTPUT_DIR` | `/output` | Output directory for rendered files |
| `VIZNOIR_RENDER_BACKEND` | `gpu` | `gpu`, `cpu`, or `auto` |
| `VIZNOIR_VTK_BACKEND` | `auto` | `egl`, `osmesa`, or `auto` |
| `VIZNOIR_TIMEOUT` | `600` | Script execution timeout (seconds) |

## Transport Modes

```bash
# Default: stdio (local MCP clients)
mcp-server-viznoir

# SSE (remote access)
mcp-server-viznoir --transport sse --port 8000

# StreamableHTTP (FastMCP 2.0+)
mcp-server-viznoir --transport streamable-http --port 8000
```
