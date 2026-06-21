"""ContextParser protocol and registry for solver-specific parsers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from viznoir.context.models import CaseContext


@runtime_checkable
class ContextParser(Protocol):
    """Protocol for solver-specific context parsers."""

    def can_parse(self, path: str) -> bool:
        """Return True if this parser can handle the given file/directory."""
        ...

    def parse_dataset(self, dataset: object) -> CaseContext:
        """Extract CaseContext from a VTK dataset."""
        ...


class ContextParserRegistry:
    """Registry of context parsers, checked in order."""

    def __init__(self) -> None:
        self._parsers: list[ContextParser] = []

    def register(self, parser: ContextParser) -> None:
        self._parsers.append(parser)

    def get_parser(self, path: str) -> ContextParser | None:
        for parser in self._parsers:
            if parser.can_parse(path):
                return parser
        return None


# Parsers registered by plugins (viznoir.parsers entry points). Checked after the
# built-in specific parsers but before the Generic catch-all fallback.
_PLUGIN_PARSERS: list[ContextParser] = []


def register_plugin_parser(parser: ContextParser) -> None:
    """Register a context parser contributed by a plugin (see viznoir.plugins)."""
    _PLUGIN_PARSERS.append(parser)


def get_default_registry() -> ContextParserRegistry:
    """Create registry with built-in parsers (OpenFOAM first, Generic as fallback)."""
    from viznoir.context.cgns import CGNSContextParser
    from viznoir.context.dualsphysics import DualSPHysicsContextParser
    from viznoir.context.generic import GenericContextParser
    from viznoir.context.openfoam import OpenFOAMContextParser

    registry = ContextParserRegistry()
    # Specific parsers first — checked in order, first match wins
    registry.register(OpenFOAMContextParser())
    registry.register(CGNSContextParser())
    registry.register(DualSPHysicsContextParser())
    # Plugin parsers — after built-ins, before the Generic catch-all
    for parser in _PLUGIN_PARSERS:
        registry.register(parser)
    # Generic is fallback — always returns True for can_parse
    registry.register(GenericContextParser())
    return registry
