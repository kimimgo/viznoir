"""Tests for viznoir.plugins — entry-point plugin discovery.

Fake EntryPoint objects are injected via monkeypatch so the real registration
paths are exercised without installing an external package.
"""

from __future__ import annotations

import pytest

import viznoir.plugins as plugins
from viznoir.context.parser import get_default_registry
from viznoir.engine.filters import list_filters
from viznoir.presets.registry import CASE_PRESETS


class _FakeEP:
    def __init__(self, name, obj=None, error=None):
        self.name = name
        self._obj = obj
        self._error = error

    def load(self):
        if self._error is not None:
            raise self._error
        return self._obj


def _patch_eps(monkeypatch, mapping):
    """mapping: {group: [FakeEP, ...]}"""

    def fake_entry_points(group):
        return mapping.get(group, [])

    monkeypatch.setattr(plugins, "entry_points", fake_entry_points)


def _noop_filter(data, **kwargs):
    return data


class _FakeParser:
    def can_parse(self, path):
        return path.endswith(".fake")

    def parse_dataset(self, dataset):
        return None


@pytest.fixture
def clean_registries():
    yield
    # remove anything a test registered
    from viznoir.context import parser as parser_mod
    from viznoir.engine import filters as filters_mod

    filters_mod._FILTER_REGISTRY.pop("plugin_filter", None)
    CASE_PRESETS.pop("plugin_case", None)
    parser_mod._PLUGIN_PARSERS.clear()


class TestLoadPlugins:
    def test_registers_filter(self, monkeypatch, clean_registries):
        _patch_eps(monkeypatch, {"viznoir.filters": [_FakeEP("plugin_filter", _noop_filter)]})
        loaded = plugins.load_plugins()
        assert "plugin_filter" in loaded["viznoir.filters"]
        assert "plugin_filter" in list_filters()

    def test_registers_preset(self, monkeypatch, clean_registries):
        preset = {"description": "plugin", "fields": {}}
        _patch_eps(monkeypatch, {"viznoir.presets": [_FakeEP("plugin_case", preset)]})
        plugins.load_plugins()
        assert CASE_PRESETS["plugin_case"] == preset

    def test_registers_parser_instance_and_class(self, monkeypatch, clean_registries):
        _patch_eps(
            monkeypatch,
            {"viznoir.parsers": [_FakeEP("inst", _FakeParser()), _FakeEP("cls", _FakeParser)]},
        )
        plugins.load_plugins()
        reg = get_default_registry()
        assert reg.get_parser("x.fake") is not None  # plugin parser handles .fake

    def test_bad_plugin_warns_and_others_load(self, monkeypatch, clean_registries):
        _patch_eps(
            monkeypatch,
            {
                "viznoir.filters": [
                    _FakeEP("broken", error=RuntimeError("boom")),
                    _FakeEP("plugin_filter", _noop_filter),
                ]
            },
        )
        with pytest.warns(UserWarning, match="broken"):
            loaded = plugins.load_plugins()
        assert loaded["viznoir.filters"] == ["plugin_filter"]
        assert "plugin_filter" in list_filters()

    def test_no_plugins_is_empty(self, monkeypatch):
        _patch_eps(monkeypatch, {})
        loaded = plugins.load_plugins()
        assert loaded == {"viznoir.filters": [], "viznoir.parsers": [], "viznoir.presets": []}


class TestRegisterHelpers:
    def test_register_filter(self, clean_registries):
        from viznoir.engine.filters import register_filter

        register_filter("plugin_filter", _noop_filter)
        assert "plugin_filter" in list_filters()

    def test_register_preset(self, clean_registries):
        from viznoir.presets.registry import register_preset

        register_preset("plugin_case", {"description": "x"})
        assert "plugin_case" in CASE_PRESETS

    def test_register_plugin_parser_used_before_generic(self, clean_registries):
        from viznoir.context.parser import register_plugin_parser

        register_plugin_parser(_FakeParser())
        reg = get_default_registry()
        # plugin parser must win over the Generic fallback for its file type
        assert reg.get_parser("sim.fake").__class__.__name__ == "_FakeParser"
