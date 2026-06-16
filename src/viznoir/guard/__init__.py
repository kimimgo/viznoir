"""viznoir physics guard — validate render choices against the physical field.

Anti-hallucination layer: an agent may pick a sequential colormap for signed
pressure, a range that hides the zero crossing, or an isovalue outside the data
range. The guard turns these into pass/warn/fail verdicts.
"""

from __future__ import annotations

from .rules import ALL_RULES, GuardContext, RuleResult, Status
from .validator import ValidationReport, validate

__all__ = [
    "ALL_RULES",
    "GuardContext",
    "RuleResult",
    "Status",
    "ValidationReport",
    "validate",
]
