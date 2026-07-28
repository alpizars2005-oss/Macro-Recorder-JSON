"""Tests for deterministic camera preparation."""

from __future__ import annotations

import threading
import unittest

from pynput import mouse

from macro_app.camera_alignment import CameraAligner, CameraAlignmentConfig
from macro_app.client_geometry import ClientRect, NormalizedPoint


class FakeMouse:
    def __init__(self) -> None:
        self.positions: list[tuple[int, int]] = []
        self.pressed: list[object] = []
        self.released: list[object] = []
        self.scrolls: list[tuple[int, int]] = []
        self._position = (0, 0)

    @property
    def position(self) -> tuple[int, int]:
        return self._position

    @position.setter
    def position(self, value: tuple[int, int]) -> None:
        self._position = value
        self.positions.append(value)

    def press(self, button: object) -> None:
        self.pressed.append(button)

    def release(self, button: object) -> None:
        self.released.append(button)

    def scroll(self, dx: int, dy: int) -> None:
        self.scrolls.append((dx, dy))


class FakeKeyboard:
    def __init__(self) -> None:
        self.pressed: list[object] = []
        self.released: list[object] = []

    def press(self, key: object) -> None:
        self.pressed.append(key)

    def release(self, key: object) -> None:
        self.released.append(key)


class CameraAlignmentTests(unittest.TestCase):
    def test_alignment_saturates_pitch_normalizes_zoom_and_centers_pointer(self) -> None:
        mouse_controller = FakeMouse()
        keyboard_controller = FakeKeyboard()
        config = CameraAlignmentConfig(
            anchor=NormalizedPoint(0.5, 0.25),
            drag_overshoot_ratio=0.25,
            settle_seconds=0.0,
            zoom_passes=2,
            zoom_hold_seconds=0.0,
            zoom_back_steps=3,
        )

        result = CameraAligner(sleep=lambda _seconds: None).align(
            ClientRect(100, 50, 800, 600),
            config,
            mouse_controller,
            keyboard_controller,
            stop_event=threading.Event(),
            window_allowed=lambda: True,
        )

        self.assertTrue(result.completed)
        self.assertEqual(mouse_controller.positions[0], (500, 200))
        self.assertEqual(mouse_controller.positions[1], (500, 800))
        self.assertEqual(mouse_controller.position, (500, 350))
        self.assertEqual(mouse_controller.pressed, [mouse.Button.right])
        self.assertEqual(mouse_controller.released, [mouse.Button.right])
        self.assertEqual(mouse_controller.scrolls, [(0, 3)])
        self.assertEqual(len(keyboard_controller.pressed), 2)
        self.assertEqual(len(keyboard_controller.released), 2)

    def test_alignment_stops_when_foreground_guard_fails(self) -> None:
        result = CameraAligner(sleep=lambda _seconds: None).align(
            ClientRect(0, 0, 1920, 1080),
            CameraAlignmentConfig(settle_seconds=0.0, zoom_hold_seconds=0.0),
            FakeMouse(),
            FakeKeyboard(),
            stop_event=threading.Event(),
            window_allowed=lambda: False,
        )

        self.assertFalse(result.completed)


if __name__ == "__main__":
    unittest.main()
