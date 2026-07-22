"""Bilingual Tkinter desktop interface."""

from __future__ import annotations

import json
import queue
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from pynput import keyboard

from .constants import APP_NAME, APP_VERSION
from .i18n import Translator
from .platform_support import PlatformStatus, detect_platform_status
from .recorder import Recorder, STOP_KEY
from .settings import AppSettings, save_settings


class App(tk.Tk):
    """Main application window."""

    def __init__(
        self,
        settings: AppSettings,
        translator: Translator,
        platform_status: PlatformStatus | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.translator = translator
        self.platform_status = platform_status or detect_platform_status()
        self.recorder = Recorder()
        self.global_stop_listener: keyboard.Listener | None = None
        self.log_entries: list[tuple[str, str]] = []

        self.record_moves_var = tk.BooleanVar(value=settings.record_mouse_move)
        self.record_text_var = tk.BooleanVar(value=False)
        self.keep_top_var = tk.BooleanVar(value=settings.keep_on_top)
        self.speed_var = tk.StringVar(value=f"{settings.playback_speed:g}")
        self.delay_var = tk.StringVar(value=f"{settings.playback_delay:g}")
        self.sample_mode_var = tk.StringVar(value=settings.mouse_sample_mode)
        self.language_var = tk.StringVar(value=translator.language_label(translator.language))
        self.status_var = tk.StringVar(value=self.t("ready"))
        self.count_var = tk.StringVar(value=self.t("events", count=0))
        self.file_var = tk.StringVar(value=self.t("no_file"))

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("860x700")
        self.minsize(760, 620)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        self._configure_style()
        self.build_ui()
        self.apply_topmost()
        self.start_global_stop_listener()
        self.after(100, self.process_messages)

    def t(self, key: str, **values: object) -> str:
        return self.translator.text(key, **values)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TButton", padding=7)
        style.configure("TLabelframe", padding=4)
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    def build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        title_box = ttk.Frame(header)
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text=f"{self.t('app_subtitle')}  •  v{APP_VERSION}",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        language_box = ttk.Frame(header)
        language_box.grid(row=0, column=1, sticky="e")
        ttk.Label(language_box, text=self.t("language")).pack(anchor="e")
        language_combo = ttk.Combobox(
            language_box,
            textvariable=self.language_var,
            values=(self.t("english"), self.t("spanish")),
            state="readonly",
            width=12,
        )
        language_combo.pack(anchor="e", pady=(4, 0))
        language_combo.bind("<<ComboboxSelected>>", self.change_language)

        platform_frame = ttk.LabelFrame(
            outer,
            text=self.t("platform_title"),
            padding=10,
        )
        platform_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(
            platform_frame,
            text=self._platform_message(),
            wraplength=800,
        ).pack(anchor="w")

        privacy = ttk.LabelFrame(outer, text=self.t("privacy_title"), padding=10)
        privacy.pack(fill="x", pady=(0, 12))
        ttk.Label(
            privacy,
            text=self.t("privacy_text"),
            wraplength=800,
        ).pack(anchor="w")

        options = ttk.LabelFrame(outer, text=self.t("recording_options"), padding=10)
        options.pack(fill="x", pady=(0, 12))
        options.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            options,
            text=self.t("record_mouse"),
            variable=self.record_moves_var,
        ).grid(row=0, column=0, sticky="w", padx=(0, 24), pady=4)
        ttk.Checkbutton(
            options,
            text=self.t("record_text"),
            variable=self.record_text_var,
        ).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(
            options,
            text=self.t("keep_top"),
            variable=self.keep_top_var,
            command=self.apply_topmost,
        ).grid(row=1, column=0, sticky="w", pady=4)

        sample_box = ttk.Frame(options)
        sample_box.grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(sample_box, text=f"{self.t('mouse_sampling')}:").pack(side="left")
        sample_combo = ttk.Combobox(
            sample_box,
            values=(
                self.t("sampling_smooth"),
                self.t("sampling_balanced"),
                self.t("sampling_compact"),
            ),
            state="readonly",
            width=21,
        )
        sample_combo.pack(side="left", padx=(8, 0))
        sample_combo.set(self._sample_label(self.sample_mode_var.get()))
        sample_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.sample_mode_var.set(self._sample_code(sample_combo.get())),
        )

        controls = ttk.LabelFrame(outer, text=self.t("controls"), padding=10)
        controls.pack(fill="x", pady=(0, 12))

        self.record_button = ttk.Button(
            controls,
            text=self.t("start_recording"),
            command=self.toggle_recording,
            style="Accent.TButton",
        )
        self.record_button.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text=self.t("play_macro"),
            command=self.play_macro,
        ).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text=self.t("emergency_stop"),
            command=self.emergency_stop,
        ).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text=self.t("save_json"),
            command=self.save_json,
        ).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text=self.t("load_json"),
            command=self.load_json,
        ).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(
            controls,
            text=self.t("clear"),
            command=self.clear_macro,
        ).grid(row=1, column=2, padx=4, pady=4, sticky="ew")
        for column in range(3):
            controls.columnconfigure(column, weight=1)

        playback = ttk.LabelFrame(outer, text=self.t("playback"), padding=10)
        playback.pack(fill="x", pady=(0, 12))
        ttk.Label(playback, text=f"{self.t('speed')}:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            playback,
            textvariable=self.speed_var,
            values=("0.25", "0.5", "1", "1.5", "2", "3"),
            width=8,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", padx=(6, 24))
        ttk.Label(playback, text=f"{self.t('start_delay')}:").grid(
            row=0,
            column=2,
            sticky="w",
        )
        ttk.Entry(playback, textvariable=self.delay_var, width=8).grid(
            row=0,
            column=3,
            sticky="w",
            padx=6,
        )

        status_frame = ttk.LabelFrame(outer, text=self.t("status_title"), padding=10)
        status_frame.pack(fill="both", expand=True)
        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
            wraplength=800,
        ).pack(anchor="w")
        ttk.Label(status_frame, textvariable=self.count_var).pack(anchor="w", pady=(6, 0))
        ttk.Label(status_frame, textvariable=self.file_var, wraplength=800).pack(
            anchor="w",
            pady=(4, 8),
        )
        self.progress = ttk.Progressbar(status_frame, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))
        self.log = tk.Text(status_frame, height=9, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)

        if not self.log_entries:
            self.add_log(self.t("application_started"))
            self.add_log(self.t("f12_help"))
        else:
            self._render_log()

    def _platform_message(self) -> str:
        key = self.platform_status.warning_key or self.platform_status.status_key
        if key == "unsupported_os":
            return self.t(key, system=self.platform_status.system)
        return self.t(key)

    def _sample_label(self, code: str) -> str:
        return {
            "smooth": self.t("sampling_smooth"),
            "balanced": self.t("sampling_balanced"),
            "compact": self.t("sampling_compact"),
        }.get(code, self.t("sampling_balanced"))

    def _sample_code(self, label: str) -> str:
        return {
            self.t("sampling_smooth"): "smooth",
            self.t("sampling_balanced"): "balanced",
            self.t("sampling_compact"): "compact",
        }.get(label, "balanced")

    def change_language(self, _event: tk.Event[Any] | None = None) -> None:
        selected = self.language_var.get()
        language = "es" if selected == self.t("spanish") else "en"
        if language == self.translator.language:
            return
        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning(self.t("warning"), self.t("language_busy"))
            self.language_var.set(self.translator.language_label(self.translator.language))
            return

        self.translator.set_language(language)
        self.settings.language = language
        save_settings(self.settings)
        self.language_var.set(self.translator.language_label(language))
        self.status_var.set(self.t("ready"))
        self.count_var.set(self.t("events", count=len(self.recorder.events)))
        self.file_var.set(self.t("no_file"))
        self.log_entries.clear()
        self.build_ui()

    def apply_topmost(self) -> None:
        self.attributes("-topmost", self.keep_top_var.get())

    def add_log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_entries.append((timestamp, text))
        if hasattr(self, "log"):
            self.log.configure(state="normal")
            self.log.insert("end", f"[{timestamp}] {text}\n")
            self.log.see("end")
            self.log.configure(state="disabled")

    def _render_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        for timestamp, text in self.log_entries:
            self.log.insert("end", f"[{timestamp}] {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_global_stop_listener(self) -> None:
        try:
            self.global_stop_listener = keyboard.Listener(on_press=self.on_global_key_press)
            self.global_stop_listener.start()
        except Exception as exc:
            self.global_stop_listener = None
            self.add_log(self.t("global_stop_unavailable", error=exc))

    def on_global_key_press(self, key: keyboard.Key | keyboard.KeyCode, *_args: Any) -> None:
        if key == STOP_KEY and self.recorder.playing:
            self.recorder.messages.put(("stop", None))

    def toggle_recording(self) -> None:
        if self.recorder.recording:
            self.recorder.stop_recording()
            return
        if self.recorder.playing:
            messagebox.showwarning(self.t("warning"), self.t("busy_stop_first"))
            return
        if not self.platform_status.supported:
            messagebox.showerror(self.t("error"), self.t("platform_blocked"))
            return
        if self.recorder.events and not messagebox.askyesno(
            self.t("new_recording_title"),
            self.t("new_recording_warning"),
        ):
            return
        if self.record_text_var.get() and not messagebox.askyesno(
            self.t("typed_text_title"),
            self.t("typed_text_warning"),
        ):
            return

        try:
            self.recorder.start(
                self.record_moves_var.get(),
                self.record_text_var.get(),
                self.sample_mode_var.get(),
            )
            self.file_var.set(self.t("unsaved"))
            self.progress["value"] = 0
        except Exception as exc:
            messagebox.showerror(self.t("error"), self.t("cannot_start", error=exc))

    def emergency_stop(self) -> None:
        if not self.recorder.recording and not self.recorder.playing:
            self.status_var.set(self.t("ready"))
            return
        self.recorder.request_stop()
        self.status_var.set(self.t("stop_requested"))
        self.add_log(self.t("stop_requested_log"))

    def play_macro(self) -> None:
        try:
            speed = float(self.speed_var.get())
            delay = float(self.delay_var.get())
        except ValueError:
            messagebox.showerror(self.t("error"), self.t("invalid_numbers"))
            return
        if speed <= 0 or delay < 0:
            messagebox.showerror(self.t("error"), self.t("invalid_playback_values"))
            return
        if not self.recorder.events:
            messagebox.showinfo(self.t("information"), self.t("record_or_load"))
            return
        if not self.platform_status.supported:
            messagebox.showerror(self.t("error"), self.t("platform_blocked"))
            return
        if not messagebox.askyesno(
            self.t("play_title"),
            self.t("play_warning", seconds=delay),
        ):
            return
        try:
            self.recorder.play(speed, delay)
        except Exception as exc:
            messagebox.showerror(self.t("error"), str(exc))

    def save_json(self) -> None:
        if not self.recorder.events:
            messagebox.showinfo(self.t("information"), self.t("no_events_save"))
            return
        selected = filedialog.asksaveasfilename(
            title=self.t("save_title"),
            defaultextension=".json",
            filetypes=[(self.t("json_files"), "*.json")],
            initialfile=f"macro_{datetime.now():%Y%m%d_%H%M%S}.json",
        )
        if not selected:
            return
        try:
            path = Path(selected)
            count = self.recorder.save(path, self.current_screen())
            self.file_var.set(self.t("file_label", path=path))
            self.add_log(self.t("saved_log", count=count, path=path))
        except Exception as exc:
            messagebox.showerror(self.t("error"), self.t("cannot_save", error=exc))

    def load_json(self) -> None:
        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning(self.t("warning"), self.t("busy_stop_first"))
            return
        selected = filedialog.askopenfilename(
            title=self.t("load_title"),
            filetypes=[
                (self.t("json_files"), "*.json"),
                (self.t("all_files"), "*.*"),
            ],
        )
        if not selected:
            return
        try:
            path = Path(selected)
            self.recorder.load(path)
            self.record_moves_var.set(self.recorder.record_moves)
            self.record_text_var.set(False)
            self.sample_mode_var.set(self.recorder.mouse_sample_mode)
            self.file_var.set(self.t("file_label", path=path))
            self.progress["value"] = 0
            self.add_log(self.t("loaded_log", count=len(self.recorder.events), path=path))
            if self._screen_mismatch():
                self.add_log(self.t("screen_mismatch"))
                messagebox.showwarning(self.t("warning"), self.t("screen_mismatch"))
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
            messagebox.showerror(self.t("error"), self.t("cannot_load", error=exc))

    def _screen_mismatch(self) -> bool:
        source = self.recorder.loaded_screen
        if not source:
            return False
        current = self.current_screen()
        return any(
            source.get(key) is not None
            and current.get(key) is not None
            and source.get(key) != current.get(key)
            for key in ("x", "y", "width", "height")
        )

    def current_screen(self) -> dict[str, int | None]:
        try:
            return {
                "x": int(self.winfo_vrootx()),
                "y": int(self.winfo_vrooty()),
                "width": int(self.winfo_vrootwidth()),
                "height": int(self.winfo_vrootheight()),
            }
        except tk.TclError:
            return {"x": None, "y": None, "width": None, "height": None}

    def clear_macro(self) -> None:
        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning(self.t("warning"), self.t("busy_stop_first"))
            return
        if self.recorder.events and messagebox.askyesno(
            APP_NAME,
            self.t("clear_warning"),
        ):
            with self.recorder.lock:
                self.recorder.events.clear()
            self.recorder.loaded_screen = None
            self.file_var.set(self.t("no_file"))
            self.count_var.set(self.t("events", count=0))
            self.progress["value"] = 0
            self.status_var.set(self.t("ready"))
            self.add_log(self.t("cleared_log"))

    def process_messages(self) -> None:
        try:
            while True:
                name, value = self.recorder.messages.get_nowait()
                if name == "stop":
                    self.emergency_stop()
                elif name == "count":
                    self.count_var.set(self.t("events", count=value))
                elif name == "recording_started":
                    self.record_button.configure(text=self.t("stop_recording"))
                    self.status_var.set(self.t("recording_status"))
                    self.add_log(self.t("recording_started"))
                elif name == "recording_stopped":
                    self.record_button.configure(text=self.t("start_recording"))
                    self.status_var.set(self.t("recording_stopped", count=value))
                    self.add_log(self.t("recording_stopped_log", count=value))
                elif name == "countdown":
                    self.progress["value"] = 0
                    self.status_var.set(self.t("countdown", seconds=float(value)))
                    self.add_log(self.t("countdown_log"))
                elif name == "playback_started":
                    self.status_var.set(self.t("playing"))
                    self.add_log(self.t("playback_started"))
                elif name == "progress":
                    current, total = value
                    self.progress["maximum"] = total
                    self.progress["value"] = current
                    self.status_var.set(self.t("playing_event", current=current, total=total))
                elif name == "playback_finished":
                    self.status_var.set(self.t("playback_finished"))
                    self.add_log(self.t("playback_finished_log"))
                elif name == "playback_stopped":
                    self.status_var.set(self.t("playback_stopped"))
                    self.add_log(self.t("playback_stopped_log"))
                elif name == "error":
                    self.status_var.set(self.t("error"))
                    self.add_log(str(value))
                    messagebox.showerror(self.t("error"), str(value))
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self.process_messages)

    def persist_settings(self) -> None:
        try:
            speed = float(self.speed_var.get())
        except ValueError:
            speed = 1.0
        try:
            delay = float(self.delay_var.get())
        except ValueError:
            delay = 3.0
        self.settings.language = self.translator.language
        self.settings.record_mouse_move = self.record_moves_var.get()
        self.settings.keep_on_top = self.keep_top_var.get()
        self.settings.mouse_sample_mode = self.sample_mode_var.get()
        self.settings.playback_speed = min(max(speed, 0.1), 10.0)
        self.settings.playback_delay = min(max(delay, 0.0), 60.0)
        save_settings(self.settings)

    def close_app(self) -> None:
        if (self.recorder.recording or self.recorder.playing) and not messagebox.askyesno(
            APP_NAME,
            self.t("exit_warning"),
        ):
            return
        self.persist_settings()
        self.recorder.request_stop()
        if self.global_stop_listener is not None:
            self.global_stop_listener.stop()
            self.global_stop_listener = None
        self.destroy()
