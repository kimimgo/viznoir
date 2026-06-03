# Installation

## pip (recommended)

```bash
pip install viznoir
```

### Optional dependencies

```bash
# Mesh format conversion (meshio + trimesh)
pip install "viznoir[mesh]"

# Split-pane animations (Pillow + matplotlib)
pip install "viznoir[composite]"

# Everything
pip install "viznoir[all]"
```

## Claude Code Plugin

```bash
claude install kimimgo/viznoir
```

## From source

```bash
git clone https://github.com/kimimgo/viznoir.git
cd viznoir
pip install -e ".[dev]"
```

## Requirements

- Python 3.10+
- VTK (installed automatically via pip)
- For GPU rendering: NVIDIA GPU + driver
- For CPU rendering: OSMesa (included in VTK wheels)
