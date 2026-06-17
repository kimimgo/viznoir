"""E2E evidence for #64 — the deprecation policy is enforced in code, end to end.

Shows that a @deprecated public callable (1) still works, (2) emits a
DeprecationWarning naming the version + replacement a user would act on, and
(3) can be made fail-fast with -W error::DeprecationWarning.

Run:  .venv/bin/python e2e/scenarios/api_stability_e2e.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

from viznoir._deprecation import deprecated


@deprecated(since="1.0.0", removed_in="2.0.0", alternative="render")
def legacy_render() -> str:
    return "rendered"


def main() -> int:
    doc = Path(__file__).resolve().parents[2] / "docs" / "api-stability.md"

    # 1) still works + emits a warning
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = legacy_render()
    warn = caught[0].message if caught else None
    print(f"result={result!r}")
    print(f"warning={str(warn)!r}")

    # 2) fail-fast mode turns it into an error
    failed_fast = False
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        try:
            legacy_render()
        except DeprecationWarning:
            failed_fast = True

    checks = {
        "deprecated callable still returns": result == "rendered",
        "emits DeprecationWarning": isinstance(warn, DeprecationWarning),
        "warning names since + removal": warn and "1.0.0" in str(warn) and "2.0.0" in str(warn),
        "warning names replacement": warn and "render" in str(warn),
        "carries __deprecated__ metadata": legacy_render.__deprecated__["removed_in"] == "2.0.0",
        "-W error makes it fail-fast": failed_fast,
        "api-stability.md exists": doc.is_file() and "Semantic Versioning" in doc.read_text(),
    }
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
