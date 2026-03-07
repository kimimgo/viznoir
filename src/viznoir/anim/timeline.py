"""Scene timeline — manages scene sequencing and duration."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field


@dataclass
class Scene:
    """A single scene in the timeline."""
    asset_indices: list[int]
    duration: float = 3.0
    transition: str = "fade_in"
    equation_entrance: str | None = None


@dataclass
class Timeline:
    """Ordered sequence of scenes with timing."""
    scenes: list[Scene]
    fps: int = 30
    _prefix_sums: list[float] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self._build_prefix_sums()

    def _build_prefix_sums(self) -> None:
        """Pre-compute cumulative duration for O(log n) scene lookup."""
        self._prefix_sums = []
        total = 0.0
        for s in self.scenes:
            total += s.duration
            self._prefix_sums.append(total)

    @property
    def total_duration(self) -> float:
        return self._prefix_sums[-1] if self._prefix_sums else 0.0

    @property
    def frame_count(self) -> int:
        return int(self.total_duration * self.fps)

    def scene_at(self, global_t: float) -> tuple[int, float]:
        """Return (scene_index, local_t) for a given global time.

        local_t is normalized [0, 1] within the scene.
        Uses binary search for O(log n) performance.
        """
        if not self.scenes:
            return (0, 0.0)

        t = max(0.0, min(global_t, self.total_duration))
        idx = bisect.bisect_left(self._prefix_sums, t)
        idx = min(idx, len(self.scenes) - 1)

        scene = self.scenes[idx]
        scene_start = self._prefix_sums[idx] - scene.duration
        local = (t - scene_start) / scene.duration if scene.duration > 0 else 0.0
        return (idx, min(max(local, 0.0), 1.0))

    def frame_times(self) -> list[float]:
        """Generate list of global times for each frame."""
        if self.frame_count == 0:
            return []
        dt = 1.0 / self.fps
        return [i * dt for i in range(self.frame_count)]
