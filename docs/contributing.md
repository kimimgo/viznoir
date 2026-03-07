# Contributing

Thank you for your interest in contributing to viznoir!

## Development Setup

```bash
git clone https://github.com/kimimgo/viznoir.git
cd viznoir
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
pytest --cov=viznoir --cov-report=term-missing -q

# Single test file
pytest tests/test_engine/test_filters.py -q

# Single test
pytest tests/test_engine/test_filters.py::test_slice_plane -q
```

## Code Quality

```bash
# Lint
ruff check src/ tests/

# Auto-fix
ruff check src/ tests/ --fix

# Type check
mypy src/viznoir/ --ignore-missing-imports
```

## Adding a New Filter

1. Add the VTK filter function to `src/viznoir/engine/filters.py`
2. Register it in `src/viznoir/core/registry.py` with PascalCase key
3. Add tests to `tests/test_engine/test_filters.py`

## Adding a New Reader

1. Add the file extension mapping to `src/viznoir/engine/readers.py`
2. Add tests to `tests/test_engine/test_readers.py`

## Project Structure

```
src/viznoir/
  server.py          # FastMCP instance + tool registrations
  tools/             # Tool implementations
  engine/            # VTK rendering engine
  core/              # Pipeline compiler, runner, registry
  pipeline/          # Pipeline models (Pydantic)
  presets/           # Case-type rendering presets
  resources/         # MCP resource catalog
  prompts/           # MCP prompt templates
tests/
  test_engine/       # VTK engine unit tests
  test_core/         # Compiler, runner, registry tests
  test_pipeline/     # Pipeline integration tests
  test_tools/        # MCP tool-level tests
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `test:` — tests only
- `docs:` — documentation
- `chore:` — maintenance
