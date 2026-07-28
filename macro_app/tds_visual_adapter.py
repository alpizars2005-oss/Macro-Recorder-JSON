"""Visual TDS adapter for the generic semantic strategy engine."""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Callable, Protocol

from pynput import keyboard, mouse

from .client_geometry import ClientRect, NormalizedPoint
from .client_window import ClientWindowCheck, check_foreground_client
from .pixel_detector_runtime import DetectorObservation, PixelDetectorRuntime
from .semantic_engine import ActionResult
from .semantic_strategy import (
    ExpectResultAction,
    PlaceTowerAction,
    SemanticStrategy,
    SetAutoSkipAction,
    UpgradeTowerAction,
    UpgradeTowerToLevelAction,
)


class MouseController(Protocol):
    position: tuple[int, int]

    def click(self, button: mouse.Button, count: int = 1) -> None: ...


class KeyboardController(Protocol):
    def press(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...
    def release(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...


class TDSVisualAdapter:
    """Confirm semantic TDS actions with user-calibrated pixel signatures.

    This adapter never treats a click as proof of success. Critical placement
    and upgrade actions require a named detector and return a retryable failure
    when the expected visual state is not confirmed.
    """

    def __init__(
        self,
        strategy: SemanticStrategy,
        *,
        strategy_path: Path,
        client_checker: Callable[[str], ClientWindowCheck] = check_foreground_client,
        detector_runtime: PixelDetectorRuntime | None = None,
        mouse_factory: Callable[[], MouseController] = mouse.Controller,
        keyboard_factory: Callable[[], KeyboardController] = keyboard.Controller,
    ) -> None:
        self.strategy = strategy
        self.strategy_path = strategy_path.expanduser().resolve()
        self.client_checker = client_checker
        self.detectors = detector_runtime or PixelDetectorRuntime(
            strategy.detectors,
            base_directory=self.strategy_path.parent,
        )
        self.mouse = mouse_factory()
        self.keyboard = keyboard_factory()
        self.mouse_lock = threading.Lock()
        self.keyboard_lock = threading.Lock()
        self.tower_points: dict[str, NormalizedPoint] = {}
        self.skip_stop = threading.Event()
        self.skip_thread: threading.Thread | None = None
        self.skip_detector = ""
        self._known_detector_names = {name.casefold() for name in self.detectors.detector_names()}

    def place_tower(
        self,
        action: PlaceTowerAction,
        point: NormalizedPoint,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult:
        if not action.confirmation_detector:
            return ActionResult(
                False,
                f"Tower '{action.tower_id}' has no confirmation detector.",
                retryable=False,
            )
        if not self._window_allowed():
            return ActionResult(False, "Roblox lost focus before placement.", retryable=False)

        with self.mouse_lock:
            self._tap(str(action.slot), stop_event)
            if stop_event.is_set():
                return ActionResult(False, "Placement stopped before clicking.", retryable=False)
            self.mouse.position = point.to_desktop(rect)
            self.mouse.click(mouse.Button.left, 1)

        observation = self._wait_detector(
            action.confirmation_detector,
            stop_event,
            timeout_seconds=1.25,
        )
        if observation is not None:
            self.tower_points[action.tower_id.casefold()] = point
            return ActionResult(True, details=observation)

        self._tap(action.cancel_key, stop_event)
        if action.wait_for_funds and self._detector_exists("insufficient-funds"):
            current = self._current_rect()
            if current is not None and self.detectors.matches("insufficient-funds", current):
                return ActionResult(False, "Not enough money for tower placement.")
        return ActionResult(False, "Tower placement was not visually confirmed.")

    def upgrade_tower(
        self,
        action: UpgradeTowerAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult:
        point = self.tower_points.get(action.tower_id.casefold())
        if point is None:
            return ActionResult(False, f"Unknown tower position: {action.tower_id}.", False)
        if not action.confirmation_detector:
            return ActionResult(
                False,
                f"Upgrade for '{action.tower_id}' has no confirmation detector.",
                False,
            )

        with self.mouse_lock:
            self.mouse.position = point.to_desktop(rect)
            self.mouse.click(mouse.Button.left, 1)
        for _ in range(action.levels):
            self._tap("e", stop_event)
            if stop_event.wait(0.12):
                return ActionResult(False, "Upgrade stopped.", False)

        observation = self._wait_detector(
            action.confirmation_detector,
            stop_event,
            timeout_seconds=1.25,
        )
        if observation is not None:
            return ActionResult(True, details=observation)
        if self._detector_exists("insufficient-funds"):
            current = self._current_rect()
            if current is not None and self.detectors.matches("insufficient-funds", current):
                return ActionResult(False, "Not enough money for the requested upgrade.")
        return ActionResult(False, "Tower upgrade was not visually confirmed.")

    def upgrade_tower_to_level(
        self,
        action: UpgradeTowerToLevelAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult:
        point = self.tower_points.get(action.tower_id.casefold())
        if point is None:
            return ActionResult(False, f"Unknown tower position: {action.tower_id}.", False)
        if not action.level_detector:
            return ActionResult(
                False,
                f"Target level {action.target_level} has no visual detector.",
                False,
            )

        if self.detectors.matches(action.level_detector, rect):
            return ActionResult(True, details=action.target_level)

        with self.mouse_lock:
            self.mouse.position = point.to_desktop(rect)
            self.mouse.click(mouse.Button.left, 1)
        self._tap("e", stop_event)
        observation = self._wait_detector(
            action.level_detector,
            stop_event,
            timeout_seconds=0.90,
        )
        if observation is not None:
            return ActionResult(True, details=action.target_level)
        return ActionResult(
            False,
            f"Tower '{action.tower_id}' has not reached level {action.target_level} yet.",
        )

    def current_wave(self, rect: ClientRect) -> int | None:
        wave_detectors: list[tuple[int, str]] = []
        for name in self.detectors.detector_names():
            match = re.fullmatch(r"wave[-:_ ]?(\d+)", name.strip(), flags=re.IGNORECASE)
            if match:
                wave_detectors.append((int(match.group(1)), name))
        for wave, name in sorted(wave_detectors, reverse=True):
            if self.detectors.matches(name, rect):
                return wave
        return None

    def set_auto_skip(
        self,
        action: SetAutoSkipAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult:
        del rect
        if not action.enabled:
            self._stop_auto_skip()
            return ActionResult(True, details=False)
        if not action.detector:
            return ActionResult(False, "Auto-skip requires a visual detector.", False)
        self._stop_auto_skip()
        self.skip_detector = action.detector
        self.skip_stop.clear()
        self.skip_thread = threading.Thread(
            target=self._auto_skip_worker,
            args=(stop_event,),
            daemon=True,
            name="tds-auto-skip",
        )
        self.skip_thread.start()
        return ActionResult(True, details=True)

    def detector_matches(self, name: str, rect: ClientRect) -> bool:
        return self.detectors.matches(name, rect)

    def expect_result(
        self,
        action: ExpectResultAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult:
        del rect
        names: tuple[str, ...]
        if action.detector:
            names = (action.detector,)
        elif action.result.casefold() == "either":
            names = tuple(
                name for name in ("triumph", "game-over") if self._detector_exists(name)
            )
        else:
            conventional = "triumph" if action.result.casefold() == "triumph" else "game-over"
            names = (conventional,) if self._detector_exists(conventional) else ()
        if not names:
            return ActionResult(False, "No result detector is configured.", False)

        deadline = time.monotonic() + action.timeout_seconds
        consecutive: dict[str, int] = {name: 0 for name in names}
        while time.monotonic() <= deadline and not stop_event.is_set():
            if not self._window_allowed():
                return ActionResult(False, "Roblox lost focus while waiting for the result.", False)
            current = self._current_rect()
            if current is None:
                return ActionResult(False, "Roblox client area is unavailable.", False)
            for name in names:
                if self.detectors.matches(name, current):
                    consecutive[name] += 1
                    definition = self.detectors.detectors[name.casefold()].definition
                    if consecutive[name] >= definition.required_matches:
                        return ActionResult(True, details=name)
                else:
                    consecutive[name] = 0
            stop_event.wait(0.10)
        return ActionResult(False, f"Timed out waiting for {action.result}.", False)

    def cleanup(self) -> None:
        self._stop_auto_skip()
        for character in tuple("1234567890eq"):
            try:
                self.keyboard.release(keyboard.KeyCode.from_char(character))
            except Exception:
                pass
        self.detectors.close()

    def _auto_skip_worker(self, parent_stop: threading.Event) -> None:
        detector = self.skip_detector
        definition = self.detectors.detectors[detector.casefold()].definition
        consecutive = 0
        last_click = 0.0
        while not parent_stop.is_set() and not self.skip_stop.is_set():
            if not self._window_allowed():
                self.skip_stop.wait(0.10)
                continue
            rect = self._current_rect()
            if rect is None:
                self.skip_stop.wait(0.10)
                continue
            if self.detectors.matches(detector, rect):
                consecutive += 1
            else:
                consecutive = 0
            now = time.monotonic()
            if (
                consecutive >= definition.required_matches
                and now - last_click >= definition.cooldown
            ):
                with self.mouse_lock:
                    self.mouse.position = self.detectors.click_point(detector, rect)
                    self.mouse.click(mouse.Button.left, 1)
                consecutive = 0
                last_click = now
            self.skip_stop.wait(definition.poll_interval)

    def _stop_auto_skip(self) -> None:
        self.skip_stop.set()
        if self.skip_thread is not None:
            self.skip_thread.join(timeout=1.0)
        self.skip_thread = None
        self.skip_detector = ""

    def _tap(self, character: str, stop_event: threading.Event) -> None:
        if stop_event.is_set() or not self._window_allowed():
            return
        key = keyboard.KeyCode.from_char(character)
        pressed = False
        try:
            with self.keyboard_lock:
                self.keyboard.press(key)
                pressed = True
                stop_event.wait(0.05)
                self.keyboard.release(key)
                pressed = False
        finally:
            if pressed:
                try:
                    self.keyboard.release(key)
                except Exception:
                    pass

    def _wait_detector(
        self,
        name: str,
        stop_event: threading.Event,
        *,
        timeout_seconds: float,
    ) -> DetectorObservation | None:
        return self.detectors.wait_for(
            name,
            rect_provider=self._require_rect,
            stop_event=stop_event,
            timeout_seconds=timeout_seconds,
            window_allowed=self._window_allowed,
        )

    def _current_rect(self) -> ClientRect | None:
        result = self.client_checker(self.strategy.window_title_contains)
        return result.rect if result.ready else None

    def _require_rect(self) -> ClientRect:
        rect = self._current_rect()
        if rect is None:
            raise RuntimeError("The allowed Roblox client is not the active foreground window.")
        return rect

    def _window_allowed(self) -> bool:
        return self.client_checker(self.strategy.window_title_contains).ready

    def _detector_exists(self, name: str) -> bool:
        return name.casefold() in self._known_detector_names
