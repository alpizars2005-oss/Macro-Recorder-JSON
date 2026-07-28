"""Tests for visually confirmed TDS semantic actions."""

from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import unittest

from pynput import keyboard, mouse

from macro_app.client_geometry import ClientRect, NormalizedPoint
from macro_app.client_window import ClientWindowCheck
from macro_app.pixel_detector_runtime import DetectorObservation
from macro_app.semantic_strategy import PlaceTowerAction, SemanticStrategy, UpgradeTowerAction
from macro_app.tds_visual_adapter import TDSVisualAdapter
from macro_app.window_guard import WindowCheck


class FakeMouse:
    def __init__(self) -> None:
        self.position = (0, 0)
        self.clicks: list[tuple[mouse.Button, int, tuple[int, int]]] = []

    def click(self, button: mouse.Button, count: int = 1) -> None:
        self.clicks.append((button, count, self.position))


class FakeKeyboard:
    def __init__(self) -> None:
        self.pressed: list[str] = []
        self.released: list[str] = []

    @staticmethod
    def _value(key: keyboard.Key | keyboard.KeyCode) -> str:
        return getattr(key, "char", None) or str(key)

    def press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self.pressed.append(self._value(key))

    def release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self.released.append(self._value(key))


class FakeDetectorRuntime:
    def __init__(self, *, matched: bool = True) -> None:
        self.matched = matched
        self.closed = False

    def detector_names(self) -> tuple[str, ...]:
        return ("tower-panel", "insufficient-funds")

    def wait_for(self, name: str, **_kwargs: object) -> DetectorObservation | None:
        if self.matched and name == "tower-panel":
            return DetectorObservation(name, True, 1.0, 3, 3)
        return None

    def matches(self, name: str, _rect: ClientRect) -> bool:
        return self.matched and name == "tower-panel"

    def close(self) -> None:
        self.closed = True


class TDSVisualAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rect = ClientRect(100, 200, 1000, 600)
        self.mouse = FakeMouse()
        self.keyboard = FakeKeyboard()
        self.runtime = FakeDetectorRuntime()
        self.strategy = SemanticStrategy(name="Test")

    def _client(self, _title: str) -> ClientWindowCheck:
        return ClientWindowCheck(
            window=WindowCheck(allowed=True, title="Roblox", supported=True),
            rect=self.rect,
        )

    def _adapter(self) -> TDSVisualAdapter:
        return TDSVisualAdapter(
            self.strategy,
            strategy_path=Path("strategy.json"),
            client_checker=self._client,
            detector_runtime=self.runtime,
            mouse_factory=lambda: self.mouse,
            keyboard_factory=lambda: self.keyboard,
        )

    def test_place_tower_requires_and_uses_visual_confirmation(self) -> None:
        adapter = self._adapter()
        action = PlaceTowerAction(
            tower_id="farm-1",
            slot=1,
            point=NormalizedPoint(0.25, 0.50),
            confirmation_detector="tower-panel",
        )

        result = adapter.place_tower(action, action.point, self.rect, threading.Event())

        self.assertTrue(result.success)
        self.assertEqual(self.keyboard.pressed[0], "1")
        self.assertEqual(self.mouse.clicks[0][2], action.point.to_desktop(self.rect))
        self.assertIn("farm-1", adapter.tower_points)

    def test_place_tower_without_detector_fails_closed(self) -> None:
        adapter = self._adapter()
        action = PlaceTowerAction(
            tower_id="farm-1",
            slot=1,
            point=NormalizedPoint(0.25, 0.50),
        )

        result = adapter.place_tower(action, action.point, self.rect, threading.Event())

        self.assertFalse(result.success)
        self.assertFalse(result.retryable)
        self.assertEqual(self.mouse.clicks, [])

    def test_upgrade_unknown_tower_is_rejected(self) -> None:
        adapter = self._adapter()
        action = UpgradeTowerAction(
            tower_id="missing",
            confirmation_detector="tower-panel",
        )

        result = adapter.upgrade_tower(action, self.rect, threading.Event())

        self.assertFalse(result.success)
        self.assertFalse(result.retryable)
        self.assertIn("Unknown tower", result.reason)

    def test_cleanup_releases_keys_and_closes_detector_runtime(self) -> None:
        adapter = self._adapter()

        adapter.cleanup()

        self.assertTrue(self.runtime.closed)
        self.assertIn("e", self.keyboard.released)
        self.assertIn("q", self.keyboard.released)


if __name__ == "__main__":
    unittest.main()
