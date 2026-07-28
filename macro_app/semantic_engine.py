"""Execution engine for explicit, retryable TDS strategy actions."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from pynput import keyboard, mouse

from .camera_alignment import CameraAligner
from .client_geometry import ClientRect, NormalizedPoint
from .client_window import ClientWindowCheck, check_foreground_client
from .semantic_strategy import (
    AlignCameraAction,
    DisableAbilityAction,
    EnableAbilityAction,
    ExpectResultAction,
    PlaceTowerAction,
    SemanticAction,
    SemanticStrategy,
    SetAutoSkipAction,
    UpgradeTowerAction,
    UpgradeTowerToLevelAction,
    WaitAction,
    WaitForWaveAction,
)


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Result returned by the game-specific adapter for one attempt."""

    success: bool
    reason: str = ""
    retryable: bool = True
    details: Any = None


class SemanticActionAdapter(Protocol):
    """Game-specific visual confirmations used by the generic engine."""

    def place_tower(
        self,
        action: PlaceTowerAction,
        point: NormalizedPoint,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult: ...

    def upgrade_tower(
        self,
        action: UpgradeTowerAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult: ...

    def upgrade_tower_to_level(
        self,
        action: UpgradeTowerToLevelAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult: ...

    def current_wave(self, rect: ClientRect) -> int | None: ...

    def set_auto_skip(
        self,
        action: SetAutoSkipAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult: ...

    def detector_matches(self, name: str, rect: ClientRect) -> bool: ...

    def expect_result(
        self,
        action: ExpectResultAction,
        rect: ClientRect,
        stop_event: threading.Event,
    ) -> ActionResult: ...

    def cleanup(self) -> None: ...


class MouseController(Protocol):
    position: tuple[int, int]

    def press(self, button: mouse.Button) -> None: ...
    def release(self, button: mouse.Button) -> None: ...
    def scroll(self, dx: int, dy: int) -> None: ...


class KeyboardController(Protocol):
    def press(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...
    def release(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...


class SemanticStrategyEngine:
    """Execute one semantic strategy with bounded retries and safe cleanup."""

    def __init__(
        self,
        strategy: SemanticStrategy,
        adapter: SemanticActionAdapter,
        *,
        client_checker: Callable[[str], ClientWindowCheck] = check_foreground_client,
        mouse_factory: Callable[[], MouseController] = mouse.Controller,
        keyboard_factory: Callable[[], KeyboardController] = keyboard.Controller,
        camera_aligner_factory: Callable[[], CameraAligner] = CameraAligner,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.strategy = strategy
        self.adapter = adapter
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.active = False

        self._client_checker = client_checker
        self._mouse_factory = mouse_factory
        self._keyboard_factory = keyboard_factory
        self._camera_aligner_factory = camera_aligner_factory
        self._clock = clock
        self._keyboard_lock = threading.Lock()
        self._ability_stops: dict[str, threading.Event] = {}
        self._ability_threads: dict[str, threading.Thread] = {}
        self._mouse_controller: MouseController | None = None
        self._keyboard_controller: KeyboardController | None = None

    def start(self) -> None:
        if self.active:
            raise RuntimeError("The semantic strategy is already running.")
        self.strategy.validate()
        self.stop_event.clear()
        self.pause_event.clear()
        self.active = True
        self.thread = threading.Thread(
            target=self.run_blocking,
            daemon=True,
            name="semantic-tds-strategy",
        )
        self.thread.start()

    def run_blocking(self) -> None:
        """Execute synchronously; useful for tests and worker threads."""

        if not self.active:
            self.strategy.validate()
            self.stop_event.clear()
            self.pause_event.clear()
            self.active = True

        self._mouse_controller = self._mouse_factory()
        self._keyboard_controller = self._keyboard_factory()
        self.messages.put(("started", self.strategy.name))

        try:
            for index, action in enumerate(self.strategy.actions):
                if not self._ready():
                    return
                self.messages.put(("action_started", (index, action)))
                result = self._execute_action(index, action)
                if not result.success:
                    self.messages.put(("action_failed", (index, action, result.reason)))
                    self.stop_event.set()
                    return
                self.messages.put(("action_finished", (index, action, result.details)))
            self.messages.put(("completed", self.strategy.name))
        except Exception as exc:
            self.messages.put(("error", str(exc)))
            self.stop_event.set()
        finally:
            self._stop_all_abilities()
            self._release_known_inputs()
            try:
                self.adapter.cleanup()
            except Exception as exc:
                self.messages.put(("cleanup_error", str(exc)))
            self.active = False
            self.messages.put(("stopped", self.strategy.name))

    def request_stop(self) -> None:
        self.stop_event.set()
        self.pause_event.clear()
        self.messages.put(("stopping", None))

    def pause(self) -> None:
        if self.active:
            self.pause_event.set()
            self.messages.put(("paused", None))

    def resume(self) -> None:
        if self.active:
            self.pause_event.clear()
            self.messages.put(("resumed", None))

    def _execute_action(self, index: int, action: SemanticAction) -> ActionResult:
        client = self._require_client()
        rect = client.rect
        assert rect is not None

        if isinstance(action, AlignCameraAction):
            assert self._mouse_controller is not None
            assert self._keyboard_controller is not None
            result = self._camera_aligner_factory().align(
                rect,
                self.strategy.camera,
                self._mouse_controller,
                self._keyboard_controller,
                stop_event=self.stop_event,
                window_allowed=self._window_allowed,
            )
            return ActionResult(result.completed, result.reason, retryable=False)
        if isinstance(action, WaitAction):
            return ActionResult(self._wait(action.seconds), "Wait interrupted.")
        if isinstance(action, WaitForWaveAction):
            return self._wait_for_wave(action)
        if isinstance(action, PlaceTowerAction):
            return self._retry_place(index, action)
        if isinstance(action, UpgradeTowerAction):
            return self._retry_adapter_action(
                index,
                action,
                action.retry,
                lambda current_rect: self.adapter.upgrade_tower(
                    action,
                    current_rect,
                    self.stop_event,
                ),
            )
        if isinstance(action, UpgradeTowerToLevelAction):
            return self._retry_adapter_action(
                index,
                action,
                action.retry,
                lambda current_rect: self.adapter.upgrade_tower_to_level(
                    action,
                    current_rect,
                    self.stop_event,
                ),
            )
        if isinstance(action, SetAutoSkipAction):
            return self.adapter.set_auto_skip(action, rect, self.stop_event)
        if isinstance(action, EnableAbilityAction):
            return self._enable_ability(action)
        if isinstance(action, DisableAbilityAction):
            return self._disable_ability(action.name)
        if isinstance(action, ExpectResultAction):
            return self.adapter.expect_result(action, rect, self.stop_event)
        return ActionResult(False, f"Unsupported action at index {index}: {type(action).__name__}", False)

    def _retry_place(self, index: int, action: PlaceTowerAction) -> ActionResult:
        started = self._clock()
        last = ActionResult(False, "Tower placement was not attempted.")
        points = list(action.retry.candidate_points(action.point))

        for attempt, point in enumerate(points, start=1):
            if not self._ready():
                return ActionResult(False, "Stopped before tower placement completed.", False)
            if self._timed_out(started, action.retry.timeout_seconds):
                return ActionResult(False, "Tower placement retry timeout expired.", False)
            rect = self._require_client().rect
            assert rect is not None
            self.messages.put(("action_attempt", (index, attempt, point)))
            last = self.adapter.place_tower(action, point, rect, self.stop_event)
            if last.success or not last.retryable:
                return last
            if attempt < action.retry.attempts:
                delay = action.retry.delay_after_failure(attempt)
                self.messages.put(("action_retry", (index, attempt, delay, last.reason)))
                if not self._wait(delay):
                    return ActionResult(False, "Stopped during tower placement retry delay.", False)
        return last

    def _retry_adapter_action(
        self,
        index: int,
        action: SemanticAction,
        policy: Any,
        attempt_callback: Callable[[ClientRect], ActionResult],
    ) -> ActionResult:
        started = self._clock()
        last = ActionResult(False, "Action was not attempted.")

        for attempt in range(1, policy.attempts + 1):
            if not self._ready():
                return ActionResult(False, "Stopped before the action completed.", False)
            if self._timed_out(started, policy.timeout_seconds):
                return ActionResult(False, "Action retry timeout expired.", False)
            rect = self._require_client().rect
            assert rect is not None
            self.messages.put(("action_attempt", (index, attempt, None)))
            last = attempt_callback(rect)
            if last.success or not last.retryable:
                return last
            if attempt < policy.attempts:
                delay = policy.delay_after_failure(attempt)
                self.messages.put(("action_retry", (index, attempt, delay, last.reason)))
                if not self._wait(delay):
                    return ActionResult(False, "Stopped during action retry delay.", False)
        return last

    def _wait_for_wave(self, action: WaitForWaveAction) -> ActionResult:
        deadline = self._clock() + action.timeout_seconds
        last_wave: int | None = None
        while self._clock() < deadline:
            if not self._ready():
                return ActionResult(False, "Stopped while waiting for the wave.", False)
            rect = self._require_client().rect
            assert rect is not None
            last_wave = self.adapter.current_wave(rect)
            if last_wave is not None:
                self.messages.put(("wave", last_wave))
                if last_wave >= action.wave:
                    return ActionResult(True, details=last_wave)
            if not self._wait(action.poll_interval):
                return ActionResult(False, "Stopped while waiting for the wave.", False)
        return ActionResult(
            False,
            f"Timed out waiting for wave {action.wave}; last detected wave was {last_wave}.",
            False,
        )

    def _enable_ability(self, action: EnableAbilityAction) -> ActionResult:
        key = action.name.casefold()
        if key in self._ability_threads:
            return ActionResult(False, f"Ability '{action.name}' is already enabled.", False)
        run_stop = threading.Event()
        worker = threading.Thread(
            target=self._ability_worker,
            args=(action, run_stop),
            daemon=True,
            name=f"semantic-ability-{action.key.casefold()}",
        )
        self._ability_stops[key] = run_stop
        self._ability_threads[key] = worker
        worker.start()
        return ActionResult(True, details=action.name)

    def _disable_ability(self, name: str) -> ActionResult:
        key = name.casefold()
        stop = self._ability_stops.pop(key, None)
        worker = self._ability_threads.pop(key, None)
        if stop is None:
            return ActionResult(True, f"Ability '{name}' was not active.", details=name)
        stop.set()
        if worker is not None:
            worker.join(timeout=1.0)
        return ActionResult(True, details=name)

    def _ability_worker(self, action: EnableAbilityAction, run_stop: threading.Event) -> None:
        assert self._keyboard_controller is not None
        key = keyboard.KeyCode.from_char(action.key)

        while not self.stop_event.is_set() and not run_stop.is_set():
            if not self._ready(run_stop):
                return
            rect = self._require_client().rect
            assert rect is not None
            if action.ready_detector:
                try:
                    ready = self.adapter.detector_matches(action.ready_detector, rect)
                except Exception as exc:
                    self.messages.put(("ability_error", (action.name, str(exc))))
                    return
                if not ready:
                    if not self._wait_ability(min(0.10, action.interval_seconds), run_stop):
                        return
                    continue

            pressed = False
            try:
                with self._keyboard_lock:
                    if self.stop_event.is_set() or run_stop.is_set():
                        return
                    self._keyboard_controller.press(key)
                    pressed = True
                    if not self._wait_ability(action.press_duration, run_stop):
                        return
                    self._keyboard_controller.release(key)
                    pressed = False
                self.messages.put(("ability_pressed", (action.name, action.key.upper())))
            finally:
                if pressed:
                    try:
                        self._keyboard_controller.release(key)
                    except Exception:
                        pass
            if not self._wait_ability(action.interval_seconds, run_stop):
                return

    def _stop_all_abilities(self) -> None:
        for stop in self._ability_stops.values():
            stop.set()
        for worker in self._ability_threads.values():
            worker.join(timeout=1.0)
        self._ability_stops.clear()
        self._ability_threads.clear()

    def _require_client(self) -> ClientWindowCheck:
        result = self._client_checker(self.strategy.window_title_contains)
        if not result.ready:
            raise RuntimeError("The allowed Roblox client is not the active foreground window.")
        return result

    def _window_allowed(self) -> bool:
        return self._client_checker(self.strategy.window_title_contains).ready

    def _ready(self, extra_stop: threading.Event | None = None) -> bool:
        while self.pause_event.is_set() and not self.stop_event.is_set():
            if extra_stop is not None and extra_stop.is_set():
                return False
            self.stop_event.wait(0.05)
        if self.stop_event.is_set():
            return False
        if extra_stop is not None and extra_stop.is_set():
            return False
        return self._window_allowed()

    def _wait(self, seconds: float) -> bool:
        deadline = self._clock() + max(0.0, seconds)
        while self._clock() < deadline:
            if not self._ready():
                return False
            remaining = deadline - self._clock()
            self.stop_event.wait(min(0.05, max(0.0, remaining)))
        return self._ready()

    def _wait_ability(self, seconds: float, run_stop: threading.Event) -> bool:
        deadline = self._clock() + max(0.0, seconds)
        while self._clock() < deadline:
            if not self._ready(run_stop):
                return False
            remaining = deadline - self._clock()
            run_stop.wait(min(0.05, max(0.0, remaining)))
        return self._ready(run_stop)

    def _timed_out(self, started: float, timeout: float) -> bool:
        return bool(timeout and self._clock() - started >= timeout)

    def _release_known_inputs(self) -> None:
        if self._keyboard_controller is None:
            return
        # Ability workers release their own keys. These defensive releases cover
        # the two current TDS ability defaults after abrupt adapter failures.
        for character in ("f", "b"):
            try:
                self._keyboard_controller.release(keyboard.KeyCode.from_char(character))
            except Exception:
                pass
