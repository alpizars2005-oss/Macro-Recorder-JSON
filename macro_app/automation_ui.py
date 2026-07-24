"""Tkinter interface for trigger-driven macro and Commander automation."""

from __future__ import annotations

import queue
import subprocess
import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from pynput import keyboard, mouse

from .automation_engine import AutomationEngine
from .automation_i18n import automation_text
from .automation_models import AutomationProfile, PixelTrigger, Point, load_profile, save_profile
from .paths import AUTOMATION_DIRECTORY, DEFAULT_MACRO_DIRECTORY, PROJECT_ROOT
from .screen_capture import ScreenSampler
from .settings import AppSettings, save_settings

STOP_KEY = keyboard.Key.f12


class AutomationStudio(tk.Tk):
    """Visible setup and status window for local automation."""

    def __init__(self, settings: AppSettings, translator: Any, _platform: Any = None) -> None:
        super().__init__()
        self.settings = settings
        self.translator = translator
        self.profile = AutomationProfile.default_tds()
        self.profile_path: Path | None = None
        self.engine: AutomationEngine | None = None
        self.stop_listener: keyboard.Listener | None = None
        self.capture_active = False
        self.log_entries: list[tuple[str, str]] = []
        self.commander_points: list[Point | None] = [None, None, None]
        self.ability_point: Point | None = None

        self.v = {
            "name": tk.StringVar(),
            "window": tk.StringVar(),
            "macro": tk.StringVar(),
            "run_macro": tk.BooleanVar(),
            "load_delay": tk.StringVar(),
            "max_runs": tk.StringVar(),
            "language": tk.StringVar(),
            "commander_enabled": tk.BooleanVar(),
            "interval": tk.StringVar(),
            "click_delay": tk.StringVar(),
            "cycle_pause": tk.StringVar(),
            "status": tk.StringVar(),
        }
        self.trigger_vars = [self._trigger_variables() for _ in range(2)]
        self.commander_summaries = [tk.StringVar() for _ in range(3)]
        self.ability_summary = tk.StringVar()

        AUTOMATION_DIRECTORY.mkdir(parents=True, exist_ok=True)
        DEFAULT_MACRO_DIRECTORY.mkdir(parents=True, exist_ok=True)
        self.geometry("1000x790")
        self.minsize(900, 690)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self._style()
        self._load_vars()
        self.build_ui()
        self._start_stop_listener()
        self.after(100, self._poll)

    def t(self, key: str, **values: object) -> str:
        return automation_text(self.translator.language, key, **values)

    @staticmethod
    def _trigger_variables() -> dict[str, tk.Variable]:
        return {
            "enabled": tk.BooleanVar(),
            "tolerance": tk.StringVar(),
            "matches": tk.StringVar(),
            "cooldown": tk.StringVar(),
            "summary": tk.StringVar(),
        }

    def _style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.configure(background="#f4f6fb")
        style.configure("App.TFrame", background="#f4f6fb")
        style.configure("Header.TLabel", background="#f4f6fb", font=("Segoe UI", 24, "bold"))
        style.configure("Sub.TLabel", background="#f4f6fb", foreground="#475569")
        style.configure("Safety.TLabel", background="#e0ecff", foreground="#1e3a5f", padding=10)
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("CardTitle.TLabel", background="#ffffff", font=("Segoe UI", 12, "bold"))
        style.configure("CardText.TLabel", background="#ffffff", foreground="#475569")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=9)
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=9)
        style.configure("TButton", padding=7)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    def build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.title(self.t("title"))
        outer = ttk.Frame(self, style="App.TFrame", padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        left = ttk.Frame(header, style="App.TFrame")
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text=self.t("title"), style="Header.TLabel").pack(anchor="w")
        ttk.Label(left, text=self.t("subtitle"), style="Sub.TLabel").pack(anchor="w")
        right = ttk.Frame(header, style="App.TFrame")
        right.grid(row=0, column=1, sticky="e")
        ttk.Label(right, text=self.t("language"), style="Sub.TLabel").pack(anchor="e")
        language = ttk.Combobox(
            right,
            textvariable=self.v["language"],
            values=("English", "Español"),
            state="readonly",
            width=12,
        )
        language.pack(pady=(4, 0))
        language.bind("<<ComboboxSelected>>", self.change_language)
        ttk.Label(
            outer,
            text=self.t("safety"),
            style="Safety.TLabel",
            wraplength=940,
        ).pack(fill="x", pady=(0, 12))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        tabs = [ttk.Frame(notebook, padding=16) for _ in range(3)]
        for tab, key in zip(tabs, ("workflow", "end_buttons", "commander")):
            notebook.add(tab, text=self.t(key))
        self._workflow_tab(tabs[0])
        self._trigger_tab(tabs[1])
        self._commander_tab(tabs[2])

        bar = ttk.Frame(outer, style="App.TFrame")
        bar.pack(fill="x", pady=(12, 8))
        profiles = ttk.LabelFrame(bar, text=self.t("profiles"), padding=6)
        profiles.pack(side="left")
        for key, command in (
            ("new_profile", self.new_profile),
            ("open_profile", self.open_profile),
            ("save_profile", self.save_profile_dialog),
        ):
            ttk.Button(profiles, text=self.t(key), command=command).pack(side="left", padx=3)
        ttk.Button(bar, text=self.t("open_recorder"), command=self.open_recorder).pack(
            side="left", padx=10
        )
        self.stop_button = ttk.Button(
            bar,
            text=self.t("stop"),
            command=self.stop_automation,
            style="Danger.TButton",
        )
        self.stop_button.pack(side="right", padx=(6, 0))
        self.start_button = ttk.Button(
            bar,
            text=self.t("start"),
            command=self.start_automation,
            style="Accent.TButton",
        )
        self.start_button.pack(side="right")

        status = ttk.LabelFrame(outer, text=self.t("status"), padding=8)
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.v["status"], font=("Segoe UI", 11, "bold")).pack(
            anchor="w"
        )
        self.log = tk.Text(status, height=5, state="disabled", wrap="word", font=("Consolas", 9))
        self.log.pack(fill="x", pady=(6, 0))
        self._render_log()
        self._running_state()

    def _workflow_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        rows = [("profile_name", "name"), ("window_guard", "window")]
        for row, (label, variable) in enumerate(rows):
            ttk.Label(tab, text=self.t(label)).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=6
            )
            ttk.Entry(tab, textvariable=self.v[variable]).grid(
                row=row, column=1, columnspan=2, sticky="ew", pady=6
            )
        ttk.Label(
            tab,
            text=self.t("window_guard_help"),
            foreground="#64748b",
            wraplength=760,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Label(tab, text=self.t("start_macro")).grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=6
        )
        ttk.Entry(tab, textvariable=self.v["macro"]).grid(row=3, column=1, sticky="ew", pady=6)
        ttk.Button(tab, text=self.t("browse"), command=self.browse_macro).grid(
            row=3, column=2, padx=(8, 0)
        )
        ttk.Checkbutton(
            tab,
            text=self.t("run_on_start"),
            variable=self.v["run_macro"],
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=8)
        for row, (label, variable) in enumerate(
            (("load_delay", "load_delay"), ("max_runs_label", "max_runs")),
            start=5,
        ):
            ttk.Label(tab, text=self.t(label)).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=6
            )
            ttk.Entry(tab, textvariable=self.v[variable], width=12).grid(
                row=row, column=1, sticky="w", pady=6
            )

    def _trigger_tab(self, tab: ttk.Frame) -> None:
        ttk.Label(
            tab,
            text=self.t("trigger_help"),
            foreground="#475569",
            wraplength=900,
        ).pack(fill="x", pady=(0, 12))
        cards = ttk.Frame(tab)
        cards.pack(fill="both", expand=True)
        for column in range(2):
            cards.columnconfigure(column, weight=1)
        for index, trigger in enumerate(self.profile.triggers[:2]):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0, 6) if index == 0 else (6, 0),
            )
            card.columnconfigure(1, weight=1)
            ttk.Label(card, text=trigger.name, style="CardTitle.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Checkbutton(
                card,
                text=self.t("enabled"),
                variable=self.trigger_vars[index]["enabled"],
            ).grid(row=0, column=1, sticky="e")
            ttk.Label(
                card,
                textvariable=self.trigger_vars[index]["summary"],
                style="CardText.TLabel",
                wraplength=390,
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=10)
            ttk.Button(
                card,
                text=self.t("capture"),
                command=lambda i=index: self.capture_trigger(i),
            ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
            for row, (key, variable) in enumerate(
                (("tolerance", "tolerance"), ("matches", "matches"), ("cooldown", "cooldown")),
                start=3,
            ):
                ttk.Label(card, text=self.t(key), style="CardText.TLabel").grid(
                    row=row, column=0, sticky="w", pady=4
                )
                ttk.Entry(
                    card,
                    textvariable=self.trigger_vars[index][variable],
                    width=10,
                ).grid(row=row, column=1, sticky="e")

    def _commander_tab(self, tab: ttk.Frame) -> None:
        ttk.Label(
            tab,
            text=self.t("commander_help"),
            foreground="#475569",
            wraplength=900,
        ).pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(
            tab,
            text=self.t("use_commander"),
            variable=self.v["commander_enabled"],
        ).pack(anchor="w", pady=(0, 10))
        points = ttk.Frame(tab)
        points.pack(fill="x")
        points.columnconfigure(1, weight=1)
        for index in range(3):
            label = self.t("commander_point", number=index + 1)
            ttk.Label(points, text=label).grid(
                row=index, column=0, sticky="w", padx=(0, 12), pady=6
            )
            ttk.Label(
                points,
                textvariable=self.commander_summaries[index],
                foreground="#475569",
            ).grid(row=index, column=1, sticky="w")
            ttk.Button(
                points,
                text=self.t("capture"),
                command=lambda i=index: self.capture_commander(i),
            ).grid(row=index, column=2, pady=6)
        ttk.Label(points, text=self.t("ability_point")).grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=6
        )
        ttk.Label(points, textvariable=self.ability_summary, foreground="#475569").grid(
            row=3, column=1, sticky="w"
        )
        ttk.Button(points, text=self.t("capture"), command=self.capture_ability).grid(
            row=3, column=2, pady=6
        )
        timing = ttk.LabelFrame(tab, text=self.t("commander"), padding=10)
        timing.pack(fill="x", pady=(14, 0))
        for row, (key, variable) in enumerate(
            (("interval", "interval"), ("click_delay", "click_delay"), ("cycle_pause", "cycle_pause"))
        ):
            ttk.Label(timing, text=self.t(key)).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=5
            )
            ttk.Entry(timing, textvariable=self.v[variable], width=12).grid(
                row=row, column=1, sticky="w"
            )

    def _load_vars(self) -> None:
        profile = self.profile
        while len(profile.triggers) < 2:
            profile.triggers.append(PixelTrigger(name="Replay" if profile.triggers else "Restart"))
        values = {
            "name": profile.name,
            "window": profile.window_title_contains,
            "macro": profile.start_macro,
            "run_macro": profile.run_macro_on_start,
            "load_delay": f"{profile.load_delay:g}",
            "max_runs": str(profile.max_runs),
            "language": "Español" if self.translator.language == "es" else "English",
            "commander_enabled": profile.commander.enabled,
            "interval": f"{profile.commander.interval_seconds:g}",
            "click_delay": f"{profile.commander.click_delay:g}",
            "cycle_pause": f"{profile.commander.cycle_pause:g}",
        }
        for key, value in values.items():
            self.v[key].set(value)
        for index, trigger in enumerate(profile.triggers[:2]):
            data = self.trigger_vars[index]
            data["enabled"].set(trigger.enabled)
            data["tolerance"].set(str(trigger.tolerance))
            data["matches"].set(str(trigger.required_matches))
            data["cooldown"].set(f"{trigger.cooldown:g}")
            data["summary"].set(self._trigger_summary(trigger))
        self.commander_points = [
            profile.commander.commander_points[index]
            if index < len(profile.commander.commander_points)
            else None
            for index in range(3)
        ]
        self.ability_point = profile.commander.ability_point
        for index, point in enumerate(self.commander_points):
            self.commander_summaries[index].set(self._point_summary(point))
        self.ability_summary.set(self._point_summary(self.ability_point))
        self.v["status"].set(self.t("ready"))

    def _collect_profile(self) -> AutomationProfile:
        profile = self.profile
        profile.name = self.v["name"].get().strip() or "TDS Commander"
        profile.window_title_contains = self.v["window"].get().strip()
        profile.start_macro = self.v["macro"].get().strip()
        profile.run_macro_on_start = bool(self.v["run_macro"].get())
        profile.load_delay = self._number("load_delay", 0, 600)
        profile.max_runs = int(self._number("max_runs", 0, 100000, integer=True))
        for index, trigger in enumerate(profile.triggers[:2]):
            data = self.trigger_vars[index]
            trigger.enabled = bool(data["enabled"].get())
            trigger.tolerance = int(
                self._number_var(data["tolerance"], 0, 255, self.t("tolerance"), True)
            )
            trigger.required_matches = int(
                self._number_var(data["matches"], 1, 20, self.t("matches"), True)
            )
            trigger.cooldown = self._number_var(
                data["cooldown"], 0, 300, self.t("cooldown")
            )
        chain = profile.commander
        chain.enabled = bool(self.v["commander_enabled"].get())
        if chain.enabled and any(point is None for point in self.commander_points):
            raise ValueError(self.t("capture_all_commanders"))
        if chain.enabled and self.ability_point is None:
            raise ValueError(self.t("capture_ability_first"))
        chain.commander_points = [point for point in self.commander_points if point is not None]
        chain.ability_point = self.ability_point
        chain.interval_seconds = self._number("interval", 0.5, 120)
        chain.click_delay = self._number("click_delay", 0.02, 5)
        chain.cycle_pause = self._number("cycle_pause", 0, 10)
        return profile

    def _number(self, key: str, minimum: float, maximum: float, integer: bool = False) -> float:
        label_key = key if key != "max_runs" else "max_runs_label"
        return self._number_var(self.v[key], minimum, maximum, self.t(label_key), integer)

    @staticmethod
    def _number_var(
        variable: tk.Variable,
        minimum: float,
        maximum: float,
        label: str,
        integer: bool = False,
    ) -> float:
        try:
            value = int(str(variable.get())) if integer else float(str(variable.get()))
        except ValueError as exc:
            raise ValueError(f"{label}: invalid number.") from exc
        if not minimum <= value <= maximum:
            raise ValueError(f"{label}: use {minimum:g} to {maximum:g}.")
        return float(value)

    def _trigger_summary(self, trigger: PixelTrigger) -> str:
        if trigger.sample_point is None or trigger.target_color is None:
            return self.t("not_captured")
        point = trigger.sample_point
        color = trigger.target_color
        return self.t(
            "captured",
            x=point.x,
            y=point.y,
            r=color.r,
            g=color.g,
            b=color.b,
        )

    def _point_summary(self, point: Point | None) -> str:
        return self.t("not_captured") if point is None else f"({point.x}, {point.y})"

    def browse_macro(self) -> None:
        selected = filedialog.askopenfilename(
            initialdir=DEFAULT_MACRO_DIRECTORY,
            filetypes=[
                (self.t("macro_files"), "*.json"),
                (self.t("all_files"), "*.*"),
            ],
        )
        if selected:
            self.v["macro"].set(selected)

    def new_profile(self) -> None:
        if self._active():
            return
        self.profile = AutomationProfile.default_tds()
        self.profile_path = None
        self.log_entries.clear()
        self._load_vars()
        self.build_ui()

    def open_profile(self) -> None:
        if self._active():
            return
        selected = filedialog.askopenfilename(
            initialdir=AUTOMATION_DIRECTORY,
            filetypes=[
                (self.t("profile_files"), "*.json"),
                (self.t("all_files"), "*.*"),
            ],
        )
        if not selected:
            return
        try:
            self.profile_path = Path(selected).resolve()
            self.profile = load_profile(self.profile_path)
            self._load_vars()
            self.build_ui()
            self.add_log(self.t("profile_opened", path=self.profile_path))
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t("error"), str(exc))

    def save_profile_dialog(self) -> None:
        try:
            profile = self._collect_profile()
        except ValueError as exc:
            messagebox.showerror(self.t("error"), str(exc))
            return
        selected = filedialog.asksaveasfilename(
            initialdir=AUTOMATION_DIRECTORY,
            initialfile=self.profile_path.name if self.profile_path else "tds_commander.json",
            defaultextension=".json",
            filetypes=[(self.t("profile_files"), "*.json")],
        )
        if not selected:
            return
        try:
            self.profile_path = Path(selected).resolve()
            save_profile(self.profile_path, profile)
            self.add_log(self.t("profile_saved", path=self.profile_path))
        except OSError as exc:
            messagebox.showerror(self.t("error"), str(exc))

    def capture_trigger(self, index: int) -> None:
        trigger = self.profile.triggers[index]

        def done(point: Point) -> None:
            try:
                with ScreenSampler() as sampler:
                    sample = sampler.sample(point, 1)
                trigger.sample_point = point
                trigger.click_point = point
                trigger.target_color = sample.color
                self.trigger_vars[index]["summary"].set(self._trigger_summary(trigger))
                self.add_log(
                    self.t("capture_done", label=trigger.name, x=point.x, y=point.y)
                )
            except Exception as exc:
                messagebox.showerror(
                    self.t("error"),
                    self.t("capture_failed", error=exc),
                )

        self._capture(done)

    def capture_commander(self, index: int) -> None:
        def done(point: Point) -> None:
            self.commander_points[index] = point
            self.commander_summaries[index].set(self._point_summary(point))
            self.add_log(
                self.t(
                    "capture_done",
                    label=self.t("commander_point", number=index + 1),
                    x=point.x,
                    y=point.y,
                )
            )

        self._capture(done)

    def capture_ability(self) -> None:
        def done(point: Point) -> None:
            self.ability_point = point
            self.ability_summary.set(self._point_summary(point))
            self.add_log(
                self.t(
                    "capture_done",
                    label=self.t("ability_point"),
                    x=point.x,
                    y=point.y,
                )
            )

        self._capture(done)

    def _capture(self, callback: Callable[[Point], None]) -> None:
        if self.capture_active or self._active():
            return
        self.capture_active = True
        self.iconify()

        def tick(seconds: int) -> None:
            if seconds:
                self.v["status"].set(self.t("capturing", seconds=seconds))
                self.after(1000, lambda: tick(seconds - 1))
                return
            try:
                x, y = mouse.Controller().position
                callback(Point(int(x), int(y)))
            finally:
                self.capture_active = False
                self.deiconify()
                self.lift()
                self.focus_force()
                self.v["status"].set(self.t("ready"))

        self.after(200, lambda: tick(3))

    def start_automation(self) -> None:
        if self._active():
            return
        try:
            profile = self._collect_profile()
            profile.validate_ready()
            macro = profile.resolved_macro_path(self.profile_path)
            if macro is not None and not macro.exists():
                raise ValueError(self.t("missing_macro"))
        except (ValueError, OSError) as exc:
            messagebox.showerror(
                self.t("error"),
                self.t("profile_invalid", error=exc),
            )
            return
        if not messagebox.askyesno(self.t("warning"), self.t("confirm_start")):
            return
        try:
            self.engine = AutomationEngine(profile, profile_path=self.profile_path)
            self.engine.start()
        except Exception as exc:
            self.engine = None
            messagebox.showerror(self.t("error"), str(exc))
            return
        self.v["status"].set(self.t("automation_started"))
        self.add_log(self.t("automation_started"))
        self._running_state()

    def stop_automation(self) -> None:
        if self._active() and self.engine is not None:
            self.engine.request_stop()
            self.v["status"].set(self.t("stopping"))

    def _poll(self) -> None:
        if self.engine is not None:
            try:
                while True:
                    self._engine_message(*self.engine.messages.get_nowait())
            except queue.Empty:
                pass
            if not self.engine.active:
                self._running_state()
        if self.winfo_exists():
            self.after(100, self._poll)

    def _engine_message(self, name: str, value: Any) -> None:
        messages = {
            "started": self.t("automation_started"),
            "stopping": self.t("stopping"),
            "macro_started": self.t("macro_started"),
            "macro_finished": self.t("macro_finished"),
            "window_blocked": self.t("window_blocked"),
        }
        message = messages.get(name)
        if name == "arming_countdown":
            message = self.t("arming", seconds=value)
        elif name == "triggered":
            message = self.t("triggered", name=value)
        elif name == "trigger_clicked":
            message = self.t("trigger_clicked", name=value[0], count=value[1])
        elif name == "load_countdown":
            message = self.t("loading", seconds=value)
        elif name == "commander_activated":
            message = self.t("commander_activated", number=value)
        elif name == "max_runs_reached":
            message = self.t("max_runs_reached", count=value)
        elif name == "stopped":
            message = self.t("stopped", count=value)
        elif name == "error":
            message = str(value)
            messagebox.showerror(self.t("error"), message)
        if message:
            self.v["status"].set(message)
            if name not in {"arming_countdown", "load_countdown", "window_blocked", "started"}:
                self.add_log(message)
        if name == "stopped":
            self._running_state()

    def add_log(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_entries.append((stamp, text))
        self.log_entries = self.log_entries[-100:]
        if hasattr(self, "log"):
            self.log.configure(state="normal")
            self.log.insert("end", f"[{stamp}] {text}\n")
            self.log.see("end")
            self.log.configure(state="disabled")

    def _render_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        for stamp, text in self.log_entries:
            self.log.insert("end", f"[{stamp}] {text}\n")
        self.log.configure(state="disabled")

    def _active(self) -> bool:
        return self.engine is not None and self.engine.active

    def _running_state(self) -> None:
        if hasattr(self, "start_button"):
            self.start_button.configure(state="disabled" if self._active() else "normal")
        if hasattr(self, "stop_button"):
            self.stop_button.configure(state="normal" if self._active() else "disabled")

    def change_language(self, _event: tk.Event[Any] | None = None) -> None:
        if self._active():
            messagebox.showwarning(self.t("warning"), self.t("busy_language"))
            self.v["language"].set(
                "Español" if self.translator.language == "es" else "English"
            )
            return
        self.translator.set_language(
            "es" if self.v["language"].get() == "Español" else "en"
        )
        self.settings.language = self.translator.language
        save_settings(self.settings)
        self._load_vars()
        self.build_ui()

    def open_recorder(self) -> None:
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "macro_recorder.py"),
                    "--language",
                    self.translator.language,
                ],
                cwd=DEFAULT_MACRO_DIRECTORY,
            )
        except OSError as exc:
            messagebox.showerror(
                self.t("error"),
                self.t("recorder_launch_failed", error=exc),
            )

    def _start_stop_listener(self) -> None:
        try:
            self.stop_listener = keyboard.Listener(on_press=self._global_key)
            self.stop_listener.start()
        except Exception as exc:
            self.add_log(str(exc))

    def _global_key(self, key: keyboard.Key | keyboard.KeyCode, *_args: Any) -> None:
        if key == STOP_KEY and self.engine is not None:
            self.engine.request_stop()

    def close_app(self) -> None:
        if self._active() and not messagebox.askyesno(
            self.t("warning"), self.t("close_running")
        ):
            return
        if self.engine is not None:
            self.engine.request_stop()
        if self.stop_listener is not None:
            self.stop_listener.stop()
        self.destroy()
