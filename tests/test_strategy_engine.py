"""Tests for the recorded strategy engine."""

from __future__ import annotations

import os
import queue
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault("PYNPUT_BACKEND", "dummy")

from macro_app.model import MacroEvent
from macro_app.strategy_engine import RecordedStrategyEngine
from macro_app.strategy_models import KeyPulse, RecordedStrategyProfile
from macro_app.window_guard import WindowCheck


class FakeRecorder:
    def __init__(self) -> None:
        self.events = [MacroEvent(0.0, "mouse_move", {"x": 1, "y": 1})]
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.playing = False

    def load(self, _path: Path) -> None:
        return None

    def play(self, speed: float, delay: float) -> None:
        self.playing = False

    def request_stop(self) -> None:
        self.playing = False


class FakeSampler:
    def close(self) -> None:
        return None


class FakeMouse:
    position = (0, 0)

    def click(self, _button: object, count: int = 1) -> None:
        return None


class FakeKeyboard:
    def __init__(self) -> None:
        self.pressed: list[str] = []
        self.released: list[str] = []

    def press(self, key: object) -> None:
        self.pressed.append(str(key))

    def release(self, key: object) -> None:
        self.released.append(str(key))


class StrategyEngineTests(unittest.TestCase):
    def test_automatic_key_runs_during_post_macro_wait(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            macro = Path(folder) / "macro.json"
            macro.write_text("{}", encoding="utf-8")
            profile = RecordedStrategyProfile(
                name="test",
                window_title_contains="Roblox",
                macro_path=str(macro),
                arming_delay=0,
                post_macro_wait=0.18,
                max_runs=1,
                optimize_recording=False,
                key_pulses=[
                    KeyPulse(
                        name="Call to Arms",
                        key="f",
                        start_after_seconds=0,
                        interval_seconds=0.1,
                        press_duration=0.01,
                    )
                ],
            )
            keyboard_controller = FakeKeyboard()
            engine = RecordedStrategyEngine(
                profile,
                recorder_factory=FakeRecorder,
                sampler_factory=FakeSampler,
                mouse_factory=FakeMouse,
                keyboard_factory=lambda: keyboard_controller,
                window_checker=lambda _title: WindowCheck(True, "Roblox", True),
            )

            engine.start()
            deadline = time.monotonic() + 2
            while engine.active and time.monotonic() < deadline:
                time.sleep(0.01)

            self.assertFalse(engine.active)
            self.assertEqual(engine.runs_completed, 1)
            self.assertGreaterEqual(len(keyboard_controller.pressed), 1)
            self.assertEqual(len(keyboard_controller.pressed), len(keyboard_controller.released))


if __name__ == "__main__":
    unittest.main()
