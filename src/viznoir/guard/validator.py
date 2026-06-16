"""Validator — run the physics rules over a GuardContext and aggregate a verdict."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .rules import ALL_RULES, GuardContext, RuleResult, Status

Rule = Callable[[GuardContext], RuleResult | None]

# Severity ordering for picking the worst verdict (FAIL > WARN > PASS).
_ORDER = {Status.PASS: 0, Status.WARN: 1, Status.FAIL: 2}


@dataclass
class ValidationReport:
    """All triggered rule results plus the worst-case verdict."""

    results: list[RuleResult]
    verdict: Status

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict.value,
            "results": [r.to_dict() for r in self.results],
        }


def validate(ctx: GuardContext, rules: list[Rule] | None = None) -> ValidationReport:
    """Run ``rules`` (default :data:`ALL_RULES`) and return an aggregated report.

    The verdict is the most severe status among applicable rules (FAIL > WARN >
    PASS); a context that no rule applies to passes vacuously.
    """
    active = ALL_RULES if rules is None else rules
    results = [res for res in (rule(ctx) for rule in active) if res is not None]
    verdict = max((r.status for r in results), key=lambda s: _ORDER[s], default=Status.PASS)
    return ValidationReport(results=results, verdict=verdict)
