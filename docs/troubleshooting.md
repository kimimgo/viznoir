# Troubleshooting

Common issues and solutions when using viznoir.

## Rendering Backend Issues

### EGL not available

**Symptom**: `RuntimeError: Failed to initialize render window` or blank images.

**Cause**: NVIDIA EGL libraries not found or VTK not configured for offscreen rendering.

**Solution**:
```bash
# Set the environment variable before starting
export VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow

# Verify NVIDIA EGL is installed
ls /usr/lib/x86_64-linux-gnu/libEGL_nvidia.so*
```

### OSMesa fallback (CPU rendering)

**Symptom**: Slow rendering or `VTK_DEFAULT_OPENGL_WINDOW` not recognized.

**Cause**: No GPU available (CI, remote servers without NVIDIA drivers).

**Solution**: Use the CPU Docker image or set OSMesa backend:
```bash
export VTK_DEFAULT_OPENGL_WINDOW=vtkOSOpenGLRenderWindow
# Or use the CPU Docker image
docker run --rm -v /data:/data ghcr.io/kimimgo/viznoir:cpu
```

### SIGSEGV on render

**Symptom**: Segmentation fault during rendering.

**Cause**: Using `vtkEGLRenderWindow()` directly instead of the generic `vtkRenderWindow()`.

**Solution**: Always use `vtkRenderWindow()` — VTK auto-selects the backend via the environment variable.

---

## File Format Issues

### File not found

**Symptom**: `FileNotFoundError: File not found: '/data/case.foam'`

**Cause**: File doesn't exist at the specified path, or `VIZNOIR_DATA_DIR` restricts access.

**Solution**:
```bash
# Check if the file exists
ls -la /data/case.foam

# If using Docker, ensure the volume is mounted
docker run -v /path/to/cases:/data ...

# Check VIZNOIR_DATA_DIR setting
echo $VIZNOIR_DATA_DIR
```

### Unknown file format

**Symptom**: `ValueError: Unsupported file extension: '.xyz'`

**Cause**: The file format is not in the built-in reader registry.

**Solution**: Check supported formats via the MCP resource:
```
viznoir://formats
```
Supported: `.vtk`, `.vtu`, `.vtp`, `.vts`, `.vti`, `.vtr`, `.vtm`, `.pvd`, `.foam`, `.stl`, `.ply`, `.obj`, `.csv`, `.cgns`, `.exo`, `.e`, `.case`, `.dat`, `.xdmf`, `.xmf`

### Empty dataset after reading

**Symptom**: `ValueError: Dataset has 0 points` or blank renders.

**Cause**: Wrong timestep, missing field arrays, or multiblock with empty blocks.

**Solution**:
1. Use `inspect_data` to check available fields and timesteps
2. Try `timestep: "latest"` or `timestep: 0`
3. For multiblock data, specify `blocks` to select non-empty blocks

---

## Docker Issues

### GPU not detected in Docker

**Symptom**: `Failed to initialize EGL` inside Docker container.

**Cause**: NVIDIA Container Toolkit not installed or `--gpus` flag missing.

**Solution**:
```bash
# Install NVIDIA Container Toolkit
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker

# Run with GPU access
docker run --gpus all -v /data:/data ghcr.io/kimimgo/viznoir
```

### Permission denied on output

**Symptom**: `PermissionError: [Errno 13] Permission denied: '/output/render.png'`

**Cause**: Output directory not writable or volume mount permissions.

**Solution**:
```bash
# Create output directory with correct permissions
mkdir -p /tmp/viznoir-output
docker run --gpus all \
  -v /data:/data \
  -v /tmp/viznoir-output:/output \
  ghcr.io/kimimgo/viznoir
```

### Large output files filling disk

**Symptom**: Disk full errors or slow performance.

**Cause**: Animations and batch renders create many temporary files.

**Solution**: Set `VIZNOIR_OUTPUT_DIR` to a location with sufficient space:
```bash
export VIZNOIR_OUTPUT_DIR=/mnt/large-disk/viznoir-output
```

---

## MCP Connection Issues

### Claude Code plugin not connecting

**Symptom**: Tools not appearing in Claude Code.

**Cause**: Server not configured or not installed.

**Solution**:
```bash
# Install the package
pip install mcp-server-viznoir

# Verify the entry point works
mcp-server-viznoir --version

# Add to Claude Code settings (stdio transport)
# In .mcp.json:
{
  "mcpServers": {
    "viznoir": {
      "command": "mcp-server-viznoir",
      "env": {
        "VIZNOIR_DATA_DIR": "/path/to/data"
      }
    }
  }
}
```

### SSE/HTTP transport

**Symptom**: Need to connect from a remote client or web application.

**Cause**: Default stdio transport only works for local connections.

**Solution**:
```bash
# SSE transport (Server-Sent Events)
mcp-server-viznoir --transport sse --port 8000

# Streamable HTTP transport
mcp-server-viznoir --transport streamable-http --port 8000
```

### Timeout on large files

**Symptom**: `TimeoutError` when processing large simulation files.

**Cause**: Default timeout is 600 seconds.

**Solution**:
```bash
export VIZNOIR_TIMEOUT=1800  # 30 minutes
```

---

## Getting Help

If your issue isn't listed here:

1. Check the [GitHub Issues](https://github.com/kimimgo/viznoir/issues) for similar reports
2. Open a new issue with:
   - viznoir version (`mcp-server-viznoir --version`)
   - Python version (`python --version`)
   - VTK version (`python -c "import vtk; print(vtk.vtkVersion.GetVTKVersion())"`)
   - Full error traceback
   - Minimal reproduction steps
