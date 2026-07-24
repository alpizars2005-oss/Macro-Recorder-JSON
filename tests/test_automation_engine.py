"""Tests for visible trigger-driven automation behavior."""

from __future__ import annotations

import os
import queue
import time
import unittest

# GitHub's Linux test runners are headless. The dummy backend is importable
# without an X server and these tests inject fake mouse/recorder objects.
os.environ.setdefault("PYNPUT_BACKEND", "dummy")

from macro_app.automation_engine import AutomationEngine
from macro_app.automation_models import AutomationProfile, PixelTrigger, Point, RGBColor
from macro_app.screen_capture import SampleResult
from macro_app.window_guard import WindowCheck


class FakeSampler:
    def __init__(self) -> None:
        self.closed = False

    def sample(self, point: Point, radius: int = 1) -> SampleResult:
        return SampleResult(RGBColor(0, 255, 0), point, radius)

    def close(self) -> None:
        self.closed = True


class FakeMouse:
    def __init__(self) -> None:
        self.position = (0, 0)
        self.clicks: list[tuple[tuple[int, int], object, int]] = []

    def click(self, button: object, count: int = 1) -> None:
        self.clicks.append((self.position, button, count))


class FakeRecorder:
    def __init__(self) -> None:
        self.playing = False
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()

    def load(self, _path: object) -> None:
        return None

    def play(self, speed: float, delay: float) -> None:
        self.playing = False

    def request_stop(self) -> None:
        self.playing = False


class AutomationEngineTests(unittest.TestCase):
    def test_trigger_clicks_once_and_stops_at_max_runs(self) -> None:
        profile = AutomationProfile(
            name="test",
            window_title_contains="Roblox",
            load_delay=0,
            max_runs=1,
            triggers=[
                PixelTrigger(
                    name="Restart",
                    enabled=True,
                    sample_point=Point(5, 5),
                    click_point=Point(8, 9),
                    target_color=RGBColor(0, 255, 0),
                    required_matches=1,
                    poll_interval=0.02,
                    cooldown=0,
                )
            ],
        )
        fake_mouse = FakeMouse()
        engine = AutomationEngine(
            profile,
            sampler_factory=FakeSampler,
            mouse_factory=lambda: fake_mouse,
            recorder_factory=FakeRecorder,
            window_checker=lambda _title: WindowCheck(True, "Roblox", True),
            arming_delay=0,
        )

        engine.start()
        deadline = time.monotonic() + 2
        while engine.active and time.monotonic() < deadline:
            time.sleep(0.01)

        self.assertFalse(engine.active)
        self.assertEqual(engine.runs_completed, 1)
        self.assertEqual(fake_mouse.clicks[0][0], (8, 9))

    def test_window_guard_prevents_click(self) -> None:
        profile = AutomationProfile(
            name="test",
            window_title_contains="Roblox",
            triggers=[
                PixelTrigger(
                    name="Restart",
                    enabled=True,
                    sample_point=Point(5, 5),
                    click_point=Point(8, 9),
                    target_color=RGBColor(0, 255, 0),
                    required_matches=1,
                    poll_interval=0.02,
                    cooldown=0,
                )
            ],
        )
        fake_mouse = FakeMouse()
        engine = AutomationEngine(
            profile,
            sampler_factory=FakeSampler,
            mouse_factory=lambda: fake_mouse,
            recorder_factory=FakeRecorder,
            window_checker=lambda _title: WindowCheck(False, "Notepad", True),
            arming_delay=0,
        )

        engine.start()
        time.sleep(0.12)
        engine.request_stop()
        deadline = time.monotonic() + 2
        while engine.active and time.monotonic() < deadline:
            time.sleep(0.01)

        self.assertEqual(fake_mouse.clicks, [])


if __name__ == "__main__":
    unittest.main()
