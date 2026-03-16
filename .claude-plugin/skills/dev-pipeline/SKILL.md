---
name: dev-pipeline
description: >-
  viznoir development automation skill. Guides the TDD cycle for viznoir-specific
  concerns: dual filter registry, CI auto-skip rules, benchmark patterns,
  and PR quality gates. Triggers: viznoir development, new filter, new tool,
  TDD, benchmark, PR review, dual registry, CI skip
---

# viznoir Dev Pipeline

## Workflow
Issue → Explore → Plan → TDD (Red→Green→Refactor) → Benchmark → PR → Review

## viznoir-Specific Checklist

### New Filter
1. Register in `core/registry.py` (PascalCase key, VTK class + param schema)
2. Register in `engine/filters.py` (snake_case key, VTK filter function)
3. Add to `TOOL_DISPATCH` in `harness/orchestrator.py` if image-producing
4. Test in `tests/test_engine/test_filters.py`

### New Tool
1. Create `tools/{name}.py` with `{name}_impl()` function
2. Register `@mcp.tool()` in `server.py`
3. Test in `tests/test_tools/`
4. Add to `TOOL_DISPATCH` if image-producing

### VTK Rendering Test
- Name file `*_vtk.py` (auto-skipped in CI) OR
- Add to `conftest.py` skip list

### Benchmark
- Write `bench_*.py` following `bench_comparison.py` pattern
- Update `REPORT.md` with results

### PR Quality Gate
- Test count >= CI guard (currently 1430)
- Coverage >= 80%
- `ruff check src/ tests/` clean
- `mypy src/viznoir/` clean
