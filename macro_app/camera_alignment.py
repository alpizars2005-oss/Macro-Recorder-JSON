"""Deterministic camera preparation for visible Roblox automation."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from pynput import keyboard, mouse

from .client_geometry import ClientRect, NormalizedPoint


class MouseController(Protocol):
    position: tuple[int, int]

    def press(self, button: mouse.Button) -> None: ...
    def release(self, button: mouse.Button) -> None: ...
    def scroll(self, dx: int, dy: int) -> None: ...


class KeyboardController(Protocol):
    def press(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...
    def release(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...


@dataclass(frozen=True, slots=True)
class CameraAlignmentConfig:
    """One reproducible camera-normalization sequence."""

    enabled: bool = True
    anchor: NormalizedPoint = field(default_factory=lambda: NormalizedPoint(0.70, 0.22))
    drag_overshoot_ratio: float = 0.25
    settle_seconds: float = 0.15
    zoom_key: str = "o"
    zoom_passes: int = 2
    zoom_hold_seconds: float = 0.50
    zoom_back_steps: int = 0
    center_pointer_after: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.drag_overshoot_ratio <= 2.0:
            raise ValueError("Camera drag overshoot must be between 0.0 and 2.0.")
        if not 0.0 <= self.settle_seconds <= 5.0:
            raise ValueError("Camera settle time must be between 0.0 and 5.0 seconds.")
        if len(self.zoom_key) != 1 or not self.zoom_key.isprintable():
            raise ValueError("Camera zoom key must contain one printable character.")
        if not 0 <= self.zoom_passes <= 10:
            raise ValueError("Camera zoom passes must be between 0 and 10.")
        if not 0.0 <= self.zoom_hold_seconds <= 5.0:
            raise ValueError("Camera zoom hold must be between 0.0 and 5.0 seconds.")
        if not -50 <= self.zoom_back_steps <= 50:
            raise ValueError("Camera zoom-back steps must be between -50 and 50.")


@dataclass(frozen=True, slots=True)
class CameraAlignmentResult:
    completed: bool
    reason: str


class CameraAligner:
    """Run a bounded, foreground-guarded camera preparation sequence."""

    def __init__(
        self,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sleep = sleep

    def align(
        self,
        rect: ClientRect,
        config: CameraAlignmentConfig,
        mouse_controller: MouseController,
        keyboard_controller: KeyboardController,
        *,
        stop_event: threading.Event,
        window_allowed: Callable[[], bool],
    ) -> CameraAlignmentResult:
        if not config.enabled:
            return CameraAlignmentResult(True, "Camera preparation is disabled.")
        if not self._ready(stop_event, window_allowed):
            return CameraAlignmentResult(False, "Stopped before camera preparation.")

        anchor_x, anchor_y = config.anchor.to_desktop(rect)
        drag_y = rect.top + rect.height + round(rect.height * config.drag_overshoot_ratio)
        mouse_controller.position = (anchor_x, anchor_y)
        if not self._pause(config.settle_seconds, stop_event, window_allowed):
            return CameraAlignmentResult(False, "Stopped before the camera drag.")

        right_pressed = False
        try:
            mouse_controller.press(mouse.Button.right)
            right_pressed = True
            mouse_controller.position = (anchor_x, drag_y)
            if not self._pause(config.settle_seconds, stop_event, window_allowed):
                return CameraAlignmentResult(False, "Stopped during the camera drag.")
        finally:
            if right_pressed:
                try:
                    mouse_controller.release(mouse.Button.right)
                except Exception:
                    pass

        zoom_key = keyboard.KeyCode.from_char(config.zoom_key)
        for _ in range(config.zoom_passes):
            if not self._ready(stop_event, window_allowed):
                return CameraAlignmentResult(False, "Stopped before zoom normalization.")
            pressed = False
            try:
                keyboard_controller.press(zoom_key)
                pressed = True
                if not self._pause(config.zoom_hold_seconds, stop_event, window_allowed):
                    return CameraAlignmentResult(False, "Stopped during zoom normalization.")
            finally:
                if pressed:
                    try:
                        keyboard_controller.release(zoom_key)
                    except Exception:
                        pass
            if not self._pause(config.settle_seconds, stop_event, window_allowed):
                return CameraAlignmentResult(False, "Stopped between zoom passes.")

        if config.zoom_back_steps:
            if not self._ready(stop_event, window_allowed):
                return CameraAlignmentResult(False, "Stopped before the zoom correction.")
            mouse_controller.position = rect.center
            mouse_controller.scroll(0, config.zoom_back_steps)
            if not self._pause(config.settle_seconds, stop_event, window_allowed):
                return CameraAlignmentResult(False, "Stopped after the zoom correction.")

        if config.center_pointer_after:
            mouse_controller.position = rect.center

        return CameraAlignmentResult(True, "Camera preparation completed.")

    def _pause(
        self,
        seconds: float,
        stop_event: threading.Event,
        window_allowed: Callable[[], bool],
    ) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        while True:
            if not self._ready(stop_event, window_allowed):
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            self._sleep(min(0.05, remaining))

    @staticmethod
    def _ready(stop_event: threading.Event, window_allowed: Callable[[], bool]) -> bool:
        return not stop_event.is_set() and bool(window_allowed())
