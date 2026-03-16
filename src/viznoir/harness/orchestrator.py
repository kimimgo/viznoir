"""Orchestrator — auto_postprocess meta-tool and tool dispatch."""
from __future__ import annotations

from typing import Any, Callable, Coroutine

# Placeholder: populated in Task 3 with actual impl functions.
TOOL_DISPATCH: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
