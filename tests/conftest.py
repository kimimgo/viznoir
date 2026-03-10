"""Shared test fixtures and CI rendering skip logic."""

from __future__ import annotations

import os

import pytest

from viznoir.config import PVConfig
from viznoir.core.compiler import ScriptCompiler

# ---------------------------------------------------------------------------
# VTK rendering availability detection
# ---------------------------------------------------------------------------

_IS_CI = bool(os.environ.get("CI"))

# Test files/classes that require VTK GPU rendering (segfault in CI).
# All *_vtk.py files are also auto-skipped via endswith("_vtk.py") pattern below.
_RENDERING_TEST_FILES = {
    "test_e2e_production.py",
    "test_renderer_cine.py",
}

_RENDERING_TEST_CLASSES = {
    "TestVTKRendererAndRenderToPng",  # test_renderer_helpers.py
    "TestComposeSideBySide",  # test_compare.py
    "TestCompareImpl",  # test_compare.py
    "TestExportGltf",  # test_export.py (export_gltf needs render window)
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip VTK rendering tests in CI (no GPU/EGL/OSMesa)."""
    if not _IS_CI:
        return

    skip_render = pytest.mark.skip(reason="VTK rendering requires GPU (not available in CI)")

    for item in items:
        # Skip entire files (explicit list + *_vtk.py pattern)
        filename = item.path.name if hasattr(item, "path") else ""
        if filename in _RENDERING_TEST_FILES or filename.endswith("_vtk.py"):
            item.add_marker(skip_render)
            continue

        # Skip specific test classes
        cls = item.cls
        if cls is not None and cls.__name__ in _RENDERING_TEST_CLASSES:
            item.add_marker(skip_render)
            continue


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def compiler() -> ScriptCompiler:
    return ScriptCompiler()


@pytest.fixture
def config() -> PVConfig:
    return PVConfig(data_dir="/data", output_dir="/output")
