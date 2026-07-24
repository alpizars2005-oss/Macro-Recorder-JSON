"""Visible local automation engine for triggers, macros, and Commander cycles."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from pynput import mouse

from .automation_models import AutomationProfile, PixelTrigger
from .recorder import Recorder
from .screen_capture import ScreenSampler, color_matches
from .window_guard import WindowCheck, check_foreground


class MouseController(Protocol):
    position: tuple[int, int]

    def click(self, button: mouse.Button, count: int = 1) -> None: ...


@dataclass(slots=True)
class TriggerRuntime:
    matches: int = 0
    latched: bool = False
    last_fired: float = 0.0
    last_checked: float = 0.0


class AutomationEngine:
    """Coordinates all automated actions while remaining visible and stoppable."""

    def __init__(
        self,
        profile: AutomationProfile,
        *,
        profile_path: Path | None = None,
        sampler_factory: Callable[[], ScreenSampler] = ScreenSampler,
        mouse_factory: Callable[[], MouseController] = mouse.Controller,
        recorder_factory: Callable[[], Recorder] = Recorder,
        window_checker: Callable[[str], WindowCheck] = check_foreground,
        arming_delay: float = 3.0,
    ) -> None:
        self.profile = profile
        self.profile_path = profile_path
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.commander_pause = threading.Event()
        self.action_lock = threading.RLock()
        self.thread: threading.Thread | None = None
        self.commander_thread: threading.Thread | None = None
        self.active = False
        self.runs_completed = 0

        self._sampler_factory = sampler_factory
        self._mouse_factory = mouse_factory
        self._recorder_factory = recorder_factory
        self._window_checker = window_checker
        self._recorder: Recorder | None = None
        self._mouse: MouseController | None = None
        self._runtime = {trigger.name: TriggerRuntime() for trigger in profile.triggers}
        self._last_window_notice = 0.0
        self._arming_delay = max(0.0, float(arming_delay))

    def start(self) -> None:
        if self.active:
            raise RuntimeError("Automation is already running.")
        self.profile.validate_ready()
        macro_path = self.profile.resolved_macro_path(self.profile_path)
        if macro_path is not None and not macro_path.is_file():
            raise FileNotFoundError(f"Start macro not found: {macro_path}")

        self.stop_event.clear()
        self.commander_pause.clear()
        self.active = True
        self.runs_completed = 0
        self._runtime = {trigger.name: TriggerRuntime() for trigger in self.profile.triggers}
        self.thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="automation-engine",
        )
        self.thread.start()

    def request_stop(self) -> None:
        self.stop_event.set()
        self.commander_pause.set()
        if self._recorder is not None:
            self._recorder.request_stop()
        self.messages.put(("stopping", None))

    def _worker(self) -> None:
        sampler: ScreenSampler | None = None
        try:
            self._mouse = self._mouse_factory()
            self._recorder = self._recorder_factory()
            sampler = self._sampler_factory()
            self.messages.put(("started", None))

            if not self._wait_with_countdown(self._arming_delay, "arming_countdown"):
                return

            if self.profile.run_macro_on_start and not self._run_start_macro():
                return

            if self.profile.commander.enabled:
                self.commander_thread = threading.Thread(
                    target=self._commander_worker,
                    daemon=True,
                    name="commander-chain",
                )
                self.commander_thread.start()

            enabled_triggers = [trigger for trigger in self.profile.triggers if trigger.enabled]
            if enabled_triggers:
                self._watch_triggers(sampler, enabled_triggers)
            else:
                self.stop_event.wait()
        except Exception as exc:
            self.messages.put(("error", str(exc)))
            self.stop_event.set()
        finally:
            self.commander_pause.set()
            if self._recorder is not None:
                self._recorder.request_stop()
            if self.commander_thread is not None and self.commander_thread.is_alive():
                self.commander_thread.join(timeout=2.0)
            if sampler is not None:
                sampler.close()
            self.active = False
            self.messages.put(("stopped", self.runs_completed))

    def _wait_with_countdown(self, seconds: float, message_name: str) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        previous: int | None = None
        while not self.stop_event.is_set():
            remaining = max(0.0, deadline - time.monotonic())
            rounded = int(remaining + 0.999)
            if rounded != previous:
                self.messages.put((message_name, rounded))
                previous = rounded
            if remaining <= 0:
                return True
            self.stop_event.wait(min(0.1, remaining))
        return False

    def _watch_triggers(self, sampler: ScreenSampler, triggers: list[PixelTrigger]) -> None:
        while not self.stop_event.is_set():
            now = time.monotonic()
            next_wait = 0.25
            for trigger in triggers:
                runtime = self._runtime[trigger.name]
                due_in = trigger.poll_interval - (now - runtime.last_checked)
                if due_in > 0:
                    next_wait = min(next_wait, due_in)
                    continue
                runtime.last_checked = now
                next_wait = min(next_wait, trigger.poll_interval)

                assert trigger.sample_point is not None
                assert trigger.target_color is not None
                sample = sampler.sample(trigger.sample_point, trigger.sample_radius)
                matched = color_matches(sample.color, trigger.target_color, trigger.tolerance)
                self.messages.put(("trigger_sample", (trigger.name, sample.color, matched)))

                if not matched:
                    runtime.matches = 0
                    runtime.latched = False
                    continue
                if runtime.latched:
                    continue

                runtime.matches += 1
                if runtime.matches < trigger.required_matches:
                    continue
                if now - runtime.last_fired < trigger.cooldown:
                    continue
                if not self._window_is_allowed():
                    runtime.matches = 0
                    continue
                if not self._revalidate_trigger(sampler, trigger):
                    runtime.matches = 0
                    continue

                runtime.latched = True
                runtime.matches = 0
                runtime.last_fired = time.monotonic()
                if not self._handle_trigger(trigger):
                    return

            self.stop_event.wait(max(0.01, next_wait))

    def _revalidate_trigger(self, sampler: ScreenSampler, trigger: PixelTrigger) -> bool:
        assert trigger.sample_point is not None
        assert trigger.target_color is not None
        sample = sampler.sample(trigger.sample_point, trigger.sample_radius)
        return color_matches(sample.color, trigger.target_color, trigger.tolerance)

    def _handle_trigger(self, trigger: PixelTrigger) -> bool:
        assert trigger.click_point is not None
        assert self._mouse is not None
        self.commander_pause.set()
        self.messages.put(("triggered", trigger.name))

        with self.action_lock:
            if self.stop_event.is_set() or not self._window_is_allowed():
                return not self.stop_event.is_set()
            self._mouse.position = (trigger.click_point.x, trigger.click_point.y)
            self._mouse.click(mouse.Button.left, 1)

        self.runs_completed += 1
        self.messages.put(("trigger_clicked", (trigger.name, self.runs_completed)))

        if not self._wait_with_countdown(self.profile.load_delay, "load_countdown"):
            return False
        if self.profile.start_macro and not self._run_start_macro():
            return False

        if self.profile.max_runs and self.runs_completed >= self.profile.max_runs:
            self.messages.put(("max_runs_reached", self.runs_completed))
            self.stop_event.set()
            return False

        self.commander_pause.clear()
        return True

    def _run_start_macro(self) -> bool:
        assert self._recorder is not None
        macro_path = self.profile.resolved_macro_path(self.profile_path)
        if macro_path is None:
            return True
        self.commander_pause.set()
        self.messages.put(("macro_loading", str(macro_path)))

        if not self._wait_for_allowed_window():
            return False

        with self.action_lock:
            if self.stop_event.is_set() or not self._window_is_allowed():
                return False
            try:
                self._recorder.load(macro_path)
                self._recorder.play(speed=1.0, delay=0.0)
            except Exception as exc:
                self.messages.put(("error", f"Could not run the start macro: {exc}"))
                self.stop_event.set()
                return False

            self.messages.put(("macro_started", str(macro_path)))
            macro_error: str | None = None
            while self._recorder.playing and not self.stop_event.is_set():
                macro_error = self._drain_recorder_messages(macro_error)
                if not self._window_is_allowed():
                    self._recorder.request_stop()
                    macro_error = "Macro stopped because the allowed window lost focus."
                    break
                self.stop_event.wait(0.05)
            if self.stop_event.is_set():
                self._recorder.request_stop()
            macro_error = self._drain_recorder_messages(macro_error)
            if macro_error:
                self.messages.put(("error", macro_error))
                self.stop_event.set()
                return False

        self.messages.put(("macro_finished", str(macro_path)))
        self.commander_pause.clear()
        return not self.stop_event.is_set()

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

    def _commander_worker(self) -> None:
        assert self._mouse is not None
        chain = self.profile.commander
        assert chain.ability_point is not None
        commander_index = 0

        while not self.stop_event.is_set():
            if self.commander_pause.is_set():
                self.stop_event.wait(0.1)
                continue
            if not self._window_is_allowed():
                self.stop_event.wait(0.35)
                continue

            point = chain.commander_points[commander_index]
            with self.action_lock:
                if self.stop_event.is_set() or self.commander_pause.is_set():
                    continue
                if not self._window_is_allowed():
                    continue
                self._mouse.position = (point.x, point.y)
                self._mouse.click(mouse.Button.left, 1)
                if self.stop_event.wait(chain.click_delay):
                    return
                if self.commander_pause.is_set() or not self._window_is_allowed():
                    continue
                self._mouse.position = (chain.ability_point.x, chain.ability_point.y)
                self._mouse.click(mouse.Button.left, 1)

            self.messages.put(("commander_activated", commander_index + 1))
            commander_index = (commander_index + 1) % len(chain.commander_points)
            wait_time = chain.interval_seconds
            if commander_index == 0:
                wait_time += chain.cycle_pause
            if self.stop_event.wait(wait_time):
                return

    def _wait_for_allowed_window(self) -> bool:
        while not self.stop_event.is_set():
            if self._window_is_allowed():
                return True
            self.stop_event.wait(0.2)
        return False

    def _window_is_allowed(self) -> bool:
        check = self._window_checker(self.profile.window_title_contains)
        if check.allowed:
            return True
        now = time.monotonic()
        if now - self._last_window_notice >= 2.0:
            self.messages.put(("window_blocked", (check.title, check.supported)))
            self._last_window_notice = now
        return False
