"""E2E evidence for #66 — discover a REAL installed plugin via entry points.

Builds a throwaway plugin package that declares viznoir.filters / viznoir.presets
entry points, pip-installs it into the venv, then (in a fresh subprocess so the
entry points are visible) runs load_plugins() through the *real*
importlib.metadata path — no monkeypatching — and verifies the filter and preset
are registered and usable. Uninstalls the package afterwards.

Run:  .venv/bin/python e2e/scenarios/plugin_system_e2e.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable  # the venv python running this script
PKG = "viznoir-e2e-demo-plugin"

PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "viznoir-e2e-demo-plugin"
version = "0.0.0"

[project.entry-points."viznoir.filters"]
demo_passthrough = "viznoir_e2e_demo_plugin:passthrough"

[project.entry-points."viznoir.presets"]
demo_case = "viznoir_e2e_demo_plugin:DEMO_PRESET"

[tool.hatch.build.targets.wheel]
packages = ["viznoir_e2e_demo_plugin"]
"""

MODULE = '''\
"""Throwaway viznoir plugin for E2E."""

def passthrough(data, **kwargs):
    """A trivial filter: return the dataset unchanged."""
    return data

DEMO_PRESET = {"description": "e2e demo preset", "fields": {}}
'''

# Runs inside the subprocess (after install) — exercises the real discovery path.
VERIFY = """
import sys
from viznoir.plugins import load_plugins
from viznoir.engine.filters import list_filters, apply_filter
from viznoir.presets.registry import CASE_PRESETS

loaded = load_plugins()
ok = True
ok &= "demo_passthrough" in loaded["viznoir.filters"]
ok &= "demo_passthrough" in list_filters()
ok &= "demo_case" in loaded["viznoir.presets"]
ok &= CASE_PRESETS.get("demo_case", {}).get("description") == "e2e demo preset"
# the registered filter is actually callable through apply_filter
sentinel = object()
ok &= apply_filter(sentinel, "demo_passthrough") is sentinel
print("LOADED", loaded["viznoir.filters"], loaded["viznoir.presets"])
sys.exit(0 if ok else 1)
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "viznoir_e2e_demo_plugin").mkdir()
        (root / "viznoir_e2e_demo_plugin" / "__init__.py").write_text(MODULE)
        (root / "pyproject.toml").write_text(PYPROJECT)

        install = subprocess.run(
            ["uv", "pip", "install", "--python", PY, "--no-deps", str(root)],
            capture_output=True, text=True,
        )
        if install.returncode != 0:
            print("install failed:", install.stderr[-400:])
            return 1
        try:
            verify = subprocess.run([PY, "-c", VERIFY], capture_output=True, text=True)
            print(verify.stdout.strip() or verify.stderr.strip()[-400:])
            passed = verify.returncode == 0
        finally:
            subprocess.run(
                ["uv", "pip", "uninstall", "--python", PY, PKG],
                capture_output=True, text=True,
            )

    print(f"  [{'PASS' if passed else 'FAIL'}] real entry-point plugin discovered + registered + callable")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
