"""Dedicated interface for repeatable recorded strategy playback."""

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

from .automation_models import PixelTrigger, Point
from .paths import DEFAULT_MACRO_DIRECTORY, PROJECT_ROOT, STRATEGY_DIRECTORY
from .screen_capture import ScreenSampler
from .settings import AppSettings, save_settings
from .strategy_engine import RecordedStrategyEngine
from .strategy_models import (
    KeyPulse,
    RecordedStrategyProfile,
    load_strategy_profile,
    save_strategy_profile,
)

STOP_KEY = keyboard.Key.f12


TEXT = {
    "es": {
        "title": "Estrategia grabada",
        "subtitle": "Reproduce la run de Wrecked Battlefield y mantiene las habilidades automáticas.",
        "safety": "Automatización visible y local. Mantén Roblox al frente y presiona F12 para detener todo.",
        "strategy": "Estrategia",
        "abilities": "Habilidades",
        "ending": "Final de partida",
        "name": "Nombre",
        "macro": "Grabación JSON",
        "browse": "Buscar…",
        "window": "Ventana permitida",
        "resolution": "Resolución requerida",
        "current_resolution": "Resolución actual: {width} × {height}",
        "arming": "Cuenta regresiva inicial (s)",
        "load": "Espera después de repetir (s)",
        "runs": "Número de runs (0 = ilimitadas)",
        "optimize": "Limpiar movimientos innecesarios y quitar F/B manuales",
        "ability_help": "Las teclas se pulsan repetidamente después del momento indicado. TDS ignora la tecla mientras la habilidad no está disponible.",
        "enabled": "Activada",
        "key": "Tecla",
        "starts": "Comenzar después de (s)",
        "interval": "Pulsar cada (s)",
        "end_help": "Captura el centro de cada botón cuando esté visible. Para una primera prueba de una sola run puedes dejarlos desactivados.",
        "capture": "Capturar bajo el cursor (3 s)",
        "not_captured": "Sin capturar",
        "captured": "Punto {x}, {y} • RGB {r}, {g}, {b}",
        "tolerance": "Tolerancia",
        "matches": "Coincidencias",
        "cooldown": "Espera entre clics (s)",
        "profiles": "Perfiles",
        "new": "Nuevo",
        "open": "Abrir",
        "save": "Guardar",
        "recorder": "Abrir grabador",
        "start": "Iniciar estrategia",
        "stop": "Detener ahora (F12)",
        "status": "Estado",
        "ready": "Listo",
        "capture_countdown": "Mueve el cursor al objetivo. Captura en {seconds}…",
        "capture_done": "Capturado {name} en ({x}, {y}).",
        "confirm": "La app reproducirá clics, teclado y cámara durante la partida. Usa solamente la misma disposición de pantalla de la grabación y mantén F12 listo. ¿Continuar?",
        "screen_warning": "La estrategia fue grabada para {required_w} × {required_h}, pero Windows reporta {current_w} × {current_h}. Los clics pueden quedar desalineados. ¿Iniciar de todas formas?",
        "started": "Estrategia iniciada. Cambia a Roblox antes de que termine la cuenta regresiva.",
        "arming_status": "Iniciando en {seconds}…",
        "prepared": "Grabación preparada: {prepared}/{original} eventos; {moves} movimientos innecesarios eliminados.",
        "macro_started": "Run {number}: reproduciendo la estrategia.",
        "ability_pressed": "{name}: tecla {key} enviada.",
        "run_finished": "Run {count} terminada. Esperando el resultado.",
        "waiting_end": "Esperando Play Again o Restart Match.",
        "end_clicked": "Se pulsó {name}.",
        "loading": "Esperando la siguiente partida: {seconds} s",
        "max_runs": "Se alcanzó el número de runs: {count}.",
        "window_blocked": "Pausado o detenido porque Roblox no está al frente.",
        "stopping": "Deteniendo…",
        "stopped": "Detenido. Runs terminadas: {count}.",
        "saved": "Perfil guardado en {path}.",
        "opened": "Perfil abierto desde {path}.",
        "error": "Error",
        "warning": "Aviso",
        "all_files": "Todos los archivos",
        "macro_files": "Macros JSON",
        "profile_files": "Perfiles de estrategia",
        "missing": "Falta seleccionar la grabación JSON.",
        "language": "Idioma",
        "busy_language": "Detén la estrategia antes de cambiar el idioma.",
        "close_running": "¿Detener la estrategia y cerrar?",
    },
    "en": {
        "title": "Recorded Strategy",
        "subtitle": "Replay the Wrecked Battlefield run and keep abilities automatic.",
        "safety": "Visible, local-only automation. Keep Roblox in front and press F12 to stop everything.",
        "strategy": "Strategy",
        "abilities": "Abilities",
        "ending": "End of match",
        "name": "Name",
        "macro": "Recorded JSON",
        "browse": "Browse…",
        "window": "Allowed window",
        "resolution": "Required resolution",
        "current_resolution": "Current resolution: {width} × {height}",
        "arming": "Initial countdown (s)",
        "load": "Wait after replay (s)",
        "runs": "Number of runs (0 = unlimited)",
        "optimize": "Remove unnecessary movement and manual F/B events",
        "ability_help": "Keys are repeated after the configured point. TDS ignores the key while the ability is unavailable.",
        "enabled": "Enabled",
        "key": "Key",
        "starts": "Start after (s)",
        "interval": "Press every (s)",
        "end_help": "Capture the center of each button while it is visible. Leave them disabled for the first one-run test.",
        "capture": "Capture under cursor (3 s)",
        "not_captured": "Not captured",
        "captured": "Point {x}, {y} • RGB {r}, {g}, {b}",
        "tolerance": "Tolerance",
        "matches": "Matches",
        "cooldown": "Click cooldown (s)",
        "profiles": "Profiles",
        "new": "New",
        "open": "Open",
        "save": "Save",
        "recorder": "Open recorder",
        "start": "Start strategy",
        "stop": "Stop now (F12)",
        "status": "Status",
        "ready": "Ready",
        "capture_countdown": "Move the cursor to the target. Capturing in {seconds}…",
        "capture_done": "Captured {name} at ({x}, {y}).",
        "confirm": "The app will replay clicks, keyboard, and camera movement. Use the same display layout as the recording and keep F12 ready. Continue?",
        "screen_warning": "This strategy was recorded for {required_w} × {required_h}, but Windows reports {current_w} × {current_h}. Clicks may be misaligned. Start anyway?",
        "started": "Strategy started. Switch to Roblox before the countdown ends.",
        "arming_status": "Starting in {seconds}…",
        "prepared": "Recording prepared: {prepared}/{original} events; {moves} unnecessary moves removed.",
        "macro_started": "Run {number}: replaying the strategy.",
        "ability_pressed": "{name}: sent key {key}.",
        "run_finished": "Run {count} finished. Waiting for the result.",
        "waiting_end": "Waiting for Play Again or Restart Match.",
        "end_clicked": "Clicked {name}.",
        "loading": "Waiting for the next match: {seconds} s",
        "max_runs": "Run limit reached: {count}.",
        "window_blocked": "Paused or stopped because Roblox is not in front.",
        "stopping": "Stopping…",
        "stopped": "Stopped. Completed runs: {count}.",
        "saved": "Profile saved to {path}.",
        "opened": "Profile opened from {path}.",
        "error": "Error",
        "warning": "Warning",
        "all_files": "All files",
        "macro_files": "Macro JSON files",
        "profile_files": "Strategy profiles",
        "missing": "Choose the recorded JSON file.",
        "language": "Language",
        "busy_language": "Stop the strategy before changing language.",
        "close_running": "Stop the strategy and close?",
    },
}


class StrategyRunner(tk.Tk):
    def __init__(self, settings: AppSettings, translator: Any, _platform: Any = None) -> None:
        super().__init__()
        self.settings = settings
        self.translator = translator
        self.profile = RecordedStrategyProfile.default_wrecked_battlefield()
        self.profile_path: Path | None = None
        self.engine: RecordedStrategyEngine | None = None
        self.stop_listener: keyboard.Listener | None = None
        self.capture_active = False
        self.log_entries: list[tuple[str, str]] = []

        STRATEGY_DIRECTORY.mkdir(parents=True, exist_ok=True)
        DEFAULT_MACRO_DIRECTORY.mkdir(parents=True, exist_ok=True)

        self.v = {
            "name": tk.StringVar(),
            "macro": tk.StringVar(),
            "window": tk.StringVar(),
            "width": tk.StringVar(),
            "height": tk.StringVar(),
            "arming": tk.StringVar(),
            "load": tk.StringVar(),
            "runs": tk.StringVar(),
            "optimize": tk.BooleanVar(),
            "status": tk.StringVar(),
            "language": tk.StringVar(),
        }
        self.pulse_vars = [self._pulse_vars() for _ in range(2)]
        self.trigger_vars = [self._trigger_vars() for _ in range(2)]

        self.geometry("980x760")
        self.minsize(880, 680)
        self.configure(background="#f4f6fb")
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self._style()
        self._load_vars()
        self.build_ui()
        self._start_stop_listener()
        self.after(100, self._poll)

    def t(self, key: str, **values: object) -> str:
        language = self.translator.language if self.translator.language in TEXT else "en"
        return TEXT[language].get(key, TEXT["en"].get(key, key)).format(**values)

    @staticmethod
    def _pulse_vars() -> dict[str, tk.Variable]:
        return {
            "enabled": tk.BooleanVar(),
            "key": tk.StringVar(),
            "start": tk.StringVar(),
            "interval": tk.StringVar(),
        }

    @staticmethod
    def _trigger_vars() -> dict[str, tk.Variable]:
        return {
            "enabled": tk.BooleanVar(),
            "summary": tk.StringVar(),
            "tolerance": tk.StringVar(),
            "matches": tk.StringVar(),
            "cooldown": tk.StringVar(),
        }

    def _style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background="#f4f6fb")
        style.configure("Header.TLabel", background="#f4f6fb", font=("Segoe UI", 24, "bold"))
        style.configure("Sub.TLabel", background="#f4f6fb", foreground="#475569")
        style.configure("Safety.TLabel", background="#dbeafe", foreground="#1e3a5f", padding=10)
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("CardTitle.TLabel", background="#ffffff", font=("Segoe UI", 12, "bold"))
        style.configure("CardText.TLabel", background="#ffffff", foreground="#475569")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=9)
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=9)
        style.configure("TButton", padding=7)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))

    def build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.title(self.t("title"))
        outer = ttk.Frame(self, style="App.TFrame", padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 10))
        left = ttk.Frame(header, style="App.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text=self.t("title"), style="Header.TLabel").pack(anchor="w")
        ttk.Label(left, text=self.t("subtitle"), style="Sub.TLabel").pack(anchor="w")
        right = ttk.Frame(header, style="App.TFrame")
        right.pack(side="right")
        ttk.Label(right, text=self.t("language"), style="Sub.TLabel").pack(anchor="e")
        language = ttk.Combobox(
            right,
            textvariable=self.v["language"],
            values=("English", "Español"),
            state="readonly",
            width=12,
        )
        language.pack(pady=(3, 0))
        language.bind("<<ComboboxSelected>>", self.change_language)

        ttk.Label(outer, text=self.t("safety"), style="Safety.TLabel").pack(fill="x", pady=(0, 10))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        strategy_tab = ttk.Frame(notebook, padding=15)
        abilities_tab = ttk.Frame(notebook, padding=15)
        ending_tab = ttk.Frame(notebook, padding=15)
        notebook.add(strategy_tab, text=self.t("strategy"))
        notebook.add(abilities_tab, text=self.t("abilities"))
        notebook.add(ending_tab, text=self.t("ending"))
        self._strategy_tab(strategy_tab)
        self._abilities_tab(abilities_tab)
        self._ending_tab(ending_tab)

        bar = ttk.Frame(outer, style="App.TFrame")
        bar.pack(fill="x", pady=(10, 7))
        profile_box = ttk.LabelFrame(bar, text=self.t("profiles"), padding=5)
        profile_box.pack(side="left")
        ttk.Button(profile_box, text=self.t("new"), command=self.new_profile).pack(side="left", padx=2)
        ttk.Button(profile_box, text=self.t("open"), command=self.open_profile).pack(side="left", padx=2)
        ttk.Button(profile_box, text=self.t("save"), command=self.save_profile_dialog).pack(side="left", padx=2)
        ttk.Button(bar, text=self.t("recorder"), command=self.open_recorder).pack(side="left", padx=9)
        self.stop_button = ttk.Button(
            bar,
            text=self.t("stop"),
            command=self.stop_strategy,
            style="Danger.TButton",
        )
        self.stop_button.pack(side="right", padx=(6, 0))
        self.start_button = ttk.Button(
            bar,
            text=self.t("start"),
            command=self.start_strategy,
            style="Accent.TButton",
        )
        self.start_button.pack(side="right")

        status = ttk.LabelFrame(outer, text=self.t("status"), padding=8)
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.v["status"], font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.log = tk.Text(status, height=5, state="disabled", wrap="word", font=("Consolas", 9))
        self.log.pack(fill="x", pady=(5, 0))
        self._render_log()
        self._running_state()

    def _strategy_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text=self.t("name")).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(tab, textvariable=self.v["name"]).grid(row=0, column=1, columnspan=2, sticky="ew", pady=6)
        ttk.Label(tab, text=self.t("macro")).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(tab, textvariable=self.v["macro"]).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(tab, text=self.t("browse"), command=self.browse_macro).grid(row=1, column=2, padx=(8, 0))
        ttk.Label(tab, text=self.t("window")).grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(tab, textvariable=self.v["window"], width=22).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(tab, text=self.t("resolution")).grid(row=3, column=0, sticky="w", padx=(0, 12), pady=6)
        resolution = ttk.Frame(tab)
        resolution.grid(row=3, column=1, sticky="w")
        ttk.Entry(resolution, textvariable=self.v["width"], width=8).pack(side="left")
        ttk.Label(resolution, text=" × ").pack(side="left")
        ttk.Entry(resolution, textvariable=self.v["height"], width=8).pack(side="left")
        ttk.Label(
            tab,
            text=self.t("current_resolution", width=self.winfo_screenwidth(), height=self.winfo_screenheight()),
            foreground="#64748b",
        ).grid(row=4, column=1, columnspan=2, sticky="w", pady=(0, 8))

        for row, (label, variable) in enumerate(
            (("arming", "arming"), ("load", "load"), ("runs", "runs")),
            start=5,
        ):
            ttk.Label(tab, text=self.t(label)).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            ttk.Entry(tab, textvariable=self.v[variable], width=12).grid(row=row, column=1, sticky="w", pady=6)
        ttk.Checkbutton(tab, text=self.t("optimize"), variable=self.v["optimize"]).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=10
        )

    def _abilities_tab(self, tab: ttk.Frame) -> None:
        ttk.Label(tab, text=self.t("ability_help"), foreground="#475569", wraplength=880).pack(fill="x", pady=(0, 12))
        cards = ttk.Frame(tab)
        cards.pack(fill="both", expand=True)
        for column in range(2):
            cards.columnconfigure(column, weight=1)
        for index, pulse in enumerate(self.profile.key_pulses[:2]):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 6) if index == 0 else (6, 0))
            card.columnconfigure(1, weight=1)
            ttk.Label(card, text=pulse.name, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Checkbutton(card, text=self.t("enabled"), variable=self.pulse_vars[index]["enabled"]).grid(
                row=0, column=1, sticky="e"
            )
            for row, (label, variable) in enumerate(
                (("key", "key"), ("starts", "start"), ("interval", "interval")),
                start=1,
            ):
                ttk.Label(card, text=self.t(label), style="CardText.TLabel").grid(
                    row=row, column=0, sticky="w", pady=8
                )
                ttk.Entry(card, textvariable=self.pulse_vars[index][variable], width=12).grid(
                    row=row, column=1, sticky="e"
                )

    def _ending_tab(self, tab: ttk.Frame) -> None:
        ttk.Label(tab, text=self.t("end_help"), foreground="#475569", wraplength=880).pack(fill="x", pady=(0, 12))
        cards = ttk.Frame(tab)
        cards.pack(fill="both", expand=True)
        for column in range(2):
            cards.columnconfigure(column, weight=1)
        for index, trigger in enumerate(self.profile.end_triggers[:2]):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 6) if index == 0 else (6, 0))
            card.columnconfigure(1, weight=1)
            ttk.Label(card, text=trigger.name, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Checkbutton(card, text=self.t("enabled"), variable=self.trigger_vars[index]["enabled"]).grid(
                row=0, column=1, sticky="e"
            )
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
            ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            for row, (label, variable) in enumerate(
                (("tolerance", "tolerance"), ("matches", "matches"), ("cooldown", "cooldown")),
                start=3,
            ):
                ttk.Label(card, text=self.t(label), style="CardText.TLabel").grid(
                    row=row, column=0, sticky="w", pady=4
                )
                ttk.Entry(card, textvariable=self.trigger_vars[index][variable], width=10).grid(
                    row=row, column=1, sticky="e"
                )

    def _load_vars(self) -> None:
        profile = self.profile
        while len(profile.key_pulses) < 2:
            profile.key_pulses.append(KeyPulse(name="Ability", key="f", enabled=False))
        while len(profile.end_triggers) < 2:
            profile.end_triggers.append(PixelTrigger(name="End", enabled=False))
        values = {
            "name": profile.name,
            "macro": profile.macro_path,
            "window": profile.window_title_contains,
            "width": str(profile.required_screen_width),
            "height": str(profile.required_screen_height),
            "arming": f"{profile.arming_delay:g}",
            "load": f"{profile.load_delay:g}",
            "runs": str(profile.max_runs),
            "optimize": profile.optimize_recording,
            "status": self.t("ready"),
            "language": "Español" if self.translator.language == "es" else "English",
        }
        for key, value in values.items():
            self.v[key].set(value)
        for index, pulse in enumerate(profile.key_pulses[:2]):
            variables = self.pulse_vars[index]
            variables["enabled"].set(pulse.enabled)
            variables["key"].set(pulse.key.upper())
            variables["start"].set(f"{pulse.start_after_seconds:g}")
            variables["interval"].set(f"{pulse.interval_seconds:g}")
        for index, trigger in enumerate(profile.end_triggers[:2]):
            variables = self.trigger_vars[index]
            variables["enabled"].set(trigger.enabled)
            variables["summary"].set(self._trigger_summary(trigger))
            variables["tolerance"].set(str(trigger.tolerance))
            variables["matches"].set(str(trigger.required_matches))
            variables["cooldown"].set(f"{trigger.cooldown:g}")

    def _collect_profile(self) -> RecordedStrategyProfile:
        profile = self.profile
        profile.name = self.v["name"].get().strip() or "Wrecked Battlefield - Molten Farm"
        profile.macro_path = self.v["macro"].get().strip()
        profile.window_title_contains = self.v["window"].get().strip()
        profile.required_screen_width = self._integer("width", 320, 100000)
        profile.required_screen_height = self._integer("height", 240, 100000)
        profile.arming_delay = self._number("arming", 0, 60)
        profile.load_delay = self._number("load", 0, 600)
        profile.max_runs = self._integer("runs", 0, 100000)
        profile.optimize_recording = bool(self.v["optimize"].get())

        for index, pulse in enumerate(profile.key_pulses[:2]):
            variables = self.pulse_vars[index]
            key = str(variables["key"].get()).strip()
            if len(key) != 1:
                raise ValueError(f"{pulse.name}: the key must contain one character.")
            pulse.enabled = bool(variables["enabled"].get())
            pulse.key = key.casefold()
            pulse.start_after_seconds = self._number_var(
                variables["start"], 0, 86400, pulse.name
            )
            pulse.interval_seconds = self._number_var(
                variables["interval"], 0.1, 300, pulse.name
            )

        for index, trigger in enumerate(profile.end_triggers[:2]):
            variables = self.trigger_vars[index]
            trigger.enabled = bool(variables["enabled"].get())
            trigger.tolerance = int(self._number_var(variables["tolerance"], 0, 255, trigger.name, True))
            trigger.required_matches = int(self._number_var(variables["matches"], 1, 20, trigger.name, True))
            trigger.cooldown = self._number_var(variables["cooldown"], 0, 300, trigger.name)
        return profile

    def _number(self, key: str, minimum: float, maximum: float) -> float:
        return self._number_var(self.v[key], minimum, maximum, key)

    def _integer(self, key: str, minimum: int, maximum: int) -> int:
        return int(self._number_var(self.v[key], minimum, maximum, key, True))

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
        return self.t("captured", x=point.x, y=point.y, r=color.r, g=color.g, b=color.b)

    def browse_macro(self) -> None:
        selected = filedialog.askopenfilename(
            initialdir=DEFAULT_MACRO_DIRECTORY,
            filetypes=[(self.t("macro_files"), "*.json"), (self.t("all_files"), "*.*")],
        )
        if selected:
            self.v["macro"].set(selected)

    def new_profile(self) -> None:
        if self._active():
            return
        self.profile = RecordedStrategyProfile.default_wrecked_battlefield()
        self.profile_path = None
        self.log_entries.clear()
        self._load_vars()
        self.build_ui()

    def open_profile(self) -> None:
        if self._active():
            return
        selected = filedialog.askopenfilename(
            initialdir=STRATEGY_DIRECTORY,
            filetypes=[(self.t("profile_files"), "*.json"), (self.t("all_files"), "*.*")],
        )
        if not selected:
            return
        try:
            self.profile_path = Path(selected).resolve()
            self.profile = load_strategy_profile(self.profile_path)
            self._load_vars()
            self.build_ui()
            self.add_log(self.t("opened", path=self.profile_path))
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t("error"), str(exc))

    def save_profile_dialog(self) -> None:
        try:
            profile = self._collect_profile()
        except ValueError as exc:
            messagebox.showerror(self.t("error"), str(exc))
            return
        selected = filedialog.asksaveasfilename(
            initialdir=STRATEGY_DIRECTORY,
            initialfile=self.profile_path.name if self.profile_path else "wrecked_battlefield_molten.json",
            defaultextension=".json",
            filetypes=[(self.t("profile_files"), "*.json")],
        )
        if not selected:
            return
        try:
            self.profile_path = Path(selected).resolve()
            save_strategy_profile(self.profile_path, profile)
            self.add_log(self.t("saved", path=self.profile_path))
        except OSError as exc:
            messagebox.showerror(self.t("error"), str(exc))

    def capture_trigger(self, index: int) -> None:
        trigger = self.profile.end_triggers[index]

        def done(point: Point) -> None:
            try:
                with ScreenSampler() as sampler:
                    sample = sampler.sample(point, 1)
                trigger.sample_point = point
                trigger.click_point = point
                trigger.target_color = sample.color
                self.trigger_vars[index]["summary"].set(self._trigger_summary(trigger))
                self.add_log(self.t("capture_done", name=trigger.name, x=point.x, y=point.y))
            except Exception as exc:
                messagebox.showerror(self.t("error"), str(exc))

        self._capture(done)

    def _capture(self, callback: Callable[[Point], None]) -> None:
        if self.capture_active or self._active():
            return
        self.capture_active = True
        self.iconify()

        def tick(seconds: int) -> None:
            if seconds:
                self.v["status"].set(self.t("capture_countdown", seconds=seconds))
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

    def start_strategy(self) -> None:
        if self._active():
            return
        try:
            profile = self._collect_profile()
            profile.validate_ready(profile_path=self.profile_path)
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t("error"), str(exc))
            return

        current_w = self.winfo_screenwidth()
        current_h = self.winfo_screenheight()
        if (current_w, current_h) != (
            profile.required_screen_width,
            profile.required_screen_height,
        ):
            if not messagebox.askyesno(
                self.t("warning"),
                self.t(
                    "screen_warning",
                    required_w=profile.required_screen_width,
                    required_h=profile.required_screen_height,
                    current_w=current_w,
                    current_h=current_h,
                ),
            ):
                return
        if not messagebox.askyesno(self.t("warning"), self.t("confirm")):
            return
        try:
            self.engine = RecordedStrategyEngine(profile, profile_path=self.profile_path)
            self.engine.start()
        except Exception as exc:
            self.engine = None
            messagebox.showerror(self.t("error"), str(exc))
            return
        self.v["status"].set(self.t("started"))
        self.add_log(self.t("started"))
        self._running_state()

    def stop_strategy(self) -> None:
        if self.engine is not None and self.engine.active:
            self.engine.request_stop()
            self.v["status"].set(self.t("stopping"))

    def _poll(self) -> None:
        if self.engine is not None:
            try:
                while True:
                    self._handle_message(*self.engine.messages.get_nowait())
            except queue.Empty:
                pass
            if not self.engine.active:
                self._running_state()
        if self.winfo_exists():
            self.after(100, self._poll)

    def _handle_message(self, name: str, value: Any) -> None:
        message: str | None = None
        if name == "arming":
            message = self.t("arming_status", seconds=value)
        elif name == "prepared":
            message = self.t(
                "prepared",
                prepared=value.prepared_events,
                original=value.original_events,
                moves=value.removed_idle_mouse_moves,
            )
        elif name == "macro_started":
            message = self.t("macro_started", number=value)
        elif name == "ability_pressed":
            message = self.t("ability_pressed", name=value[0], key=value[1])
        elif name == "run_finished":
            message = self.t("run_finished", count=value)
        elif name == "waiting_for_end":
            message = self.t("waiting_end")
        elif name == "end_clicked":
            message = self.t("end_clicked", name=value)
        elif name == "loading":
            message = self.t("loading", seconds=value)
        elif name == "max_runs_reached":
            message = self.t("max_runs", count=value)
        elif name == "window_blocked":
            message = self.t("window_blocked")
        elif name == "stopping":
            message = self.t("stopping")
        elif name == "stopped":
            message = self.t("stopped", count=value)
        elif name == "error":
            message = str(value)
            messagebox.showerror(self.t("error"), message)

        if message:
            self.v["status"].set(message)
            if name not in {"arming", "loading", "ability_pressed", "window_blocked"}:
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
            self.v["language"].set("Español" if self.translator.language == "es" else "English")
            return
        self.translator.set_language("es" if self.v["language"].get() == "Español" else "en")
        self.settings.language = self.translator.language
        save_settings(self.settings)
        self._load_vars()
        self.build_ui()

    def open_recorder(self) -> None:
        try:
            command = [sys.executable]
            if not getattr(sys, "frozen", False):
                command.append(str(PROJECT_ROOT / "macro_recorder.py"))
            command.extend(["--language", self.translator.language])
            subprocess.Popen(command, cwd=DEFAULT_MACRO_DIRECTORY)
        except OSError as exc:
            messagebox.showerror(self.t("error"), str(exc))

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
        if self._active() and not messagebox.askyesno(self.t("warning"), self.t("close_running")):
            return
        if self.engine is not None:
            self.engine.request_stop()
        if self.stop_listener is not None:
            self.stop_listener.stop()
        self.destroy()
