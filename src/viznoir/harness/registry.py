"""Tool dispatch registry — shared between models.py and orchestrator.py.

Separated to eliminate circular imports:
  models.py → registry.py (validation)
  orchestrator.py → registry.py (population + execution)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

# Populated by orchestrator.py at import time.
TOOL_DISPATCH: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
