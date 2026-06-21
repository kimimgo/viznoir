"""Tests for viznoir._deprecation — enforces the v1.0 deprecation policy."""

from __future__ import annotations

import warnings

import pytest

from viznoir._deprecation import deprecated, warn_deprecated


class TestDeprecatedDecorator:
    def test_emits_deprecation_warning(self):
        @deprecated(since="1.0.0", removed_in="2.0.0")
        def old():
            return 42

        with pytest.warns(DeprecationWarning) as record:
            assert old() == 42
        assert len(record) == 1
        msg = str(record[0].message)
        assert "1.0.0" in msg and "2.0.0" in msg

    def test_includes_alternative(self):
        @deprecated(since="1.0.0", removed_in="2.0.0", alternative="new_func")
        def old():
            return None

        with pytest.warns(DeprecationWarning, match="new_func"):
            old()

    def test_preserves_metadata(self):
        @deprecated(since="1.0.0", removed_in="2.0.0")
        def documented():
            """Original docstring."""
            return 1

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Original docstring."

    def test_attaches_deprecation_info(self):
        @deprecated(since="1.0.0", removed_in="2.0.0", alternative="x")
        def f():
            return 0

        assert f.__deprecated__ == {
            "since": "1.0.0",
            "removed_in": "2.0.0",
            "alternative": "x",
        }

    def test_return_value_passthrough(self):
        @deprecated(since="1.0.0", removed_in="2.0.0")
        def add(a, b):
            return a + b

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert add(2, 3) == 5


class TestWarnDeprecated:
    def test_emits_for_named_thing(self):
        with pytest.warns(DeprecationWarning, match="old_param"):
            warn_deprecated("old_param", since="1.0.0", removed_in="2.0.0")

    def test_message_mentions_versions_and_alternative(self):
        with pytest.warns(DeprecationWarning) as record:
            warn_deprecated("p", since="1.0.0", removed_in="2.0.0", alternative="q")
        msg = str(record[0].message)
        assert "1.0.0" in msg and "2.0.0" in msg and "q" in msg
