"""Keyboard and mouse capture/playback backend powered by pynput."""

from __future__ import annotations

import json
import os
import queue
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from pynput import keyboard, mouse

from .constants import MAX_MACRO_FILE_BYTES, MOUSE_SAMPLE_INTERVALS_MS, STOP_KEY_NAME
from .model import MacroDocument, MacroEvent, optimize_mouse_moves, validate_payload

STOP_KEY = keyboard.Key.f12


class Recorder:
    """Capture, validate, save, load, and replay macro events."""

    def __init__(self) -> None:
        self.events: list[MacroEvent] = []
        self.recording = False
        self.playing = False
        self.record_moves = True
        self.record_text = False
        self.mouse_sample_mode = "balanced"
        self.started_at = 0.0
        self.last_move = 0.0
        self.keyboard_listener: keyboard.Listener | None = None
        self.mouse_listener: mouse.Listener | None = None
        self.stop_playback = threading.Event()
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.lock = threading.RLock()
        self.loaded_screen: dict[str, int | None] | None = None

    @property
    def sample_interval_seconds(self) -> float:
        return MOUSE_SAMPLE_INTERVALS_MS.get(self.mouse_sample_mode, 33) / 1000.0

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.started_at, 6)

    def append(self, event_type: str, data: dict[str, Any]) -> None:
        if not self.recording or self.playing:
            return
        with self.lock:
            self.events.append(MacroEvent(self.elapsed(), event_type, data))
            count = len(self.events)
        self.messages.put(("count", count))

    @staticmethod
    def key_to_json(key: keyboard.Key | keyboard.KeyCode) -> dict[str, str]:
        if isinstance(key, keyboard.KeyCode):
            if key.char is not None:
                return {"kind": "char", "value": key.char}
            if key.vk is not None:
                return {"kind": "vk", "value": str(key.vk)}
        name = str(key)
        if name.startswith("Key."):
            name = name[4:]
        return {"kind": "special", "value": name}

    @staticmethod
    def json_to_key(data: dict[str, str]) -> keyboard.Key | keyboard.KeyCode:
        kind = data["kind"]
        value = data["value"]
        if kind == "char":
            return keyboard.KeyCode.from_char(value)
        if kind == "vk":
            return keyboard.KeyCode.from_vk(int(value))
        if kind == "special":
            try:
                return getattr(keyboard.Key, value)
            except AttributeError as exc:
                raise ValueError(f"Unsupported special key: {value}") from exc
        raise ValueError(f"Invalid key data: {data}")

    @staticmethod
    def button_name(button: mouse.Button) -> str:
        return str(button).split(".")[-1]

    @staticmethod
    def name_button(name: str) -> mouse.Button:
        try:
            return getattr(mouse.Button, name)
        except AttributeError as exc:
            raise ValueError(f"Unsupported mouse button: {name}") from exc

    def on_press(self, key: keyboard.Key | keyboard.KeyCode, *_args: Any) -> None:
        if key == STOP_KEY:
            self.messages.put(("stop", None))
            return
        data = self.key_to_json(key)
        if data["kind"] == "char" and not self.record_text:
            return
        self.append("key_down", {"key": data})

    def on_release(self, key: keyboard.Key | keyboard.KeyCode, *_args: Any) -> None:
        if key == STOP_KEY:
            return
        data = self.key_to_json(key)
        if data["kind"] == "char" and not self.record_text:
            return
        self.append("key_up", {"key": data})

    def on_move(self, x: int, y: int, *_args: Any) -> None:
        if not self.record_moves:
            return
        now = time.perf_counter()
        if now - self.last_move < self.sample_interval_seconds:
            return
        self.last_move = now
        self.append("mouse_move", {"x": int(x), "y": int(y)})

    def on_click(
        self,
        x: int,
        y: int,
        button: mouse.Button,
        pressed: bool,
        *_args: Any,
    ) -> None:
        self.append(
            "mouse_button",
            {
                "x": int(x),
                "y": int(y),
                "button": self.button_name(button),
                "pressed": bool(pressed),
            },
        )

    def on_scroll(self, x: int, y: int, dx: int, dy: int, *_args: Any) -> None:
        self.append(
            "mouse_scroll",
            {"x": int(x), "y": int(y), "dx": int(dx), "dy": int(dy)},
        )

    def start(self, record_moves: bool, record_text: bool, sample_mode: str) -> None:
        if self.recording or self.playing:
            raise RuntimeError("The recorder is busy.")

        with self.lock:
            self.events = []
        self.loaded_screen = None
        self.record_moves = record_moves
        self.record_text = record_text
        self.mouse_sample_mode = sample_mode
        self.started_at = time.perf_counter()
        self.last_move = 0.0
        self.recording = True

        try:
            self.keyboard_listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release,
            )
            self.mouse_listener = mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click,
                on_scroll=self.on_scroll,
            )
            self.keyboard_listener.start()
            self.mouse_listener.start()
        except Exception:
            self.recording = False
            self._stop_listeners()
            raise

        self.messages.put(("recording_started", None))

    def _stop_listeners(self) -> None:
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None

    def stop_recording(self) -> None:
        if not self.recording:
            return
        self.recording = False
        self._stop_listeners()
        self.messages.put(("recording_stopped", len(self.events)))

    def request_stop(self) -> None:
        if self.recording:
            self.stop_recording()
        if self.playing:
            self.stop_playback.set()

    def build_document(self) -> MacroDocument:
        with self.lock:
            copied = [MacroEvent(event.t, event.type, dict(event.data)) for event in self.events]
        optimized = optimize_mouse_moves(copied, self.sample_interval_seconds * 0.75)
        return MacroDocument(
            events=optimized,
            record_mouse_move=self.record_moves,
            record_printable_keys=self.record_text,
            mouse_sample_mode=self.mouse_sample_mode,
        )

    def save(self, path: Path, screen: dict[str, int | None]) -> int:
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        document = self.build_document()
        serialized = json.dumps(
            document.to_payload(screen),
            ensure_ascii=False,
            indent=2,
        ) + "\n"

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                delete=False,
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
            ) as handle:
                handle.write(serialized)
                temporary_path = Path(handle.name)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

        with self.lock:
            self.events = document.events
        self.messages.put(("count", len(document.events)))
        return len(document.events)

    def load(self, path: Path) -> None:
        if path.stat().st_size > MAX_MACRO_FILE_BYTES:
            size_mb = MAX_MACRO_FILE_BYTES // (1024 * 1024)
            raise ValueError(f"The macro file is larger than the allowed {size_mb} MB limit.")

        payload = json.loads(path.read_text(encoding="utf-8"))
        document = validate_payload(payload)
        with self.lock:
            self.events = document.events
        self.record_moves = document.record_mouse_move
        self.record_text = document.record_printable_keys
        self.mouse_sample_mode = document.mouse_sample_mode
        self.loaded_screen = document.source_screen
        self.messages.put(("count", len(self.events)))

    def play(self, speed: float, delay: float) -> None:
        if self.recording or self.playing:
            raise RuntimeError("The recorder is busy.")
        if not self.events:
            raise RuntimeError("Record or load a macro first.")
        if speed <= 0 or delay < 0:
            raise ValueError(
                "Playback speed must be greater than zero and delay cannot be negative."
            )

        self.playing = True
        self.stop_playback.clear()
        threading.Thread(
            target=self._play_worker,
            args=(speed, delay),
            daemon=True,
            name="macro-playback",
        ).start()

    def _interruptible_sleep(self, seconds: float) -> bool:
        return not self.stop_playback.wait(timeout=max(0.0, seconds))

    def _play_worker(self, speed: float, delay: float) -> None:
        keyboard_controller = keyboard.Controller()
        mouse_controller = mouse.Controller()
        pressed_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        pressed_buttons: set[mouse.Button] = set()

        try:
            self.messages.put(("countdown", delay))
            if not self._interruptible_sleep(delay):
                self.messages.put(("playback_stopped", None))
                return

            self.messages.put(("playback_started", None))
            with self.lock:
                events = [MacroEvent(event.t, event.type, dict(event.data)) for event in self.events]

            previous_timestamp = 0.0
            for index, event in enumerate(events, 1):
                event_delay = max(0.0, (event.t - previous_timestamp) / speed)
                if not self._interruptible_sleep(event_delay):
                    self.messages.put(("playback_stopped", None))
                    return
                previous_timestamp = event.t
                self.execute(
                    event,
                    keyboard_controller,
                    mouse_controller,
                    pressed_keys,
                    pressed_buttons,
                )
                self.messages.put(("progress", (index, len(events))))

            self.messages.put(("playback_finished", None))
        except Exception as exc:
            self.messages.put(("error", f"Playback failed: {exc}"))
        finally:
            self.release_held_inputs(
                keyboard_controller,
                mouse_controller,
                pressed_keys,
                pressed_buttons,
            )
            self.playing = False

    def execute(
        self,
        event: MacroEvent,
        keyboard_controller: keyboard.Controller,
        mouse_controller: mouse.Controller,
        pressed_keys: set[keyboard.Key | keyboard.KeyCode],
        pressed_buttons: set[mouse.Button],
    ) -> None:
        data = event.data
        if event.type == "key_down":
            key = self.json_to_key(data["key"])
            if str(key).removeprefix("Key.") == STOP_KEY_NAME:
                raise ValueError("F12 is reserved for the emergency stop.")
            keyboard_controller.press(key)
            pressed_keys.add(key)
        elif event.type == "key_up":
            key = self.json_to_key(data["key"])
            keyboard_controller.release(key)
            pressed_keys.discard(key)
        elif event.type == "mouse_move":
            mouse_controller.position = (data["x"], data["y"])
        elif event.type == "mouse_button":
            mouse_controller.position = (data["x"], data["y"])
            button = self.name_button(data["button"])
            if data["pressed"]:
                mouse_controller.press(button)
                pressed_buttons.add(button)
            else:
                mouse_controller.release(button)
                pressed_buttons.discard(button)
        elif event.type == "mouse_scroll":
            mouse_controller.position = (data["x"], data["y"])
            mouse_controller.scroll(data["dx"], data["dy"])
        else:
            raise ValueError(f"Unknown event type: {event.type}")

    @staticmethod
    def release_held_inputs(
        keyboard_controller: keyboard.Controller,
        mouse_controller: mouse.Controller,
        pressed_keys: set[keyboard.Key | keyboard.KeyCode],
        pressed_buttons: set[mouse.Button],
    ) -> None:
        for key in list(pressed_keys):
            try:
                keyboard_controller.release(key)
            except Exception:
                pass
        for button in list(pressed_buttons):
            try:
                mouse_controller.release(button)
            except Exception:
                pass
