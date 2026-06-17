"""Deprecation utilities backing the v1.0 SemVer + deprecation policy.

Public API marked with :func:`deprecated` (or signalled via
:func:`warn_deprecated`) emits a ``DeprecationWarning`` naming the version it was
deprecated in, when it will be removed, and the replacement — so the deprecation
cycle documented in ``docs/api-stability.md`` is enforced in code, not just prose.
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def _message(name: str, since: str, removed_in: str, alternative: str | None) -> str:
    msg = f"{name} is deprecated since viznoir {since} and will be removed in {removed_in}."
    if alternative:
        msg += f" Use {alternative} instead."
    return msg


def deprecated(since: str, removed_in: str, alternative: str | None = None) -> Callable[[F], F]:
    """Mark a public callable as deprecated.

    Calling the decorated function emits a ``DeprecationWarning`` and attaches a
    ``__deprecated__`` metadata dict; the original behaviour is otherwise
    unchanged.

    Args:
        since: version the deprecation started (e.g. ``"1.0.0"``).
        removed_in: version it will be removed in (e.g. ``"2.0.0"``).
        alternative: the replacement to point users to.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(
                _message(func.__qualname__, since, removed_in, alternative),
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        wrapper.__deprecated__ = {  # type: ignore[attr-defined]
            "since": since,
            "removed_in": removed_in,
            "alternative": alternative,
        }
        return wrapper  # type: ignore[return-value]

    return decorator


def warn_deprecated(
    name: str,
    since: str,
    removed_in: str,
    alternative: str | None = None,
    stacklevel: int = 2,
) -> None:
    """Emit a deprecation warning for a parameter or behaviour (not a whole callable)."""
    warnings.warn(_message(name, since, removed_in, alternative), DeprecationWarning, stacklevel=stacklevel)
