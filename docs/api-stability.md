# API Stability & Deprecation Policy

From **v1.0.0**, viznoir follows [Semantic Versioning](https://semver.org/) for
its **public API**. This document defines what "public" means, what stability we
guarantee, and how things are deprecated and removed.

## What is the public API

The public, SemVer-covered surface is:

| Surface | Contract |
|---------|----------|
| **MCP tools** | The 24 registered tools, their names, and their parameter names/types/defaults (see `docs/tools/`). |
| **MCP resources** | `viznoir://` resource URIs and their schemas. |
| **MCP prompts** | Registered prompt names and arguments. |
| **Pipeline models** | `viznoir.pipeline.models` (`SourceDef`, `FilterStep`, `RenderDef`, `OutputDef`, `PipelineDefinition`) field names and types. |
| **CLI** | The `mcp-server-viznoir` entry point and its behaviour. |
| **Environment variables** | The documented `VIZNOIR_*` variables (see `CLAUDE.md` / README). |

**Not public** (may change in any release): anything prefixed with `_`, the
`viznoir.engine.*` internals, test fixtures, and benchmark scripts. Build on the
MCP tools and pipeline models, not the engine internals.

## SemVer guarantee

- **PATCH** (`1.0.x`): bug fixes only. No public API changes.
- **MINOR** (`1.x.0`): backward-compatible additions — new tools, new optional
  parameters (with defaults), new resources. Existing calls keep working.
- **MAJOR** (`x.0.0`): may remove or change public API, but only items that have
  been through a full deprecation cycle (below).

A call that works on `1.a.b` works on any `1.c.d` with `c.d >= a.b`.

## Deprecation cycle

Deprecations are **enforced in code**, not just documented, via
`viznoir._deprecation`:

```python
from viznoir._deprecation import deprecated, warn_deprecated

@deprecated(since="1.2.0", removed_in="2.0.0", alternative="new_tool")
def old_tool(...): ...

# for a single parameter or behaviour:
warn_deprecated("legacy_param", since="1.2.0", removed_in="2.0.0", alternative="modern_param")
```

Lifecycle:

1. **Deprecate** in a MINOR release — the item still works but emits a
   `DeprecationWarning` naming the version, the removal target, and the
   replacement.
2. **Warn** for at least one full MINOR series so users have time to migrate.
3. **Remove** only in the next MAJOR release.

Run your client with `-W error::DeprecationWarning` to fail fast on anything
deprecated.

## Breaking-change checklist (maintainers)

Before merging a change that touches the public surface:

- [ ] Is it additive (new tool / optional param)? → MINOR, fine.
- [ ] Does it change/remove existing public behaviour? → it must first ship as a
      `@deprecated` / `warn_deprecated` shim in a MINOR, and only be removed in a
      MAJOR.
- [ ] Tool inventory/count tests (`tests/test_tools/test_server_registration.py`,
      `test_mcp_compliance.py`) updated and still pinning the surface?
- [ ] `CHANGELOG.md` entry (release-please) reflects the SemVer impact.
