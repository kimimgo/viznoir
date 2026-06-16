"""autoexp — modify -> render -> measure -> keep/revert loop (Git Ratcheting pilot).

Greedy hill-climb over render parameters using ``engine.quality.measure_quality``
as the objective: try each candidate, render it, measure quality, and KEEP it
only if the score improves (the ratchet never moves backward), else REVERT. The
render step is injected (``render_fn``) so the loop is testable without a GPU;
``engine.presets.candidates_for`` supplies physics-appropriate candidates,
combining the quality metric (#60) with the guard's physics knowledge (#58).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from viznoir.engine.quality import QualityMetrics, measure_quality

RenderFn = Callable[[dict[str, Any]], np.ndarray]


@dataclass
class Trial:
    """One modify->render->measure step and whether the ratchet kept it."""

    params: dict[str, Any]
    score: float
    metrics: QualityMetrics
    kept: bool
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params,
            "score": self.score,
            "metrics": self.metrics.to_dict(),
            "kept": self.kept,
            "label": self.label,
        }


@dataclass
class AutoexpResult:
    """Outcome of an autoexp run: the best params found plus the full trial log."""

    best_params: dict[str, Any]
    best_score: float
    baseline_score: float
    improved: bool
    trials: list[Trial]

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "baseline_score": self.baseline_score,
            "improved": self.improved,
            "trials": [t.to_dict() for t in self.trials],
        }


def _label(cand: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in cand.items()) or "noop"


def autoexp(
    base_params: dict[str, Any],
    candidates: list[dict[str, Any]],
    render_fn: RenderFn,
    *,
    background_color: tuple[float, float, float] | None = None,
    min_delta: float = 0.0,
) -> AutoexpResult:
    """Greedily try ``candidates`` on top of ``base_params``, keeping improvements.

    Args:
        base_params: starting render parameters.
        candidates: parameter overrides to try (each applied on the current best).
        render_fn: maps a params dict to a rendered image (numpy array).
        background_color: passed to the quality metric for coverage detection.
        min_delta: a candidate must beat the current score by more than this to be
            kept (guards against churn on noise).

    Returns:
        AutoexpResult with the best params, baseline/best scores, and the trial log.
    """
    current = dict(base_params)
    current_metrics = measure_quality(render_fn(current), background_color=background_color)
    baseline = current_metrics.score
    trials = [Trial(dict(current), baseline, current_metrics, True, "baseline")]

    for cand in candidates:
        trial_params = {**current, **cand}
        metrics = measure_quality(render_fn(trial_params), background_color=background_color)
        keep = metrics.score > current_metrics.score + min_delta
        trials.append(Trial(trial_params, metrics.score, metrics, keep, _label(cand)))
        if keep:
            current, current_metrics = trial_params, metrics

    return AutoexpResult(
        best_params=current,
        best_score=current_metrics.score,
        baseline_score=baseline,
        improved=current_metrics.score > baseline + min_delta,
        trials=trials,
    )
