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


def get_default_registry() -> ContextParserRegistry:
    """Create registry with built-in parsers (OpenFOAM first, Generic as fallback)."""
    from viznoir.context.generic import GenericContextParser
    from viznoir.context.openfoam import OpenFOAMContextParser

    registry = ContextParserRegistry()
    # Specific parsers first — checked in order, first match wins
    registry.register(OpenFOAMContextParser())
    # Generic is fallback — always returns True for can_parse
    registry.register(GenericContextParser())
    return registry
