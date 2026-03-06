# Contributing to parapilot

Thank you for your interest in contributing to parapilot! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10+
- VTK 9.4+ (installed automatically via pip)
- GPU with EGL support (optional, for headless rendering)

### Install

```bash
git clone https://github.com/kimimgo/parapilot.git
cd parapilot
pip install -e ".[dev]"
```

Optional dependencies:

```bash
pip install -e ".[mesh]"       # meshio + trimesh for format conversion
pip install -e ".[composite]"  # Pillow + matplotlib for split_animate
pip install -e ".[all]"        # everything
```

## Running Tests

```bash
# Full test suite (1048 tests)
pytest --cov=parapilot --cov-report=term-missing -q

# Single test file
pytest tests/test_engine/test_filters.py -q

# Single test function
pytest tests/test_engine/test_filters.py::test_slice_plane -q
```

Tests use `asyncio_mode = "auto"` — async tests are detected automatically.

## Linting and Type Checking

```bash
# Lint
ruff check src/ tests/

# Lint with auto-fix
ruff check src/ tests/ --fix

# Type check
mypy src/parapilot/ --ignore-missing-imports
```

Ruff config: `target-version = "py310"`, `line-length = 120`.

## Project Structure

```
src/parapilot/
├── server.py          # FastMCP instance + tool registration
├── config.py          # Environment-based configuration
├── tools/             # Tool implementations (render_impl, slice_impl, etc.)
├── pipeline/
│   └── models.py      # Pydantic models (SourceDef, FilterStep, RenderDef, OutputDef)
├── core/
│   ├── compiler.py    # PipelineDefinition → Python script string
│   ├── runner.py      # VTKRunner: execute scripts via subprocess/Docker
│   ├── registry.py    # PascalCase filter/format registries
│   └── output.py      # RunResult → PipelineResult
└── engine/
    ├── filters.py     # VTK filter functions (snake_case keys)
    ├── readers.py     # File format reader factory
    ├── renderer.py    # Off-screen rendering (EGL/OSMesa)
    ├── camera.py      # Camera presets and positioning
    └── colormaps.py   # Built-in colormap definitions
```

## Adding a New Filter

Filters live in two places (dual registry pattern):

### 1. Implement the filter function

Add a function to `src/parapilot/engine/filters.py`:

```python
def my_filter(dataset, param1: float = 1.0, param2: str = "default"):
    """Apply my custom filter to the dataset."""
    import vtkmodules.vtkFiltersCore as vtk_filters

    filt = vtk_filters.vtkMyFilter()
    filt.SetInputData(dataset)
    filt.SetParam1(param1)
    filt.Update()
    return filt.GetOutput()
```

### 2. Register in the filter registry

Add entry to `_FILTER_REGISTRY` dict in `src/parapilot/engine/filters.py`:

```python
_FILTER_REGISTRY = {
    # ... existing entries ...
    "my_filter": my_filter,
}
```

### 3. Add PascalCase schema to core registry

Add the filter schema in `src/parapilot/core/registry.py`:

```python
"MyFilter": {
    "params": {
        "param1": {"type": "float", "default": 1.0},
        "param2": {"type": "str", "default": "default"},
    }
}
```

The `get_filter()` function performs case-insensitive lookup to bridge PascalCase (pipeline DSL) with snake_case (engine implementation).

### 4. Write tests

Add tests in `tests/test_engine/test_filters.py`:

```python
def test_my_filter():
    from tests.fixtures.create_data import create_wavelet
    from parapilot.engine.filters import my_filter

    dataset = create_wavelet()
    result = my_filter(dataset, param1=2.0)
    assert result is not None
    assert result.GetNumberOfPoints() > 0
```

## Adding a New Reader

### 1. Add reader function

Add to `src/parapilot/engine/readers.py`:

```python
def _read_my_format(path: str):
    """Read .myext files."""
    import vtkmodules.vtkIOMyModule as vtk_io

    reader = vtk_io.vtkMyFormatReader()
    reader.SetFileName(path)
    reader.Update()
    return reader.GetOutput()
```

### 2. Register the extension

Add the file extension mapping in the reader factory within the same file.

### 3. Test with a fixture

Create a minimal test fixture if needed and add tests in `tests/test_engine/test_readers.py`.

## Pull Request Process

1. **Fork** the repository and create a feature branch from `main`
2. **Write tests** for any new functionality
3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```
4. **Run the full check suite** before submitting:
   ```bash
   ruff check src/ tests/
   mypy src/parapilot/ --ignore-missing-imports
   pytest --cov=parapilot --cov-report=term-missing -q
   ```
5. **Keep commits focused** — one logical change per commit, [Conventional Commits](https://www.conventionalcommits.org/) format
6. **Open a PR** against `main` with a clear description

### Quality Gates (automated on every PR)

Your PR must pass all 5 gates to be mergeable:

| Gate | Tool | Threshold |
|------|------|-----------|
| G1. Lint | ruff | 0 errors |
| G2. Type Safety | mypy (strict) | 0 errors |
| G3. Tests | pytest (Python 3.10-3.13) | All pass |
| G4. Coverage | pytest-cov + Codecov | >= 80% project, >= 70% new code |
| G5. Security | CodeQL + pip-audit | 0 critical/high |

### PR Size Guidelines

PRs are automatically labeled by size. Smaller PRs get reviewed faster:

| Label | Lines Changed | Review Time |
|-------|---------------|-------------|
| `size/XS` | < 10 | Minutes |
| `size/S` | < 50 | Same day |
| `size/M` | < 200 | 1-2 days |
| `size/L` | < 500 | 2-3 days |
| `size/XL` | 500+ | Consider splitting |

## Contributor Recognition

We use [All Contributors](https://allcontributors.org/) to recognize every contribution.

### Contribution Tiers

| Tier | Criteria | Recognition |
|------|----------|-------------|
| First-timer | 1st merged PR | Welcome message + All Contributors badge |
| Contributor | 3+ merged PRs | README Hall of Fame |
| Core Contributor | 10+ merged PRs | CODEOWNERS listing + review privileges |
| Maintainer | Sustained contributions | Write access + release authority |

### Types of Contributions

Not just code! We recognize:
- **Code** — features, bug fixes, performance improvements
- **Documentation** — guides, API docs, examples
- **Testing** — test cases, coverage improvements
- **Bug Reports** — well-documented issue reports
- **Ideas** — feature proposals via Discussions
- **Reviews** — PR reviews and feedback

To add a contributor: `@all-contributors please add @username for code, test`

## Code Style

- Formatter/linter: [ruff](https://docs.astral.sh/ruff/) (line length 120, target Python 3.10)
- Type checker: [mypy](https://mypy-lang.org/) (strict mode)
- Test framework: [pytest](https://docs.pytest.org/) with [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- Naming: snake_case for engine functions, PascalCase for registry/DSL keys

## Good First Issues

Look for issues labeled [`good first issue`](https://github.com/kimimgo/parapilot/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — these are curated for newcomers with clear scope and guidance.

## Reporting Issues

Use [GitHub Issues](https://github.com/kimimgo/parapilot/issues) to report bugs or request features. Please include:

- Steps to reproduce
- Expected vs actual behavior
- VTK version and Python version
- File format being processed (if applicable)
