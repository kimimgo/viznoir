# ──────────────────────────────────────────────────────────────
# viznoir: ParaView MCP Server (GPU EGL headless rendering)
# ──────────────────────────────────────────────────────────────
FROM ubuntu:22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive

# System deps + EGL/GL for GPU headless rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
        libgomp1 libtbb12 libsqlite3-0 \
        libgl1 libegl1 libgles2 libopengl0 \
    && rm -rf /var/lib/apt/lists/*

# ── ParaView 5.13.3 EGL binary (GPU headless — no X11 needed) ──
ARG PV_VERSION=5.13.3
ARG PV_TARBALL=ParaView-${PV_VERSION}-egl-MPI-Linux-Python3.10-x86_64.tar.gz
ARG PV_URL=https://www.paraview.org/files/v5.13/${PV_TARBALL}

RUN curl -fSL ${PV_URL} -o /tmp/pv.tar.gz \
    && tar -xzf /tmp/pv.tar.gz -C /opt \
    && rm /tmp/pv.tar.gz \
    && ln -s /opt/ParaView-${PV_VERSION}-egl-MPI-Linux-Python3.10-x86_64 /opt/paraview

ENV PATH="/opt/paraview/bin:${PATH}"

# ── NVIDIA runtime (container toolkit provides driver libs) ──
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics

# ── uv + Python venv ──
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Install viznoir into a venv (separate from ParaView's Python)
COPY pyproject.toml .
COPY src/ ./src/
RUN uv venv /opt/venv --python 3.10 \
    && . /opt/venv/bin/activate \
    && uv pip install .

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# ── Runtime directories ──
RUN mkdir -p /data /output
ENV VIZNOIR_DATA_DIR=/data
ENV VIZNOIR_OUTPUT_DIR=/output
ENV VIZNOIR_RENDER_BACKEND=gpu

ENTRYPOINT []
CMD ["mcp-server-viznoir"]
