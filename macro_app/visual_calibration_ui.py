"""Visible calibration wizard for private TDS pixel signatures."""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from pynput import mouse

from .client_window import check_foreground_client
from .paths import VISUAL_DIRECTORY, ensure_visual_directory
from .pixel_signatures import (
    PixelSignature,
    PixelSignatureMatcher,
    PixelSignatureSample,
    capture_signature_sample,
    load_pixel_signature,
    save_pixel_signature,
)
from .settings import AppSettings


PRESETS = (
    "camera-ready",
    "tower-panel",
    "farm-level-5",
    "insufficient-funds",
    "call-to-arms-ready",
    "drop-the-beat-ready",
    "skip-wave",
    "triumph",
    "game-over",
    "play-again",
    "restart-match",
)

TEXT = {
    "es": {
        "title": "Calibrar TDS",
        "subtitle": "Crea detectores visuales privados usando varios puntos de color dentro de Roblox.",
        "safety": "La herramienta solo toma pequeñas muestras bajo el cursor. No sube capturas ni se conecta a Internet.",
        "name": "Detector",
        "ratio": "Coincidencia mínima",
        "tolerance": "Tolerancia RGB",
        "radius": "Radio de muestra",
        "samples": "Puntos capturados",
        "capture": "Capturar punto (3 s)",
        "test": "Probar detector (3 s)",
        "remove": "Quitar seleccionado",
        "new": "Nuevo",
        "open": "Abrir",
        "save": "Guardar",
        "ready": "Listo. Elige un detector y captura al menos tres puntos estables.",
        "capture_wait": "Cambia a Roblox y coloca el cursor sobre el punto. Capturando en 3 segundos…",
        "test_wait": "Cambia a Roblox y deja visible el estado correcto. Probando en 3 segundos…",
        "foreground": "Roblox debe estar al frente al terminar la cuenta regresiva.",
        "outside": "El cursor debe estar dentro del área de Roblox.",
        "captured": "Punto capturado: ({x:.4f}, {y:.4f}) RGB {r}, {g}, {b}.",
        "tested": "Resultado: {matched} • puntuación {score:.0%} • {good}/{total} puntos.",
        "yes": "COINCIDE",
        "no": "NO COINCIDE",
        "need_samples": "Captura al menos tres puntos antes de guardar o probar.",
        "saved": "Detector guardado en:\n{path}",
        "opened": "Detector abierto desde:\n{path}",
        "invalid": "Revisa nombre, tolerancia, radio y coincidencia mínima.",
        "instructions": "Captura puntos dentro de zonas de color sólido del botón o icono. Evita letras, bordes animados y enemigos. Combina puntos del objetivo y del fondo para reducir falsos positivos.",
        "files": "Detectores de píxeles",
    },
    "en": {
        "title": "TDS Visual Calibration",
        "subtitle": "Create private visual detectors from multiple color points inside Roblox.",
        "safety": "The tool only takes tiny samples under the cursor. It does not upload screenshots or use the Internet.",
        "name": "Detector",
        "ratio": "Minimum match",
        "tolerance": "RGB tolerance",
        "radius": "Sample radius",
        "samples": "Captured points",
        "capture": "Capture point (3 s)",
        "test": "Test detector (3 s)",
        "remove": "Remove selected",
        "new": "New",
        "open": "Open",
        "save": "Save",
        "ready": "Ready. Choose a detector and capture at least three stable points.",
        "capture_wait": "Switch to Roblox and place the pointer on the point. Capturing in 3 seconds…",
        "test_wait": "Switch to Roblox and keep the correct state visible. Testing in 3 seconds…",
        "foreground": "Roblox must be in front when the countdown ends.",
        "outside": "The pointer must be inside the Roblox client area.",
        "captured": "Captured point: ({x:.4f}, {y:.4f}) RGB {r}, {g}, {b}.",
        "tested": "Result: {matched} • score {score:.0%} • {good}/{total} points.",
        "yes": "MATCH",
        "no": "NO MATCH",
        "need_samples": "Capture at least three points before saving or testing.",
        "saved": "Detector saved to:\n{path}",
        "opened": "Detector opened from:\n{path}",
        "invalid": "Check the name, tolerance, radius, and minimum match values.",
        "instructions": "Capture points inside solid-color areas of the button or icon. Avoid text, animated edges, and enemies. Mix target and background points to reduce false positives.",
        "files": "Pixel detectors",
    },
}


class VisualCalibrationApp(tk.Tk):
    def __init__(
        self,
        settings: AppSettings,
        translator: Any,
        _platform: Any = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.translator = translator
        self.language = translator.language if translator.language in TEXT else "en"
        self.samples: list[PixelSignatureSample] = []
        self.current_path: Path | None = None
        self.matcher = PixelSignatureMatcher()
        self.mouse = mouse.Controller()
        ensure_visual_directory()

        self.name_var = tk.StringVar(value=PRESETS[0])
        self.ratio_var = tk.StringVar(value="0.80")
        self.tolerance_var = tk.StringVar(value="30")
        self.radius_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value=self.t("ready"))

        self.title(self.t("title"))
        self.geometry("850x680")
        self.minsize(760, 600)
        self.configure(background="#f4f6fb")
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self._style()
        self._build_ui()

    def t(self, key: str, **values: object) -> str:
        return TEXT[self.language].get(key, key).format(**values)

    def _style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background="#f4f6fb")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Header.TLabel", background="#f4f6fb", font=("Segoe UI", 23, "bold"))
        style.configure("Sub.TLabel", background="#f4f6fb", foreground="#475569")
        style.configure("CardTitle.TLabel", background="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("CardText.TLabel", background="#ffffff", foreground="#475569")
        style.configure("Safety.TLabel", background="#dbeafe", foreground="#1e3a5f", padding=10)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TButton", padding=7)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, style="App.TFrame", padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text=self.t("title"), style="Header.TLabel").pack(anchor="w")
        ttk.Label(outer, text=self.t("subtitle"), style="Sub.TLabel").pack(anchor="w")
        ttk.Label(outer, text=self.t("safety"), style="Safety.TLabel").pack(
            fill="x", pady=(12, 12)
        )

        form = ttk.Frame(outer, style="Card.TFrame", padding=14)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text=self.t("name"), style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=5
        )
        name_box = ttk.Combobox(form, textvariable=self.name_var, values=PRESETS)
        name_box.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(form, text=self.t("ratio"), style="CardTitle.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=5
        )
        ttk.Entry(form, textvariable=self.ratio_var, width=10).grid(
            row=1, column=1, sticky="w", pady=5
        )

        controls = ttk.Frame(form, style="Card.TFrame")
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Label(controls, text=self.t("tolerance"), style="CardText.TLabel").pack(
            side="left"
        )
        ttk.Entry(controls, textvariable=self.tolerance_var, width=7).pack(
            side="left", padx=(6, 18)
        )
        ttk.Label(controls, text=self.t("radius"), style="CardText.TLabel").pack(
            side="left"
        )
        ttk.Entry(controls, textvariable=self.radius_var, width=7).pack(side="left", padx=6)

        ttk.Label(
            form,
            text=self.t("instructions"),
            style="CardText.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))

        samples_card = ttk.Frame(outer, style="Card.TFrame", padding=14)
        samples_card.pack(fill="both", expand=True, pady=12)
        ttk.Label(samples_card, text=self.t("samples"), style="CardTitle.TLabel").pack(
            anchor="w", pady=(0, 8)
        )

        list_frame = ttk.Frame(samples_card, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)
        self.sample_list = tk.Listbox(
            list_frame,
            font=("Consolas", 10),
            activestyle="none",
            selectmode="extended",
        )
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.sample_list.yview)
        self.sample_list.configure(yscrollcommand=scroll.set)
        self.sample_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        capture_row = ttk.Frame(samples_card, style="Card.TFrame")
        capture_row.pack(fill="x", pady=(10, 0))
        ttk.Button(
            capture_row,
            text=self.t("capture"),
            style="Accent.TButton",
            command=self.start_capture,
        ).pack(side="left")
        ttk.Button(capture_row, text=self.t("test"), command=self.start_test).pack(
            side="left", padx=8
        )
        ttk.Button(capture_row, text=self.t("remove"), command=self.remove_selected).pack(
            side="left"
        )

        file_row = ttk.Frame(outer, style="App.TFrame")
        file_row.pack(fill="x")
        ttk.Button(file_row, text=self.t("new"), command=self.new_signature).pack(side="left")
        ttk.Button(file_row, text=self.t("open"), command=self.open_signature).pack(
            side="left", padx=8
        )
        ttk.Button(
            file_row,
            text=self.t("save"),
            style="Accent.TButton",
            command=self.save_signature,
        ).pack(side="left")
        ttk.Label(file_row, textvariable=self.status_var, style="Sub.TLabel", wraplength=500).pack(
            side="right", anchor="e"
        )

    def start_capture(self) -> None:
        try:
            tolerance, radius, _ratio = self._validated_values(require_samples=False)
        except ValueError:
            messagebox.showerror(self.t("title"), self.t("invalid"), parent=self)
            return
        self.status_var.set(self.t("capture_wait"))
        self.iconify()
        self.after(3000, lambda: self._finish_capture(tolerance, radius))

    def _finish_capture(self, tolerance: int, radius: int) -> None:
        try:
            client = check_foreground_client("Roblox")
            if not client.ready or client.rect is None:
                raise RuntimeError(self.t("foreground"))
            sample = capture_signature_sample(
                client.rect,
                self.mouse.position,
                self.matcher.sampler,
                tolerance=tolerance,
                radius=radius,
            )
            self.samples.append(sample)
            self._refresh_samples()
            self.status_var.set(
                self.t(
                    "captured",
                    x=sample.point.x,
                    y=sample.point.y,
                    r=sample.color.r,
                    g=sample.color.g,
                    b=sample.color.b,
                )
            )
        except ValueError:
            self.status_var.set(self.t("outside"))
            messagebox.showerror(self.t("title"), self.t("outside"), parent=self)
        except Exception as exc:
            self.status_var.set(str(exc))
            messagebox.showerror(self.t("title"), str(exc), parent=self)
        finally:
            self._restore_window()

    def start_test(self) -> None:
        try:
            _tolerance, _radius, ratio = self._validated_values(require_samples=True)
            signature = PixelSignature(
                name=self.name_var.get().strip(),
                samples=tuple(self.samples),
                minimum_ratio=ratio,
            )
        except ValueError as exc:
            messagebox.showerror(
                self.t("title"),
                self.t("need_samples") if len(self.samples) < 3 else str(exc),
                parent=self,
            )
            return
        self.status_var.set(self.t("test_wait"))
        self.iconify()
        self.after(3000, lambda: self._finish_test(signature))

    def _finish_test(self, signature: PixelSignature) -> None:
        try:
            client = check_foreground_client("Roblox")
            if not client.ready or client.rect is None:
                raise RuntimeError(self.t("foreground"))
            result = self.matcher.evaluate(signature, client.rect)
            matched = self.t("yes") if result.score >= 1.0 else self.t("no")
            self.status_var.set(
                self.t(
                    "tested",
                    matched=matched,
                    score=result.score,
                    good=result.matched_samples,
                    total=result.total_samples,
                )
            )
        except Exception as exc:
            self.status_var.set(str(exc))
            messagebox.showerror(self.t("title"), str(exc), parent=self)
        finally:
            self._restore_window()

    def remove_selected(self) -> None:
        indexes = list(self.sample_list.curselection())
        for index in reversed(indexes):
            del self.samples[index]
        self._refresh_samples()

    def new_signature(self) -> None:
        self.samples.clear()
        self.current_path = None
        self.name_var.set(PRESETS[0])
        self.ratio_var.set("0.80")
        self.tolerance_var.set("30")
        self.radius_var.set("1")
        self._refresh_samples()
        self.status_var.set(self.t("ready"))

    def open_signature(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            initialdir=ensure_visual_directory(),
            title=self.t("open"),
            filetypes=((self.t("files"), "*.pixels.json"), ("JSON", "*.json")),
        )
        if not path:
            return
        try:
            signature = load_pixel_signature(Path(path))
        except Exception as exc:
            messagebox.showerror(self.t("title"), str(exc), parent=self)
            return
        self.current_path = Path(path).resolve()
        self.name_var.set(signature.name)
        self.ratio_var.set(f"{signature.minimum_ratio:.2f}")
        self.samples = list(signature.samples)
        if self.samples:
            self.tolerance_var.set(str(self.samples[0].tolerance))
            self.radius_var.set(str(self.samples[0].radius))
        self._refresh_samples()
        self.status_var.set(self.t("opened", path=self.current_path))

    def save_signature(self) -> None:
        try:
            _tolerance, _radius, ratio = self._validated_values(require_samples=True)
            signature = PixelSignature(
                name=self.name_var.get().strip(),
                samples=tuple(self.samples),
                minimum_ratio=ratio,
            )
        except ValueError as exc:
            messagebox.showerror(
                self.t("title"),
                self.t("need_samples") if len(self.samples) < 3 else str(exc),
                parent=self,
            )
            return

        default_name = self._safe_filename(signature.name) + ".pixels.json"
        path = filedialog.asksaveasfilename(
            parent=self,
            initialdir=ensure_visual_directory(),
            initialfile=self.current_path.name if self.current_path else default_name,
            defaultextension=".pixels.json",
            filetypes=((self.t("files"), "*.pixels.json"),),
        )
        if not path:
            return
        try:
            self.current_path = Path(path).resolve()
            save_pixel_signature(self.current_path, signature)
        except Exception as exc:
            messagebox.showerror(self.t("title"), str(exc), parent=self)
            return
        self.status_var.set(self.t("saved", path=self.current_path))
        messagebox.showinfo(
            self.t("title"), self.t("saved", path=self.current_path), parent=self
        )

    def _validated_values(self, *, require_samples: bool) -> tuple[int, int, float]:
        name = self.name_var.get().strip()
        if not name or len(name) > 100:
            raise ValueError("Invalid detector name.")
        tolerance = int(self.tolerance_var.get().strip())
        radius = int(self.radius_var.get().strip())
        ratio = float(self.ratio_var.get().strip())
        if not 0 <= tolerance <= 255 or not 0 <= radius <= 5 or not 0.0 <= ratio <= 1.0:
            raise ValueError("Invalid detector values.")
        if require_samples and len(self.samples) < 3:
            raise ValueError("At least three samples are required.")
        return tolerance, radius, ratio

    def _refresh_samples(self) -> None:
        self.sample_list.delete(0, tk.END)
        for index, sample in enumerate(self.samples, start=1):
            self.sample_list.insert(
                tk.END,
                (
                    f"{index:02d}  x={sample.point.x:.5f}  y={sample.point.y:.5f}  "
                    f"RGB=({sample.color.r:3d},{sample.color.g:3d},{sample.color.b:3d})  "
                    f"tol={sample.tolerance}  radius={sample.radius}"
                ),
            )

    def _restore_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
        return cleaned or "detector"

    def close_app(self) -> None:
        self.matcher.close()
        self.destroy()
