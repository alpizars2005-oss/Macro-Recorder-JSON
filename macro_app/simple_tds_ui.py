"""Simple front end for reusing an older TDS recording safely."""

from __future__ import annotations

import queue
import subprocess
import sys
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from pynput import keyboard

from .legacy_tds_import import (
    LegacyMacroReport,
    analyze_legacy_macro,
    build_recorded_profile,
    save_migration_report,
)
from .paths import DEFAULT_MACRO_DIRECTORY, PROJECT_ROOT, STRATEGY_DIRECTORY
from .settings import AppSettings
from .strategy_engine import RecordedStrategyEngine
from .strategy_models import RecordedStrategyProfile, save_strategy_profile


TEXT = {
    "es": {
        "title": "TDS Macro — modo simple",
        "subtitle": "Reutiliza tu grabación anterior y deja las opciones técnicas en segundo plano.",
        "safety": "Mantén Roblox al frente durante la ejecución. F12 detiene todo.",
        "choose": "1. Elegir macro anterior",
        "start": "2. Iniciar una run",
        "stop": "Detener (F12)",
        "calibrate": "Calibrar TDS",
        "advanced": "Opciones avanzadas",
        "none": "Todavía no has elegido una macro.",
        "ready": "Lista para una prueba supervisada.",
        "running": "Ejecutando. Cambia a Roblox antes de que termine la cuenta regresiva.",
        "stopping": "Deteniendo…",
        "stopped": "Detenida.",
        "finished": "Run terminada.",
        "confirm": "Se reproducirá la grabación anterior con F y B automáticas. Usa la misma configuración de pantalla y mantén F12 listo. ¿Continuar?",
        "selected": "Macro importada: {name}\nDuración: {minutes:.1f} min · Eventos: {events}\nIntentos detectados: {attempts}\n{summary}\nPerfil y reporte guardados en: {folder}",
        "error": "Error",
        "warning": "Aviso",
        "screen": "La macro fue grabada para {w} × {h}; la pantalla actual reporta {cw} × {ch}. ¿Ejecutarla de todas formas?",
        "ability": "{name}: {key}",
        "prepared": "Preparada: {prepared}/{original} eventos.",
        "profile_saved": "Se creó automáticamente un perfil híbrido usando los tiempos de la grabación.",
    },
    "en": {
        "title": "TDS Macro — simple mode",
        "subtitle": "Reuse the earlier recording while keeping technical options in the background.",
        "safety": "Keep Roblox in front during playback. F12 stops everything.",
        "choose": "1. Choose earlier macro",
        "start": "2. Start one run",
        "stop": "Stop (F12)",
        "calibrate": "Calibrate TDS",
        "advanced": "Advanced options",
        "none": "No macro has been selected yet.",
        "ready": "Ready for one supervised test.",
        "running": "Running. Switch to Roblox before the countdown ends.",
        "stopping": "Stopping…",
        "stopped": "Stopped.",
        "finished": "Run finished.",
        "confirm": "The earlier recording will play with automatic F and B. Keep the same display setup and have F12 ready. Continue?",
        "selected": "Imported macro: {name}\nDuration: {minutes:.1f} min · Events: {events}\nDetected attempts: {attempts}\n{summary}\nProfile and report saved in: {folder}",
        "error": "Error",
        "warning": "Warning",
        "screen": "The macro was recorded for {w} × {h}; the current screen reports {cw} × {ch}. Run it anyway?",
        "ability": "{name}: {key}",
        "prepared": "Prepared: {prepared}/{original} events.",
        "profile_saved": "A hybrid profile was created automatically from the recording timings.",
    },
}


class SimpleTDSApp(tk.Tk):
    """A five-control interface over the existing recorded strategy engine."""

    def __init__(self, settings: AppSettings, translator: Any, _platform: Any = None) -> None:
        super().__init__()
        self.settings = settings
        self.translator = translator
        self.profile: RecordedStrategyProfile | None = None
        self.profile_path: Path | None = None
        self.report: LegacyMacroReport | None = None
        self.engine: RecordedStrategyEngine | None = None
        self.stop_listener: keyboard.Listener | None = None

        self.status_var = tk.StringVar(value=self.t("none"))
        self.details_var = tk.StringVar(value="")

        self.title(self.t("title"))
        self.geometry("650x500")
        self.minsize(590, 440)
        self.configure(background="#f5f7fb")
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self._style()
        self._build_ui()
        self._start_stop_listener()
        self.after(100, self._poll)

    def t(self, key: str, **values: object) -> str:
        language = self.translator.language if self.translator.language in TEXT else "en"
        return TEXT[language].get(key, TEXT["en"].get(key, key)).format(**values)

    def _style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Root.TFrame", background="#f5f7fb")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Title.TLabel", background="#f5f7fb", font=("Segoe UI", 22, "bold"))
        style.configure("Sub.TLabel", background="#f5f7fb", foreground="#475569")
        style.configure("Safe.TLabel", background="#dbeafe", foreground="#1e3a5f", padding=10)
        style.configure("Card.TLabel", background="#ffffff", foreground="#334155")
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=11)
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=9)
        style.configure("TButton", padding=9)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=18)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text=self.t("title"), style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text=self.t("subtitle"), style="Sub.TLabel").pack(anchor="w", pady=(2, 12))
        ttk.Label(root, text=self.t("safety"), style="Safe.TLabel").pack(fill="x", pady=(0, 14))

        card = ttk.Frame(root, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True)

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.pack(fill="x")
        ttk.Button(buttons, text=self.t("choose"), command=self.choose_macro, style="Primary.TButton").pack(fill="x")
        self.start_button = ttk.Button(
            buttons,
            text=self.t("start"),
            command=self.start_run,
            style="Primary.TButton",
            state="disabled",
        )
        self.start_button.pack(fill="x", pady=(10, 0))
        self.stop_button = ttk.Button(
            buttons,
            text=self.t("stop"),
            command=self.stop_run,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_button.pack(fill="x", pady=(10, 0))

        tools = ttk.Frame(card, style="Card.TFrame")
        tools.pack(fill="x", pady=(14, 0))
        ttk.Button(tools, text=self.t("calibrate"), command=lambda: self._launch("--visual-calibration")).pack(side="left", expand=True, fill="x")
        ttk.Button(tools, text=self.t("advanced"), command=lambda: self._launch("--strategy")).pack(side="left", expand=True, fill="x", padx=(10, 0))

        ttk.Separator(card).pack(fill="x", pady=14)
        ttk.Label(card, textvariable=self.status_var, style="Card.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(
            card,
            textvariable=self.details_var,
            style="Card.TLabel",
            justify="left",
            wraplength=570,
        ).pack(anchor="w", fill="x", pady=(8, 0))

    def choose_macro(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self,
            initialdir=DEFAULT_MACRO_DIRECTORY,
            filetypes=(("Macro JSON", "*.json"), ("All files", "*.*")),
        )
        if not selected:
            return
        try:
            macro_path = Path(selected).resolve()
            report = analyze_legacy_macro(macro_path)
            profile = build_recorded_profile(macro_path, report)
            STRATEGY_DIRECTORY.mkdir(parents=True, exist_ok=True)
            safe_stem = "".join(character if character.isalnum() or character in "-_" else "_" for character in macro_path.stem)
            profile_path = STRATEGY_DIRECTORY / f"{safe_stem}.hybrid.strategy.json"
            report_path = STRATEGY_DIRECTORY / f"{safe_stem}.migration-report.json"
            save_strategy_profile(profile_path, profile)
            save_migration_report(report_path, report)
        except Exception as exc:
            messagebox.showerror(self.t("error"), str(exc), parent=self)
            return

        self.profile = profile
        self.profile_path = profile_path
        self.report = report
        tower_counts = Counter(item.tower for item in report.placement_attempts)
        summary = " · ".join(f"{name}: {count}" for name, count in tower_counts.items())
        self.status_var.set(self.t("ready"))
        self.details_var.set(
            self.t(
                "selected",
                name=macro_path.name,
                minutes=report.duration_seconds / 60.0,
                events=report.event_count,
                attempts=len(report.placement_attempts),
                summary=summary,
                folder=STRATEGY_DIRECTORY,
            )
        )
        self.start_button.configure(state="normal")

    def start_run(self) -> None:
        if self.engine is not None and self.engine.active:
            return
        if self.profile is None:
            return
        current_width = self.winfo_screenwidth()
        current_height = self.winfo_screenheight()
        if (
            current_width != self.profile.required_screen_width
            or current_height != self.profile.required_screen_height
        ):
            proceed = messagebox.askyesno(
                self.t("warning"),
                self.t(
                    "screen",
                    w=self.profile.required_screen_width,
                    h=self.profile.required_screen_height,
                    cw=current_width,
                    ch=current_height,
                ),
                parent=self,
            )
            if not proceed:
                return
        if not messagebox.askyesno(self.t("warning"), self.t("confirm"), parent=self):
            return
        try:
            self.engine = RecordedStrategyEngine(self.profile, profile_path=self.profile_path)
            self.engine.start()
        except Exception as exc:
            messagebox.showerror(self.t("error"), str(exc), parent=self)
            self.engine = None
            return
        self.status_var.set(self.t("running"))
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def stop_run(self) -> None:
        if self.engine is not None:
            self.engine.request_stop()
            self.status_var.set(self.t("stopping"))

    def _start_stop_listener(self) -> None:
        def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
            if key == keyboard.Key.f12:
                self.after(0, self.stop_run)

        self.stop_listener = keyboard.Listener(on_press=on_press)
        self.stop_listener.daemon = True
        self.stop_listener.start()

    def _poll(self) -> None:
        engine = self.engine
        if engine is not None:
            while True:
                try:
                    name, value = engine.messages.get_nowait()
                except queue.Empty:
                    break
                if name == "prepared":
                    self.status_var.set(
                        self.t(
                            "prepared",
                            prepared=value.prepared_events,
                            original=value.original_events,
                        )
                    )
                elif name == "ability_pressed":
                    ability_name, key = value
                    self.status_var.set(self.t("ability", name=ability_name, key=key))
                elif name == "macro_finished":
                    self.status_var.set(self.t("finished"))
                elif name == "error":
                    self.status_var.set(str(value))
                elif name == "stopped":
                    self.status_var.set(self.t("stopped"))
                    self.start_button.configure(state="normal" if self.profile else "disabled")
                    self.stop_button.configure(state="disabled")
            if not engine.active and self.stop_button.instate(["!disabled"]):
                self.stop_button.configure(state="disabled")
                self.start_button.configure(state="normal" if self.profile else "disabled")
        self.after(100, self._poll)

    def _launch(self, flag: str) -> None:
        language = self.translator.language if self.translator.language in {"en", "es"} else "en"
        if getattr(sys, "frozen", False):
            command = [sys.executable, flag, "--language", language]
        else:
            command = [sys.executable, str(PROJECT_ROOT / "macro_recorder.py"), flag, "--language", language]
        try:
            subprocess.Popen(command, cwd=PROJECT_ROOT)
        except OSError as exc:
            messagebox.showerror(self.t("error"), str(exc), parent=self)

    def close_app(self) -> None:
        if self.engine is not None and self.engine.active:
            self.engine.request_stop()
        if self.stop_listener is not None:
            self.stop_listener.stop()
        self.destroy()
