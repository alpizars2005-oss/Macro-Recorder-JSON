"""Engine for repeatable recorded strategies with automatic ability keys."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from pynput import keyboard, mouse

from .automation_models import PixelTrigger
from .recorder import Recorder
from .screen_capture import ScreenSampler, color_matches
from .strategy_models import KeyPulse, RecordedStrategyProfile
from .strategy_prepare import PreparationStats, prepare_recorded_strategy
from .window_guard import WindowCheck, check_foreground


class MouseController(Protocol):
    position: tuple[int, int]

    def click(self, button: mouse.Button, count: int = 1) -> None: ...


class KeyboardController(Protocol):
    def press(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...
    def release(self, key: keyboard.Key | keyboard.KeyCode) -> None: ...


@dataclass(slots=True)
class TriggerState:
    matches: int = 0
    latched: bool = False
    last_fired: float = 0.0
    last_checked: float = 0.0


class RecordedStrategyEngine:
    """Replays one cleaned human run and coordinates repeatable abilities."""

    def __init__(
        self,
        profile: RecordedStrategyProfile,
        *,
        profile_path: Path | None = None,
        recorder_factory: Callable[[], Recorder] = Recorder,
        sampler_factory: Callable[[], ScreenSampler] = ScreenSampler,
        mouse_factory: Callable[[], MouseController] = mouse.Controller,
        keyboard_factory: Callable[[], KeyboardController] = keyboard.Controller,
        window_checker: Callable[[str], WindowCheck] = check_foreground,
    ) -> None:
        self.profile = profile
        self.profile_path = profile_path
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.active = False
        self.runs_completed = 0

        self._recorder_factory = recorder_factory
        self._sampler_factory = sampler_factory
        self._mouse_factory = mouse_factory
        self._keyboard_factory = keyboard_factory
        self._window_checker = window_checker
        self._recorder: Recorder | None = None
        self._last_window_notice = 0.0
        self._keyboard_lock = threading.Lock()

    def start(self) -> None:
        if self.active:
            raise RuntimeError("The recorded strategy is already running.")
        self.profile.validate_ready(profile_path=self.profile_path)
        if self.profile.max_runs == 0 and not any(
            trigger.enabled for trigger in self.profile.end_triggers
        ):
            raise ValueError("Unlimited repetition requires at least one enabled end trigger.")

        self.stop_event.clear()
        self.active = True
        self.runs_completed = 0
        self.thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="recorded-strategy",
        )
        self.thread.start()

    def request_stop(self) -> None:
        if not self.active:
            return
        self.stop_event.set()
        if self._recorder is not None:
            self._recorder.request_stop()
        self.messages.put(("stopping", None))

    def _worker(self) -> None:
        sampler: ScreenSampler | None = None
        try:
            self._recorder = self._recorder_factory()
            sampler = self._sampler_factory()
            mouse_controller = self._mouse_factory()
            keyboard_controller = self._keyboard_factory()
            self.messages.put(("started", None))

            if not self._countdown(self.profile.arming_delay, "arming"):
                return

            while not self.stop_event.is_set():
                run_number = self.runs_completed + 1
                if not self._wait_for_allowed_window():
                    return

                run_stop = threading.Event()
                ability_threads: list[threading.Thread] = []
                try:
                    stats = self._prepare_macro()
                    self.messages.put(("prepared", stats))
                    run_started = time.monotonic()
                    ability_threads = self._start_ability_workers(
                        keyboard_controller,
                        run_stop,
                        run_started,
                    )
                    if not self._play_macro(run_number):
                        return

                    self.runs_completed += 1
                    self.messages.put(("run_finished", self.runs_completed))

                    if self.profile.max_runs and self.runs_completed >= self.profile.max_runs:
                        self.messages.put(("max_runs_reached", self.runs_completed))
                        return

                    enabled_triggers = [
                        trigger for trigger in self.profile.end_triggers if trigger.enabled
                    ]
                    if not enabled_triggers:
                        self.messages.put(("one_shot_complete", self.runs_completed))
                        return

                    detected = self._wait_for_end_trigger(
                        sampler,
                        mouse_controller,
                        enabled_triggers,
                    )
                    if detected is None:
                        return
                    self.messages.put(("end_clicked", detected))
                finally:
                    run_stop.set()
                    for worker in ability_threads:
                        worker.join(timeout=1.0)

                if not self._countdown(self.profile.load_delay, "loading"):
                    return
        except Exception as exc:
            self.messages.put(("error", str(exc)))
            self.stop_event.set()
        finally:
            if self._recorder is not None:
                self._recorder.request_stop()
            if sampler is not None:
                sampler.close()
            self.active = False
            self.messages.put(("stopped", self.runs_completed))

    def _prepare_macro(self) -> PreparationStats:
        assert self._recorder is not None
        macro_path = self.profile.resolved_macro_path(self.profile_path)
        assert macro_path is not None
        self._recorder.load(macro_path)

        automatic_keys = {
            pulse.key.casefold() for pulse in self.profile.key_pulses if pulse.enabled
        }
        if self.profile.optimize_recording:
            prepared, stats = prepare_recorded_strategy(
                self._recorder.events,
                automatic_keys=automatic_keys,
            )
            self._recorder.events = prepared
            return stats

        original = len(self._recorder.events)
        return PreparationStats(
            original_events=original,
            prepared_events=original,
            removed_idle_mouse_moves=0,
            removed_ability_key_events=0,
            collapsed_repeated_key_down=0,
            removed_orphan_key_up=0,
            added_key_releases=0,
        )

    def _play_macro(self, run_number: int) -> bool:
        assert self._recorder is not None
        self.messages.put(("macro_started", run_number))
        self._recorder.play(speed=1.0, delay=0.0)
        error: str | None = None

        while self._recorder.playing and not self.stop_event.is_set():
            error = self._drain_recorder_messages(error)
            if not self._window_allowed():
                self._recorder.request_stop()
                error = "The strategy stopped because the allowed window lost focus."
                break
            self.stop_event.wait(0.05)

        if self.stop_event.is_set():
            self._recorder.request_stop()
            return False
        error = self._drain_recorder_messages(error)
        if error:
            self.messages.put(("error", error))
            self.stop_event.set()
            return False
        return True

    def _drain_recorder_messages(self, current_error: str | None) -> str | None:
        assert self._recorder is not None
        error = current_error
        while True:
            try:
                name, value = self._recorder.messages.get_nowait()
            except queue.Empty:
                break
            if name == "error":
                error = str(value)
            elif name == "progress":
                self.messages.put(("macro_progress", value))
        return error

    def _start_ability_workers(
        self,
        keyboard_controller: KeyboardController,
        run_stop: threading.Event,
        run_started: float,
    ) -> list[threading.Thread]:
        workers: list[threading.Thread] = []
        for pulse in self.profile.key_pulses:
            if not pulse.enabled:
                continue
            worker = threading.Thread(
                target=self._ability_worker,
                args=(pulse, keyboard_controller, run_stop, run_started),
                daemon=True,
                name=f"ability-{pulse.key.casefold()}",
            )
            worker.start()
            workers.append(worker)
        return workers

    def _ability_worker(
        self,
        pulse: KeyPulse,
        controller: KeyboardController,
        run_stop: threading.Event,
        run_started: float,
    ) -> None:
        deadline = run_started + pulse.start_after_seconds
        if not self._wait_until(deadline, run_stop):
            return

        key = keyboard.KeyCode.from_char(pulse.key)
        while not self.stop_event.is_set() and not run_stop.is_set():
            if not self._window_allowed():
                if self._wait_run(0.25, run_stop):
                    continue
                return

            pressed = False
            try:
                with self._keyboard_lock:
                    if self.stop_event.is_set() or run_stop.is_set():
                        return
                    controller.press(key)
                    pressed = True
                    if not self._wait_run(pulse.press_duration, run_stop):
                        return
                    controller.release(key)
                    pressed = False
                self.messages.put(("ability_pressed", (pulse.name, pulse.key.upper())))
            finally:
                if pressed:
                    try:
                        controller.release(key)
                    except Exception:
                        pass

            if not self._wait_run(pulse.interval_seconds, run_stop):
                return

    def _wait_for_end_trigger(
        self,
        sampler: ScreenSampler,
        mouse_controller: MouseController,
        triggers: list[PixelTrigger],
    ) -> str | None:
        runtime = {trigger.name: TriggerState() for trigger in triggers}
        self.messages.put(("waiting_for_end", None))

        while not self.stop_event.is_set():
            now = time.monotonic()
            next_wait = 0.25
            for trigger in triggers:
                state = runtime[trigger.name]
                due = trigger.poll_interval - (now - state.last_checked)
                if due > 0:
                    next_wait = min(next_wait, due)
                    continue
                state.last_checked = now
                next_wait = min(next_wait, trigger.poll_interval)

                assert trigger.sample_point is not None
                assert trigger.target_color is not None
                sample = sampler.sample(trigger.sample_point, trigger.sample_radius)
                matched = color_matches(sample.color, trigger.target_color, trigger.tolerance)
                if not matched:
                    state.matches = 0
                    state.latched = False
                    continue
                if state.latched:
                    continue

                state.matches += 1
                if state.matches < trigger.required_matches:
                    continue
                if now - state.last_fired < trigger.cooldown:
                    continue
                if not self._window_allowed():
                    state.matches = 0
                    continue

                confirm = sampler.sample(trigger.sample_point, trigger.sample_radius)
                if not color_matches(confirm.color, trigger.target_color, trigger.tolerance):
                    state.matches = 0
                    continue

                assert trigger.click_point is not None
                state.latched = True
                state.last_fired = time.monotonic()
                mouse_controller.position = (trigger.click_point.x, trigger.click_point.y)
                mouse_controller.click(mouse.Button.left, 1)
                return trigger.name

            self.stop_event.wait(max(0.01, next_wait))
        return None

    def _countdown(self, seconds: float, message: str) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        previous: int | None = None
        while not self.stop_event.is_set():
            remaining = max(0.0, deadline - time.monotonic())
            rounded = int(remaining + 0.999)
            if rounded != previous:
                self.messages.put((message, rounded))
                previous = rounded
            if remaining <= 0:
                return True
            self.stop_event.wait(min(0.1, remaining))
        return False

    def _wait_until(self, deadline: float, run_stop: threading.Event) -> bool:
        while not self.stop_event.is_set() and not run_stop.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            if not self._wait_run(min(0.1, remaining), run_stop):
                return False
        return False

    def _wait_run(self, seconds: float, run_stop: threading.Event) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        while not self.stop_event.is_set() and not run_stop.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            self.stop_event.wait(min(0.05, remaining))
        return False

    def _wait_for_allowed_window(self) -> bool:
        while not self.stop_event.is_set():
            if self._window_allowed():
                return True
            self.stop_event.wait(0.2)
        return False

    def _window_allowed(self) -> bool:
        check = self._window_checker(self.profile.window_title_contains)
        if check.allowed:
            return True
        now = time.monotonic()
        if now - self._last_window_notice >= 2.0:
            self.messages.put(("window_blocked", (check.title, check.supported)))
            self._last_window_notice = now
        return False
