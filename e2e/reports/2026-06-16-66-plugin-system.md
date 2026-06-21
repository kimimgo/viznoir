# E2E Evidence — #66 Plugin system (entry-point discovery)

- **Date**: 2026-06-16
- **Scenario**: `e2e/scenarios/plugin_system_e2e.py`

## What was delivered

`viznoir/plugins.py` — `load_plugins()` discovers setuptools entry points in
three groups and registers them into viznoir's registries; one broken plugin is
warned-and-skipped, never blocking the others or the server:

| group | registers into | via |
|-------|----------------|-----|
| `viznoir.filters` | `engine.filters._FILTER_REGISTRY` | new `register_filter()` |
| `viznoir.parsers` | context parser registry (before the Generic fallback) | new `register_plugin_parser()` |
| `viznoir.presets` | `presets.registry.CASE_PRESETS` | new `register_preset()` |

Wired into `server.main()` so plugins load at startup (failures logged, never fatal).

## End-to-end demonstration (real install, no mocks)

The scenario builds a throwaway package declaring real entry points,
`pip install`s it into the venv, then in a **fresh subprocess** runs the real
`importlib.metadata` discovery path:

```
LOADED ['demo_passthrough'] ['demo_case']
  [PASS] real entry-point plugin discovered + registered + callable
```

- the `viznoir.filters` entry point appears in `list_filters()` and is invocable
  via `apply_filter(data, "demo_passthrough")`
- the `viznoir.presets` entry point appears in `CASE_PRESETS`
- the package is uninstalled afterwards (no residue)

## Unit coverage

`tests/test_plugins.py` — 8 tests (fake entry points exercise registration +
graceful-failure isolation), `plugins.py` at **100%**. Existing parser/filter/
preset tests still pass (231 related). Suite: 1779 tests. ruff + mypy (90 files)
clean.
