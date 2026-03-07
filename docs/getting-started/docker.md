# Docker

## GPU Rendering (EGL)

```bash
docker compose up viznoir -d
```

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/).

## CPU Rendering (OSMesa)

```bash
docker compose up viznoir-cpu -d
```

No GPU required — uses OSMesa software rendering. Works on any machine.

## Custom Data Directory

```bash
VIZNOIR_DATA_DIR=/path/to/simulations docker compose up -d
```

## HTTP Transport

Edit `docker-compose.yml` to uncomment the HTTP transport section:

```yaml
services:
  viznoir:
    ports:
      - "8000:8000"
    command: ["mcp-server-viznoir", "--transport", "streamable-http", "--port", "8000"]
```

## Building

```bash
# GPU image
docker compose build viznoir

# CPU image
docker compose build viznoir-cpu
```
