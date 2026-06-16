"""Tests for core/autoexp.py — the modify->render->measure->keep/revert ratchet.

A fake render_fn maps params to synthetic images of known quality, so the loop
logic is exercised without a GPU.
"""

from __future__ import annotations

import numpy as np

from viznoir.core.autoexp import AutoexpResult, Trial, autoexp


def _flat() -> np.ndarray:
    return np.full((32, 32, 3), 128, dtype=np.uint8)


def _rich(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, size=(32, 32, 3), dtype=np.uint8)


def _render(params: dict) -> np.ndarray:
    """colormap 'rich' -> high-quality image, anything else -> flat (score ~0)."""
    return _rich() if params.get("colormap") == "rich" else _flat()


class TestAutoexp:
    def test_keeps_improvement(self):
        result = autoexp({"colormap": "flat"}, [{"colormap": "rich"}], _render)
        assert isinstance(result, AutoexpResult)
        assert result.improved is True
        assert result.best_params["colormap"] == "rich"
        assert result.best_score > result.baseline_score

    def test_reverts_regression(self):
        # baseline already good; a flat candidate must NOT be kept
        result = autoexp({"colormap": "rich"}, [{"colormap": "flat"}], _render)
        assert result.improved is False
        assert result.best_params["colormap"] == "rich"
        assert result.trials[-1].kept is False

    def test_picks_best_of_several(self):
        result = autoexp(
            {"colormap": "flat"},
            [{"colormap": "flat2"}, {"colormap": "rich"}, {"colormap": "flat3"}],
            _render,
        )
        assert result.best_params["colormap"] == "rich"

    def test_min_delta_blocks_marginal(self):
        # huge min_delta means even a real improvement is rejected
        result = autoexp({"colormap": "flat"}, [{"colormap": "rich"}], _render, min_delta=1.0)
        assert result.improved is False
        assert result.best_params["colormap"] == "flat"

    def test_empty_candidates_is_baseline(self):
        result = autoexp({"colormap": "rich"}, [], _render)
        assert result.improved is False
        assert len(result.trials) == 1
        assert result.trials[0].label == "baseline"

    def test_baseline_recorded_and_kept(self):
        result = autoexp({"colormap": "flat"}, [{"colormap": "rich"}], _render)
        assert result.trials[0].label == "baseline"
        assert result.trials[0].kept is True

    def test_to_dict(self):
        result = autoexp({"colormap": "flat"}, [{"colormap": "rich"}], _render)
        d = result.to_dict()
        assert {"best_params", "best_score", "baseline_score", "improved", "trials"} <= set(d)
        assert isinstance(d["trials"], list)
        assert {"params", "score", "metrics", "kept", "label"} <= set(d["trials"][0])

    def test_trial_dataclass(self):
        result = autoexp({"colormap": "rich"}, [], _render)
        assert isinstance(result.trials[0], Trial)
