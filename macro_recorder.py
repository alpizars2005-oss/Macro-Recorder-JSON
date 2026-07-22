"""Visible, local-only keyboard and mouse macro recorder for Windows.

The application records user-authorized input events, stores them as JSON,
and replays them through a Tkinter desktop interface.
"""

from __future__ import annotations

import ctypes
import json
import os
import queue
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from pynput import keyboard, mouse

APP_NAME = "Macro Recorder JSON"
APP_VERSION = "1.1.0"
SCHEMA_VERSION = 1
STOP_KEY = keyboard.Key.f12
SUPPORTED_EVENT_TYPES = {
    "key_down",
    "key_up",
    "mouse_move",
    "mouse_button",
    "mouse_scroll",
}


@dataclass(slots=True)
class MacroEvent:
    """One timestamped keyboard or mouse event."""

    t: float
    type: str
    data: dict[str, Any]


def enable_dpi_awareness() -> None:
    """Improve coordinate accuracy on scaled Windows displays."""

    if os.name != "nt":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def get_virtual_screen_metadata() -> dict[str, int | None]:
    """Return the virtual desktop bounds used by Windows mouse coordinates."""

    if os.name != "nt":
        return {"x": None, "y": None, "width": None, "height": None}

    try:
        user32 = ctypes.windll.user32
        return {
            "x": int(user32.GetSystemMetrics(76)),
            "y": int(user32.GetSystemMetrics(77)),
            "width": int(user32.GetSystemMetrics(78)),
            "height": int(user32.GetSystemMetrics(79)),
        }
    except (AttributeError, OSError):
        return {"x": None, "y": None, "width": None, "height": None}


class Recorder:
    """Capture, validate, save, load, and replay macro events."""

    def __init__(self) -> None:
        self.events: list[MacroEvent] = []
        self.recording = False
        self.playing = False
        self.record_moves = True
        self.record_text = False
        self.started_at = 0.0
        self.last_move = 0.0
        self.keyboard_listener: keyboard.Listener | None = None
        self.mouse_listener: mouse.Listener | None = None
        self.stop_playback = threading.Event()
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.lock = threading.Lock()

    def elapsed(self) -> float:
        """Return seconds elapsed since recording began."""

        return round(time.perf_counter() - self.started_at, 6)

    def append(self, event_type: str, data: dict[str, Any]) -> None:
        """Append an event when recording is active."""

        if not self.recording or self.playing:
            return

        with self.lock:
            self.events.append(MacroEvent(self.elapsed(), event_type, data))
            count = len(self.events)
        self.messages.put(("count", count))

    @staticmethod
    def key_to_json(key: keyboard.Key | keyboard.KeyCode) -> dict[str, str]:
        """Convert a pynput key to a JSON-safe representation."""

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
        """Convert JSON key data back to a pynput key."""

        kind = data.get("kind")
        value = data.get("value", "")

        if kind == "char":
            if len(value) != 1:
                raise ValueError("Printable key values must contain one character.")
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
        """Convert a pynput mouse button to its short name."""

        return str(button).split(".")[-1]

    @staticmethod
    def name_button(name: str) -> mouse.Button:
        """Convert a short mouse-button name to a pynput button."""

        try:
            return getattr(mouse.Button, name)
        except AttributeError as exc:
            raise ValueError(f"Unsupported mouse button: {name}") from exc

    def on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle a keyboard press during recording."""

        if key == STOP_KEY:
            self.messages.put(("stop", None))
            return

        data = self.key_to_json(key)
        if data["kind"] == "char" and not self.record_text:
            return
        self.append("key_down", {"key": data})

    def on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle a keyboard release during recording."""

        if key == STOP_KEY:
            return

        data = self.key_to_json(key)
        if data["kind"] == "char" and not self.record_text:
            return
        self.append("key_up", {"key": data})

    def on_move(self, x: int, y: int) -> None:
        """Handle rate-limited mouse movement during recording."""

        if not self.record_moves:
            return

        now = time.perf_counter()
        if now - self.last_move < 0.03:
            return

        self.last_move = now
        self.append("mouse_move", {"x": int(x), "y": int(y)})

    def on_click(
        self,
        x: int,
        y: int,
        button: mouse.Button,
        pressed: bool,
    ) -> None:
        """Handle a mouse-button press or release during recording."""

        self.append(
            "mouse_button",
            {
                "x": int(x),
                "y": int(y),
                "button": self.button_name(button),
                "pressed": bool(pressed),
            },
        )

    def on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Handle mouse-wheel movement during recording."""

        self.append(
            "mouse_scroll",
            {
                "x": int(x),
                "y": int(y),
                "dx": int(dx),
                "dy": int(dy),
            },
        )

    def start(self, record_moves: bool, record_text: bool) -> None:
        """Start a fresh recording session."""

        if self.recording or self.playing:
            raise RuntimeError("The recorder is busy.")

        self.events = []
        self.record_moves = record_moves
        self.record_text = record_text
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
            if self.keyboard_listener is not None:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            if self.mouse_listener is not None:
                self.mouse_listener.stop()
                self.mouse_listener = None
            raise

        self.messages.put(("recording_started", None))

    def stop_recording(self) -> None:
        """Stop listeners and finish the active recording."""

        if not self.recording:
            return

        self.recording = False

        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        if self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None

        self.messages.put(("recording_stopped", len(self.events)))

    def request_stop(self) -> None:
        """Request an immediate stop for recording or playback."""

        if self.recording:
            self.stop_recording()
        if self.playing:
            self.stop_playback.set()

    def build_payload(self) -> dict[str, Any]:
        """Build the serializable macro document."""

        with self.lock:
            events = [asdict(event) for event in self.events]

        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "screen": get_virtual_screen_metadata(),
            "settings": {
                "record_mouse_move": self.record_moves,
                "record_printable_keys": self.record_text,
                "emergency_stop": "F12",
            },
            "event_count": len(events),
            "events": events,
        }

    def save(self, path: Path) -> None:
        """Atomically save the current macro as UTF-8 JSON."""

        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(
            self.build_payload(),
            ensure_ascii=False,
            indent=2,
        )

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
            ) as temporary_file:
                temporary_file.write(serialized)
                temporary_file.write("\n")
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

    def load(self, path: Path) -> None:
        """Load and validate a macro JSON document."""

        payload = json.loads(path.read_text(encoding="utf-8"))
        loaded, settings = self.validate_payload(payload)

        with self.lock:
            self.events = loaded

        self.record_moves = settings["record_mouse_move"]
        self.record_text = settings["record_printable_keys"]
        self.messages.put(("count", len(self.events)))

    @classmethod
    def validate_payload(
        cls,
        payload: Any,
    ) -> tuple[list[MacroEvent], dict[str, bool]]:
        """Validate untrusted JSON before it can be replayed."""

        if not isinstance(payload, dict):
            raise ValueError("The macro file must contain a JSON object.")

        schema_version = payload.get("schema_version", 1)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema version: {schema_version}. "
                f"Expected {SCHEMA_VERSION}."
            )

        raw_events = payload.get("events")
        if not isinstance(raw_events, list):
            raise ValueError("The macro file must contain an events list.")

        declared_count = payload.get("event_count")
        if declared_count is not None:
            if isinstance(declared_count, bool) or not isinstance(declared_count, int):
                raise ValueError("event_count must be an integer.")
            if declared_count != len(raw_events):
                raise ValueError("event_count does not match the events list.")

        loaded: list[MacroEvent] = []
        previous_timestamp = 0.0

        for index, item in enumerate(raw_events):
            event = cls.validate_event(item, index)
            if event.t < previous_timestamp:
                raise ValueError("Event timestamps must be in ascending order.")
            previous_timestamp = event.t
            loaded.append(event)

        raw_settings = payload.get("settings", {})
        if not isinstance(raw_settings, dict):
            raise ValueError("settings must be a JSON object.")

        settings = {
            "record_mouse_move": cls.require_bool(
                raw_settings.get("record_mouse_move", True),
                "settings.record_mouse_move",
            ),
            "record_printable_keys": cls.require_bool(
                raw_settings.get("record_printable_keys", False),
                "settings.record_printable_keys",
            ),
        }
        return loaded, settings

    @classmethod
    def validate_event(cls, item: Any, index: int) -> MacroEvent:
        """Validate and normalize one event from a macro document."""

        label = f"events[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be a JSON object.")

        timestamp = cls.require_number(item.get("t"), f"{label}.t")
        if timestamp < 0:
            raise ValueError(f"{label}.t must be non-negative.")

        event_type = item.get("type")
        if event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"{label}.type is not supported: {event_type}")

        data = item.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"{label}.data must be a JSON object.")

        normalized: dict[str, Any]
        if event_type in {"key_down", "key_up"}:
            key_data = data.get("key")
            if not isinstance(key_data, dict):
                raise ValueError(f"{label}.data.key must be a JSON object.")
            normalized_key = {
                "kind": str(key_data.get("kind", "")),
                "value": str(key_data.get("value", "")),
            }
            resolved_key = cls.json_to_key(normalized_key)
            if resolved_key == STOP_KEY:
                raise ValueError("F12 is reserved for the emergency stop.")
            normalized = {"key": normalized_key}

        elif event_type == "mouse_move":
            normalized = {
                "x": cls.require_int(data.get("x"), f"{label}.data.x"),
                "y": cls.require_int(data.get("y"), f"{label}.data.y"),
            }

        elif event_type == "mouse_button":
            button_name = data.get("button")
            if not isinstance(button_name, str):
                raise ValueError(f"{label}.data.button must be a string.")
            cls.name_button(button_name)
            normalized = {
                "x": cls.require_int(data.get("x"), f"{label}.data.x"),
                "y": cls.require_int(data.get("y"), f"{label}.data.y"),
                "button": button_name,
                "pressed": cls.require_bool(
                    data.get("pressed"),
                    f"{label}.data.pressed",
                ),
            }

        else:
            normalized = {
                "x": cls.require_int(data.get("x"), f"{label}.data.x"),
                "y": cls.require_int(data.get("y"), f"{label}.data.y"),
                "dx": cls.require_int(data.get("dx"), f"{label}.data.dx"),
                "dy": cls.require_int(data.get("dy"), f"{label}.data.dy"),
            }

        return MacroEvent(timestamp, event_type, normalized)

    @staticmethod
    def require_number(value: Any, field: str) -> float:
        """Require a finite integer or float and return it as a float."""

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be a number.")
        result = float(value)
        if result != result or result in {float("inf"), float("-inf")}:
            raise ValueError(f"{field} must be finite.")
        return result

    @staticmethod
    def require_int(value: Any, field: str) -> int:
        """Require a JSON integer."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} must be an integer.")
        return value

    @staticmethod
    def require_bool(value: Any, field: str) -> bool:
        """Require a JSON boolean."""

        if not isinstance(value, bool):
            raise ValueError(f"{field} must be a boolean.")
        return value

    def play(self, speed: float, delay: float) -> None:
        """Start playback in a daemon worker thread."""

        if self.recording or self.playing:
            raise RuntimeError("The recorder is busy.")
        if not self.events:
            raise RuntimeError("Record or load a macro first.")
        if speed <= 0 or delay < 0:
            raise ValueError("Playback speed must be greater than zero and delay cannot be negative.")

        self.playing = True
        self.stop_playback.clear()
        threading.Thread(
            target=self._play_worker,
            args=(speed, delay),
            daemon=True,
            name="macro-playback",
        ).start()

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep in short intervals so emergency stop remains responsive."""

        return not self.stop_playback.wait(timeout=max(0.0, seconds))

    def _play_worker(self, speed: float, delay: float) -> None:
        """Replay events while reporting progress to the UI thread."""

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
                events = list(self.events)

            previous_timestamp = 0.0
            for index, event in enumerate(events, 1):
                event_delay = max(
                    0.0,
                    (event.t - previous_timestamp) / speed,
                )
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
        """Execute one validated macro event."""

        data = event.data

        if event.type == "key_down":
            key = self.json_to_key(data["key"])
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
        """Release inputs still held when playback stops or fails."""

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


class App(tk.Tk):
    """Tkinter interface for the macro recorder."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("780x620")
        self.minsize(700, 540)

        self.recorder = Recorder()
        self.global_stop_listener: keyboard.Listener | None = None
        self.record_moves = tk.BooleanVar(value=True)
        self.record_text = tk.BooleanVar(value=False)
        self.keep_on_top = tk.BooleanVar(value=True)
        self.speed = tk.StringVar(value="1.0")
        self.delay = tk.StringVar(value="3.0")
        self.status = tk.StringVar(value="Ready")
        self.count = tk.StringVar(value="Events: 0")
        self.filename = tk.StringVar(value="No file selected")

        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.build_ui()
        self.apply_topmost()
        self.start_global_stop_listener()
        self.after(100, self.process_messages)

    def build_ui(self) -> None:
        """Create and arrange all interface widgets."""

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text=APP_NAME,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            root,
            text=(
                "Visible, local-only keyboard and mouse macro recorder. "
                "Press F12 to stop immediately."
            ),
            wraplength=720,
        ).pack(anchor="w", pady=(4, 12))

        privacy = ttk.LabelFrame(root, text="Privacy", padding=10)
        privacy.pack(fill="x", pady=(0, 12))
        ttk.Label(
            privacy,
            text=(
                "Printable-key recording is disabled by default. Do not record "
                "passwords, banking details, private chats, or other sensitive "
                "information. Macro data is not transmitted by the application."
            ),
            wraplength=700,
        ).pack(anchor="w")

        options = ttk.LabelFrame(root, text="Recording options", padding=10)
        options.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(
            options,
            text="Record mouse movement",
            variable=self.record_moves,
        ).grid(row=0, column=0, sticky="w", padx=(0, 24), pady=4)
        ttk.Checkbutton(
            options,
            text="Record printable keys (typed text)",
            variable=self.record_text,
        ).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(
            options,
            text="Keep window on top",
            variable=self.keep_on_top,
            command=self.apply_topmost,
        ).grid(row=1, column=0, sticky="w", pady=4)

        controls = ttk.LabelFrame(root, text="Controls", padding=10)
        controls.pack(fill="x", pady=(0, 12))

        self.record_button = ttk.Button(
            controls,
            text="Start recording",
            command=self.toggle_recording,
        )
        self.record_button.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text="Play macro",
            command=self.play_macro,
        ).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text="Emergency stop (F12)",
            command=self.emergency_stop,
        ).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text="Save JSON",
            command=self.save_json,
        ).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text="Load JSON",
            command=self.load_json,
        ).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text="Clear",
            command=self.clear_macro,
        ).grid(row=1, column=2, padx=4, pady=4, sticky="ew")

        for column in range(3):
            controls.columnconfigure(column, weight=1)

        playback = ttk.LabelFrame(root, text="Playback", padding=10)
        playback.pack(fill="x", pady=(0, 12))
        ttk.Label(playback, text="Speed:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            playback,
            textvariable=self.speed,
            values=("0.25", "0.5", "1.0", "1.5", "2.0", "3.0"),
            width=8,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", padx=(6, 22))
        ttk.Label(playback, text="Start delay (seconds):").grid(
            row=0,
            column=2,
            sticky="w",
        )
        ttk.Entry(
            playback,
            textvariable=self.delay,
            width=8,
        ).grid(row=0, column=3, sticky="w", padx=6)

        status_box = ttk.LabelFrame(root, text="Status", padding=10)
        status_box.pack(fill="both", expand=True)
        ttk.Label(
            status_box,
            textvariable=self.status,
            font=("Segoe UI", 12, "bold"),
            wraplength=700,
        ).pack(anchor="w")
        ttk.Label(
            status_box,
            textvariable=self.count,
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            status_box,
            textvariable=self.filename,
            wraplength=700,
        ).pack(anchor="w", pady=(4, 8))

        self.progress = ttk.Progressbar(status_box, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))
        self.log = tk.Text(
            status_box,
            height=8,
            state="disabled",
            wrap="word",
        )
        self.log.pack(fill="both", expand=True)
        self.add_log("Application started.")
        self.add_log("Press F12 at any time to stop recording or playback.")

    def start_global_stop_listener(self) -> None:
        """Listen only for F12 while playback is active."""

        try:
            self.global_stop_listener = keyboard.Listener(
                on_press=self.on_global_key_press,
            )
            self.global_stop_listener.start()
        except Exception as exc:
            self.global_stop_listener = None
            self.add_log(
                "Global F12 listener is unavailable. "
                f"Use the Emergency stop button instead: {exc}"
            )

    def on_global_key_press(
        self,
        key: keyboard.Key | keyboard.KeyCode,
    ) -> None:
        """Request playback stop when the physical F12 key is pressed."""

        if key == STOP_KEY and self.recorder.playing:
            self.recorder.messages.put(("stop", None))

    def apply_topmost(self) -> None:
        """Apply the current always-on-top preference."""

        self.attributes("-topmost", self.keep_on_top.get())

    def add_log(self, text: str) -> None:
        """Append a timestamped line to the interface log."""

        self.log.configure(state="normal")
        self.log.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def toggle_recording(self) -> None:
        """Start or stop recording from the main button."""

        if self.recorder.recording:
            self.recorder.stop_recording()
            return

        if self.recorder.playing:
            messagebox.showwarning(APP_NAME, "Stop playback first.")
            return

        if self.recorder.events and not messagebox.askyesno(
            "Start new recording",
            "Starting a new recording clears the current macro. Continue?",
        ):
            return

        if self.record_text.get() and not messagebox.askyesno(
            "Typed text recording",
            (
                "This option may capture everything you type while recording. "
                "Do not type passwords or sensitive information. Continue?"
            ),
        ):
            return

        try:
            self.recorder.start(
                self.record_moves.get(),
                self.record_text.get(),
            )
            self.filename.set("Unsaved recording")
            self.progress["value"] = 0
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not start recording:\n{exc}")

    def emergency_stop(self) -> None:
        """Request an immediate stop from the UI or F12 listener."""

        if not self.recorder.recording and not self.recorder.playing:
            self.status.set("Ready")
            return

        self.recorder.request_stop()
        self.status.set("Stop requested")
        self.add_log("Emergency stop requested.")

    def play_macro(self) -> None:
        """Validate options and start playback."""

        try:
            speed = float(self.speed.get())
            delay = float(self.delay.get())
        except ValueError:
            messagebox.showerror(
                APP_NAME,
                "Speed and delay must be valid numbers.",
            )
            return

        if speed <= 0 or delay < 0:
            messagebox.showerror(
                APP_NAME,
                "Speed must be greater than zero and delay cannot be negative.",
            )
            return

        if not self.recorder.events:
            messagebox.showinfo(APP_NAME, "Record or load a macro first.")
            return

        if not messagebox.askyesno(
            "Play macro",
            (
                f"Playback begins in {delay:g} seconds. Focus the target window. "
                "Press F12 to stop. Continue?"
            ),
        ):
            return

        try:
            self.recorder.play(speed, delay)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def save_json(self) -> None:
        """Ask for a destination and save the current macro."""

        if not self.recorder.events:
            messagebox.showinfo(APP_NAME, "There are no events to save.")
            return

        selected_path = filedialog.asksaveasfilename(
            title="Save macro",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"macro_{datetime.now():%Y%m%d_%H%M%S}.json",
        )
        if not selected_path:
            return

        try:
            path = Path(selected_path)
            self.recorder.save(path)
            self.filename.set(f"File: {path}")
            self.add_log(f"Saved {len(self.recorder.events)} events to {path}.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not save the file:\n{exc}")

    def load_json(self) -> None:
        """Ask for and load a validated macro JSON file."""

        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning(APP_NAME, "Stop recording or playback first.")
            return

        selected_path = filedialog.askopenfilename(
            title="Load macro",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not selected_path:
            return

        try:
            path = Path(selected_path)
            self.recorder.load(path)
            self.record_moves.set(self.recorder.record_moves)
            self.record_text.set(self.recorder.record_text)
            self.filename.set(f"File: {path}")
            self.progress["value"] = 0
            self.add_log(f"Loaded {len(self.recorder.events)} events from {path}.")
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
            messagebox.showerror(APP_NAME, f"Could not load the file:\n{exc}")

    def clear_macro(self) -> None:
        """Clear events from memory after confirmation."""

        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning(APP_NAME, "Stop recording or playback first.")
            return

        if self.recorder.events and messagebox.askyesno(
            APP_NAME,
            "Delete all recorded events from memory?",
        ):
            with self.recorder.lock:
                self.recorder.events.clear()
            self.filename.set("No file selected")
            self.count.set("Events: 0")
            self.progress["value"] = 0
            self.status.set("Ready")
            self.add_log("Macro cleared.")

    def process_messages(self) -> None:
        """Process recorder messages on the Tkinter main thread."""

        try:
            while True:
                name, value = self.recorder.messages.get_nowait()

                if name == "stop":
                    self.emergency_stop()
                elif name == "count":
                    self.count.set(f"Events: {value}")
                elif name == "recording_started":
                    self.record_button.configure(text="Stop recording")
                    self.status.set("RECORDING — press F12 to stop")
                    self.add_log("Recording started.")
                elif name == "recording_stopped":
                    self.record_button.configure(text="Start recording")
                    self.status.set(f"Recording stopped — {value} events")
                    self.add_log(f"Recording stopped with {value} events.")
                elif name == "countdown":
                    self.progress["value"] = 0
                    self.status.set(
                        f"Playback begins in {float(value):g} seconds"
                    )
                    self.add_log("Playback countdown started.")
                elif name == "playback_started":
                    self.status.set("PLAYING — press F12 to stop")
                    self.add_log("Playback started.")
                elif name == "progress":
                    current, total = value
                    self.progress["maximum"] = total
                    self.progress["value"] = current
                    self.status.set(f"Playing event {current} of {total}")
                elif name == "playback_finished":
                    self.status.set("Playback finished")
                    self.add_log("Playback finished.")
                elif name == "playback_stopped":
                    self.status.set("Playback stopped")
                    self.add_log("Playback stopped.")
                elif name == "error":
                    self.status.set("Error")
                    self.add_log(str(value))
                    messagebox.showerror(APP_NAME, str(value))
        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(100, self.process_messages)

    def close_app(self) -> None:
        """Stop active work and close the application safely."""

        if (
            self.recorder.recording or self.recorder.playing
        ) and not messagebox.askyesno(
            APP_NAME,
            "Stop the active operation and exit?",
        ):
            return

        self.recorder.request_stop()
        if self.global_stop_listener is not None:
            self.global_stop_listener.stop()
            self.global_stop_listener = None
        self.destroy()


def main() -> None:
    """Start the desktop application."""

    enable_dpi_awareness()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
