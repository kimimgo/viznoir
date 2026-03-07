"""Scene timeline — manages scene sequencing and duration."""

from __future__ import annotations

from dataclasses import dataclass


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

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    @property
    def frame_count(self) -> int:
        return int(self.total_duration * self.fps)

    def scene_at(self, global_t: float) -> tuple[int, float]:
        """Return (scene_index, local_t) for a given global time.

        local_t is normalized [0, 1] within the scene.
        """
        if not self.scenes:
            return (0, 0.0)

        t = max(0.0, min(global_t, self.total_duration))
        elapsed = 0.0
        for i, scene in enumerate(self.scenes):
            if elapsed + scene.duration >= t or i == len(self.scenes) - 1:
                local = (t - elapsed) / scene.duration if scene.duration > 0 else 0.0
                return (i, min(local, 1.0))
            elapsed += scene.duration
        return (len(self.scenes) - 1, 1.0)

    def frame_times(self) -> list[float]:
        """Generate list of global times for each frame."""
        if self.frame_count == 0:
            return []
        dt = 1.0 / self.fps
        return [i * dt for i in range(self.frame_count)]
