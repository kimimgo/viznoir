"""Tests for anim/timeline.py — scene sequencing."""

from __future__ import annotations


class TestScene:
    def test_scene_creation(self):
        from viznoir.anim.timeline import Scene

        s = Scene(asset_indices=[0, 1], duration=3.0, transition="fade_in")
        assert s.duration == 3.0
        assert s.transition == "fade_in"


class TestTimeline:
    def test_total_duration(self):
        from viznoir.anim.timeline import Scene, Timeline

        scenes = [
            Scene(asset_indices=[0], duration=3.0),
            Scene(asset_indices=[1], duration=4.0),
        ]
        tl = Timeline(scenes)
        assert tl.total_duration == 7.0

    def test_frame_count(self):
        from viznoir.anim.timeline import Scene, Timeline

        scenes = [Scene(asset_indices=[0], duration=2.0)]
        tl = Timeline(scenes, fps=30)
        assert tl.frame_count == 60

    def test_scene_at_time(self):
        from viznoir.anim.timeline import Scene, Timeline

        scenes = [
            Scene(asset_indices=[0], duration=3.0),
            Scene(asset_indices=[1], duration=4.0),
        ]
        tl = Timeline(scenes)
        idx, local_t = tl.scene_at(0.0)
        assert idx == 0
        assert local_t == 0.0

        idx, local_t = tl.scene_at(3.5)
        assert idx == 1
        assert 0.0 < local_t < 1.0

    def test_scene_at_end(self):
        from viznoir.anim.timeline import Scene, Timeline

        scenes = [Scene(asset_indices=[0], duration=2.0)]
        tl = Timeline(scenes)
        idx, local_t = tl.scene_at(2.0)
        assert idx == 0
        assert local_t == 1.0

    def test_empty_timeline(self):
        from viznoir.anim.timeline import Timeline

        tl = Timeline([])
        assert tl.total_duration == 0.0
        assert tl.frame_count == 0
