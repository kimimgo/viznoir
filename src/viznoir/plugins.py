"""Plugin discovery — load user filters, parsers, and presets from entry points.

Users extend viznoir without forking by declaring setuptools entry points:

    [project.entry-points."viznoir.filters"]
    my_filter = "my_pkg:my_filter_func"      # callable(data, **kwargs) -> dataset

    [project.entry-points."viznoir.parsers"]
    my_parser = "my_pkg:MyParser"            # ContextParser instance or class

    [project.entry-points."viznoir.presets"]
    my_case = "my_pkg:MY_PRESET"             # case-preset dict

:func:`load_plugins` discovers and registers them into viznoir's registries. A
single broken plugin is logged and skipped — it never blocks the others or the
server.
"""

from __future__ import annotations

import warnings
from importlib.metadata import entry_points

# Entry-point groups viznoir looks up.
FILTER_GROUP = "viznoir.filters"
PARSER_GROUP = "viznoir.parsers"
PRESET_GROUP = "viznoir.presets"


def _register_filter(name: str, obj: object) -> None:
    from viznoir.engine.filters import register_filter

    register_filter(name, obj)


def _register_parser(name: str, obj: object) -> None:
    from viznoir.context.parser import register_plugin_parser

    parser = obj() if isinstance(obj, type) else obj
    register_plugin_parser(parser)  # type: ignore[arg-type]  # runtime-checked Protocol


def _register_preset(name: str, obj: object) -> None:
    from viznoir.presets.registry import register_preset

    register_preset(name, obj)  # type: ignore[arg-type]


_GROUPS = {
    FILTER_GROUP: _register_filter,
    PARSER_GROUP: _register_parser,
    PRESET_GROUP: _register_preset,
}


def load_plugins() -> dict[str, list[str]]:
    """Discover and register all viznoir plugins from entry points.

    Returns a ``{group: [registered names]}`` map. Plugins that fail to load or
    register emit a ``UserWarning`` and are skipped.
    """
    loaded: dict[str, list[str]] = {group: [] for group in _GROUPS}
    for group, register in _GROUPS.items():
        for ep in entry_points(group=group):
            try:
                register(ep.name, ep.load())
            except Exception as exc:  # noqa: BLE001 — one bad plugin must not break others
                warnings.warn(
                    f"viznoir: failed to load plugin '{ep.name}' from '{group}': {exc}",
                    stacklevel=2,
                )
                continue
            loaded[group].append(ep.name)
    return loaded
