# E2E Evidence — #59 validate_render MCP tool

- **Date**: 2026-06-16
- **Scenario**: `e2e/scenarios/validate_render_e2e.py`
- **Driven over**: the real MCP protocol (FastMCP `Client` → in-process viznoir server)

## What was driven (agent-facing path)

1. Wrote a real `.vti` with a signed `pressure` field (range `[-90, 110]`).
2. Connected a FastMCP `Client` to the viznoir server and listed tools — confirmed
   `validate_render` is exposed (tool count 23→24).
3. Called `validate_render` with a **bad** config (sequential `viridis` on signed
   pressure + out-of-range isovalue) and a **good** config (`coolwarm`,
   zero-centered range, in-range isovalue).

## Results

```
field range: [-90.0, 110.0]
BAD  verdict=fail :: FAIL: pressure_diverging_colormap (warn); empty_isosurface (fail)
GOOD verdict=pass :: PASS: render choices are physically consistent
```

## Checks (6/6 PASS)

```
[PASS] validate_render exposed over MCP
[PASS] bad config -> FAIL
[PASS] bad flags pressure colormap (sequential on signed field)
[PASS] bad flags empty isosurface (out-of-range isovalue)
[PASS] good config -> PASS
[PASS] real field range reported
```

The guard (#58) is now reachable by agents as an MCP tool, validating render
choices against the dataset's actual physics before they mislead.

## Unit coverage

`tests/test_tools/test_validate_render.py` — 11 tests, `validate_render.py` at
**100%** line coverage. Tool-count tests updated (compliance 18→19, registration
inventory). Suite: 1744 tests (≥1650 guard). ruff + mypy (86 files) clean.
