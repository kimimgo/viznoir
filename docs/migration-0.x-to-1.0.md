# Migrating to viznoir 1.0

viznoir 1.0 is the first release with a **stability guarantee**. If you used a
0.x release, here's what to know.

## Install

```bash
pip install -U viznoir          # PyPI package name is `viznoir`
mcp-server-viznoir              # the MCP server entry point (unchanged)
```

The PyPI package and CLI have been `viznoir` / `mcp-server-viznoir` since 0.8.x
(the older `mcp-server-viznoir` PyPI name is retired). If your MCP client config
still references the old package, update it to `viznoir`.

## What's stable in 1.0

From 1.0, the **public API follows SemVer** (see
[api-stability.md](./api-stability.md)): the 24 MCP tools and their parameters,
`viznoir://` resources, `viznoir.pipeline.models`, the CLI, and `VIZNOIR_*`
environment variables. Additions come in minor releases; removals only after a
deprecation cycle in a major release.

## New since 0.10

- **Trust & Guard** (the 0.11 line, folded into 1.0):
  - `validate_render` tool — physics-checks a render spec (colormap/range/camera/
    isosurface) against the field and returns pass/warn/fail + fixes.
  - `viznoir.guard` — the physics rules behind it.
  - `engine.quality` — render quality metrics (contrast, edge entropy, coverage).
  - `core.autoexp` — modify→render→measure→keep/revert tuning.
- **Plugins** — register your own filters/parsers/presets via entry points
  (`viznoir.filters` / `viznoir.parsers` / `viznoir.presets`); no fork needed.
- **Remote render** — `python -m viznoir.remote` streams rendered frames over a
  WebSocket from a GPU host.

## Deprecations

- `analyze_data` is deprecated — use `inspect_physics`. It still works in 1.x and
  emits a `DeprecationWarning`; run your client with
  `-W error::DeprecationWarning` to find usages.

## Behaviour notes

- Rendering is headless (EGL on GPU, with an OSMesa fallback) — no ParaView and
  no display required.
- No public API was removed in 1.0; existing 0.10 tool calls keep working.
