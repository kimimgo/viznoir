"""Shared test fixtures."""

from __future__ import annotations

import pytest

from parapilot.config import PVConfig
from parapilot.core.compiler import ScriptCompiler


@pytest.fixture
def compiler() -> ScriptCompiler:
    return ScriptCompiler()


@pytest.fixture
def config() -> PVConfig:
    return PVConfig(data_dir="/data", output_dir="/output")
