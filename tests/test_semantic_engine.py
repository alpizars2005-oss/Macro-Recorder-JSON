"""Tests for the explicit semantic strategy execution engine."""

from __future__ import annotations

import queue
import threading
import time
import unittest

from macro_app.camera_alignment import CameraAlignmentResult
from macro_app.client_geometry import ClientRect, NormalizedPoint
from macro_app.client_window import ClientWindowCheck
from macro_app.retry_policy import RetryPolicy
from macro_app.semantic_engine import ActionResult, SemanticStrategyEngine
from macro_app.semantic_strategy import (
    DisableAbilityAction,
    EnableAbilityAction,
    PlaceTowerAction,
    SemanticStrategy,
    UpgradeTowerToLevelAction,
    WaitAction,
    WaitForWaveAction,
)
from macro_app.window_guard import WindowCheck


class FakeMouse:
    def __init__(self) -> None:
        self.position = (0, 0)

    def press(self, _button) -> None:
        return None

    def release(self, _button) -> None:
        return None

    def scroll(self, _dx: int, _dy: int) -> None:
        return None


class FakeKeyboard:
    def __init__(self) -> None:
        self.pressed: list[str] = []
        self.released: list[str] = []

    @staticmethod
    def _name(key) -> str:
        return getattr(key, "char", None) or str(key)

    def press(self, key) -> None:
        self.pressed.append(self._name(key))

    def release(self, key) -> None:
        self.released.append(self._name(key))


class FakeAligner:
    def align(self, *_args, **_kwargs) -> CameraAlignmentResult:
        return CameraAlignmentResult(True, "aligned")


class FakeAdapter:
    def __init__(self) -> None:
        self.place_results: list[ActionResult] = []
        self.place_points: list[NormalizedPoint] = []
        self.upgrade_calls = 0
        self.wave_values: list[int | None] = []
        self.detector_ready = True
        self.auto_skip = False
        self.cleaned = False

    def place_tower(self, _action, point, _rect, _stop_event) -> ActionResult:
        self.place_points.append(point)
        if self.place_results:
            return self.place_results.pop(0)
        return ActionResult(True)

    def upgrade_tower(self, _action, _rect, _stop_event) -> ActionResult:
        self.upgrade_calls += 1
        return ActionResult(True)

    def upgrade_tower_to_level(self, _action, _rect, _stop_event) -> ActionResult:
        self.upgrade_calls += 1
        return ActionResult(True)

    def current_wave(self, _rect) -> int | None:
        if self.wave_values:
            return self.wave_values.pop(0)
        return None

    def set_auto_skip(self, action, _rect, _stop_event) -> ActionResult:
        self.auto_skip = action.enabled
        return ActionResult(True)

    def detector_matches(self, _name, _rect) -> bool:
        return self.detector_ready

    def expect_result(self, _action, _rect, _stop_event) -> ActionResult:
        return ActionResult(True, details="Triumph")

    def cleanup(self) -> None:
        self.cleaned = True


def ready_client(_required: str) -> ClientWindowCheck:
    return ClientWindowCheck(
        window=WindowCheck(allowed=True, title="Roblox", supported=True),
        rect=ClientRect(10, 20, 1280, 720),
    )


class SemanticEngineTests(unittest.TestCase):
    def make_engine(
        self,
        strategy: SemanticStrategy,
        adapter: FakeAdapter,
        keyboard_controller: FakeKeyboard | None = None,
    ) -> SemanticStrategyEngine:
        keyboard_controller = keyboard_controller or FakeKeyboard()
        return SemanticStrategyEngine(
            strategy,
            adapter,
            client_checker=ready_client,
            mouse_factory=FakeMouse,
            keyboard_factory=lambda: keyboard_controller,
            camera_aligner_factory=FakeAligner,
        )

    def test_placement_retries_use_deterministic_candidate_points(self) -> None:
        adapter = FakeAdapter()
        adapter.place_results = [
            ActionResult(False, "blocked", retryable=True),
            ActionResult(False, "blocked", retryable=True),
            ActionResult(True, "placed"),
        ]
        strategy = SemanticStrategy(
            name="Retry placement",
            actions=[
                PlaceTowerAction(
                    "farm-1",
                    1,
                    NormalizedPoint(0.5, 0.5),
                    retry=RetryPolicy(
                        attempts=3,
                        initial_delay=0.0,
                        max_delay=0.0,
                        jitter_radius=0.01,
                    ),
                )
            ],
        )
        engine = self.make_engine(strategy, adapter)

        engine.run_blocking()

        self.assertEqual(len(adapter.place_points), 3)
        self.assertEqual(adapter.place_points[0], NormalizedPoint(0.5, 0.5))
        self.assertNotEqual(adapter.place_points[1], adapter.place_points[0])
        self.assertTrue(adapter.cleaned)
        self.assertFalse(engine.stop_event.is_set())

    def test_non_retryable_failure_stops_strategy(self) -> None:
        adapter = FakeAdapter()
        adapter.place_results = [ActionResult(False, "wrong map", retryable=False)]
        strategy = SemanticStrategy(
            name="Stop on failure",
            actions=[
                PlaceTowerAction(
                    "farm-1",
                    1,
                    NormalizedPoint(0.5, 0.5),
                    retry=RetryPolicy(attempts=5),
                )
            ],
        )
        engine = self.make_engine(strategy, adapter)

        engine.run_blocking()

        self.assertEqual(len(adapter.place_points), 1)
        self.assertTrue(engine.stop_event.is_set())
        self.assertTrue(adapter.cleaned)

    def test_wait_for_wave_then_target_level_upgrade(self) -> None:
        adapter = FakeAdapter()
        adapter.wave_values = [3, 4, 5]
        strategy = SemanticStrategy(
            name="Wave gated",
            actions=[
                PlaceTowerAction("farm-1", 1, NormalizedPoint(0.5, 0.5)),
                WaitForWaveAction(wave=5, timeout_seconds=1.0, poll_interval=0.001),
                UpgradeTowerToLevelAction("farm-1", target_level=5),
            ],
        )
        engine = self.make_engine(strategy, adapter)

        engine.run_blocking()

        self.assertEqual(adapter.upgrade_calls, 1)
        self.assertFalse(engine.stop_event.is_set())

    def test_detector_gated_ability_is_pressed_and_released(self) -> None:
        adapter = FakeAdapter()
        keyboard_controller = FakeKeyboard()
        strategy = SemanticStrategy(
            name="Abilities",
            detectors=[],
            actions=[
                EnableAbilityAction(
                    "Call to Arms",
                    "f",
                    interval_seconds=0.01,
                    press_duration=0.005,
                ),
                WaitAction(0.04),
                DisableAbilityAction("Call to Arms"),
            ],
        )
        engine = self.make_engine(strategy, adapter, keyboard_controller)

        engine.run_blocking()

        self.assertIn("f", keyboard_controller.pressed)
        self.assertIn("f", keyboard_controller.released)
        self.assertFalse(engine.stop_event.is_set())

    def test_engine_reports_completed_message(self) -> None:
        adapter = FakeAdapter()
        strategy = SemanticStrategy(name="Empty", actions=[])
        engine = self.make_engine(strategy, adapter)

        engine.run_blocking()

        names: list[str] = []
        while True:
            try:
                name, _value = engine.messages.get_nowait()
            except queue.Empty:
                break
            names.append(name)
        self.assertIn("completed", names)
        self.assertEqual(names[-1], "stopped")


if __name__ == "__main__":
    unittest.main()
