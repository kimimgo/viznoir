"""Agent Harness — autonomous post-processing orchestration layer."""

from __future__ import annotations

__all__ = ["HAS_HARNESS"]


def _check_harness_support() -> bool:
    """Check if FastMCP >= 3.0.0 is available (required for ctx.sample)."""
    try:
        from importlib.metadata import version as get_version

        from packaging.version import Version

        return Version(get_version("fastmcp")) >= Version("3.0.0")
    except Exception:
        return False


HAS_HARNESS = _check_harness_support()
