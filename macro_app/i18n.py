"""Natural English and Spanish text for the desktop interface."""

from __future__ import annotations

import locale
from dataclasses import dataclass

from .constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_subtitle": "Record and replay keyboard and mouse actions on this computer.",
        "language": "Language",
        "english": "English",
        "spanish": "Español",
        "privacy_title": "Privacy",
        "privacy_text": "Typing capture is off when the app starts. Do not record passwords, payment details, private messages, security codes, or other sensitive information.",
        "platform_title": "System",
        "platform_ready": "Keyboard and mouse control is ready.",
        "recording_options": "Recording",
        "record_mouse": "Record mouse movement",
        "record_text": "Record what I type",
        "keep_top": "Keep app on top",
        "mouse_sampling": "Mouse movement detail",
        "sampling_smooth": "High detail (16 ms)",
        "sampling_balanced": "Balanced (33 ms)",
        "sampling_compact": "Smaller files (75 ms)",
        "controls": "Actions",
        "start_recording": "Start recording",
        "stop_recording": "Stop recording",
        "play_macro": "Run macro",
        "emergency_stop": "Stop now (F12)",
        "save_json": "Save macro",
        "load_json": "Open macro",
        "clear": "Clear macro",
        "playback": "Run settings",
        "speed": "Speed",
        "start_delay": "Wait before starting (seconds)",
        "status_title": "Status",
        "ready": "Ready",
        "events": "Actions: {count}",
        "no_file": "No macro loaded",
        "unsaved": "Unsaved macro",
        "recording_status": "Recording — press F12 to stop",
        "recording_started": "Recording started.",
        "recording_stopped": "Recording stopped — {count} actions",
        "recording_stopped_log": "Recording stopped with {count} actions.",
        "countdown": "Starting in {seconds:g} seconds",
        "countdown_log": "Countdown started.",
        "playing": "Running — press F12 to stop",
        "playback_started": "Macro started.",
        "playing_event": "Action {current} of {total}",
        "playback_finished": "Macro finished",
        "playback_finished_log": "Macro finished.",
        "playback_stopped": "Macro stopped",
        "playback_stopped_log": "Macro stopped.",
        "stop_requested": "Stopping...",
        "stop_requested_log": "Stop requested.",
        "application_started": "App started.",
        "f12_help": "Press F12 anytime to stop.",
        "global_stop_unavailable": "F12 could not be enabled as a global shortcut. Use the Stop now button instead: {error}",
        "busy_stop_first": "Stop the current recording or macro first.",
        "new_recording_title": "New recording",
        "new_recording_warning": "Starting a new recording will replace the current macro. Continue?",
        "typed_text_title": "Record typing",
        "typed_text_warning": "This may record everything you type. Avoid passwords and sensitive information. Continue?",
        "cannot_start": "Could not start recording:\n{error}",
        "invalid_numbers": "Speed and wait time must be valid numbers.",
        "invalid_playback_values": "Speed must be greater than zero and wait time cannot be negative.",
        "record_or_load": "Record or open a macro first.",
        "play_title": "Run macro",
        "play_warning": "The macro will start in {seconds:g} seconds. Switch to the target window. Press F12 to stop. Continue?",
        "no_events_save": "There are no actions to save.",
        "save_title": "Save macro",
        "json_files": "JSON files",
        "all_files": "All files",
        "saved_log": "Saved a macro with {count} actions to {path}.",
        "cannot_save": "Could not save the macro:\n{error}",
        "load_title": "Open macro",
        "loaded_log": "Opened a macro with {count} actions from {path}.",
        "cannot_load": "Could not open the macro:\n{error}",
        "clear_warning": "Clear all recorded actions?",
        "cleared_log": "Macro cleared.",
        "exit_warning": "Stop and close the app?",
        "error": "Error",
        "warning": "Warning",
        "information": "Info",
        "file_label": "Macro: {path}",
        "wayland_warning": "Wayland detected. The app works best with programs running through Xwayland. Use an X11 session for full Linux support.",
        "linux_no_display": "No Linux desktop session detected. Open the app from a desktop terminal, not a headless SSH session.",
        "unsupported_os": "Unsupported system: {system}.",
        "x11_ready": "Linux detected (X11/Xwayland).",
        "windows_ready": "Windows detected.",
        "mac_experimental": "macOS support is experimental.",
        "platform_unknown": "Desktop detected. Some system details are unavailable.",
        "macro_too_large": "This macro is larger than the {size_mb} MB limit.",
        "settings_saved": "Language changed.",
        "language_busy": "Stop the current recording or macro before changing the language.",
        "platform_blocked": "Keyboard and mouse control is not available in this desktop session.",
        "screen_mismatch": "This macro was recorded with a different monitor layout. Check your monitors before running it.",
    },
    "es": {
        "app_subtitle": "Graba y repite acciones del teclado y ratón en esta computadora.",
        "language": "Idioma",
        "english": "English",
        "spanish": "Español",
        "privacy_title": "Privacidad",
        "privacy_text": "La captura de lo que escribes está desactivada al iniciar. No grabes contraseñas, datos de pago, mensajes privados, códigos de seguridad ni información sensible.",
        "platform_title": "Sistema",
        "platform_ready": "El control del teclado y ratón está listo.",
        "recording_options": "Grabación",
        "record_mouse": "Grabar movimiento del ratón",
        "record_text": "Grabar lo que escribo",
        "keep_top": "Mantener la app al frente",
        "mouse_sampling": "Detalle del movimiento",
        "sampling_smooth": "Más detalle (16 ms)",
        "sampling_balanced": "Equilibrado (33 ms)",
        "sampling_compact": "Archivos más pequeños (75 ms)",
        "controls": "Acciones",
        "start_recording": "Iniciar grabación",
        "stop_recording": "Detener grabación",
        "play_macro": "Ejecutar macro",
        "emergency_stop": "Detener ahora (F12)",
        "save_json": "Guardar macro",
        "load_json": "Abrir macro",
        "clear": "Borrar macro",
        "playback": "Opciones de ejecución",
        "speed": "Velocidad",
        "start_delay": "Espera antes de iniciar (segundos)",
        "status_title": "Estado",
        "ready": "Listo",
        "events": "Acciones: {count}",
        "no_file": "No hay una macro cargada",
        "unsaved": "Macro sin guardar",
        "recording_status": "Grabando — presiona F12 para detener",
        "recording_started": "Grabación iniciada.",
        "recording_stopped": "Grabación detenida — {count} acciones",
        "recording_stopped_log": "La grabación terminó con {count} acciones.",
        "countdown": "La macro iniciará en {seconds:g} segundos",
        "countdown_log": "Cuenta regresiva iniciada.",
        "playing": "Ejecutando — presiona F12 para detener",
        "playback_started": "Macro iniciada.",
        "playing_event": "Acción {current} de {total}",
        "playback_finished": "Macro finalizada",
        "playback_finished_log": "Macro finalizada.",
        "playback_stopped": "Macro detenida",
        "playback_stopped_log": "Macro detenida.",
        "stop_requested": "Deteniendo...",
        "stop_requested_log": "Se solicitó detener la macro.",
        "application_started": "App iniciada.",
        "f12_help": "Presiona F12 en cualquier momento para detener.",
        "global_stop_unavailable": "No se pudo activar F12 como atajo global. Usa el botón Detener ahora: {error}",
        "busy_stop_first": "Primero detén la grabación o macro actual.",
        "new_recording_title": "Nueva grabación",
        "new_recording_warning": "Al iniciar una nueva grabación se reemplazará la macro actual. ¿Continuar?",
        "typed_text_title": "Grabar lo que escribes",
        "typed_text_warning": "Esta opción puede grabar todo lo que escribas. Evita contraseñas e información sensible. ¿Continuar?",
        "cannot_start": "No se pudo iniciar la grabación:\n{error}",
        "invalid_numbers": "La velocidad y el tiempo de espera deben ser números.",
        "invalid_playback_values": "La velocidad debe ser mayor a cero y la espera no puede ser negativa.",
        "record_or_load": "Primero graba o abre una macro.",
        "play_title": "Ejecutar macro",
        "play_warning": "La macro iniciará en {seconds:g} segundos. Cambia a la ventana donde quieres ejecutarla. Presiona F12 para detener. ¿Continuar?",
        "no_events_save": "No hay acciones para guardar.",
        "save_title": "Guardar macro",
        "json_files": "Archivos JSON",
        "all_files": "Todos los archivos",
        "saved_log": "Se guardó una macro con {count} acciones en {path}.",
        "cannot_save": "No se pudo guardar la macro:\n{error}",
        "load_title": "Abrir macro",
        "loaded_log": "Se abrió una macro con {count} acciones desde {path}.",
        "cannot_load": "No se pudo abrir la macro:\n{error}",
        "clear_warning": "¿Borrar todas las acciones grabadas?",
        "cleared_log": "Macro borrada.",
        "exit_warning": "¿Detener y cerrar la app?",
        "error": "Error",
        "warning": "Aviso",
        "information": "Información",
        "file_label": "Macro: {path}",
        "wayland_warning": "Wayland detectado. La app funciona mejor con programas abiertos mediante Xwayland. Usa una sesión X11 para tener compatibilidad completa en Linux.",
        "linux_no_display": "No se detectó una sesión de escritorio en Linux. Abre la app desde una terminal del escritorio, no desde una sesión SSH sin interfaz.",
        "unsupported_os": "Sistema no compatible: {system}.",
        "x11_ready": "Linux detectado (X11/Xwayland).",
        "windows_ready": "Windows detectado.",
        "mac_experimental": "El soporte para macOS es experimental.",
        "platform_unknown": "Escritorio detectado. No se pudo obtener toda la información del sistema.",
        "macro_too_large": "Esta macro supera el límite de {size_mb} MB.",
        "settings_saved": "Idioma cambiado.",
        "language_busy": "Detén la grabación o macro actual antes de cambiar el idioma.",
        "platform_blocked": "El control del teclado y ratón no está disponible en esta sesión de escritorio.",
        "screen_mismatch": "Esta macro se grabó con una configuración de monitores diferente. Revisa tus monitores antes de ejecutarla.",
    },
}


LANGUAGE_LABELS = {
    "en": {"en": "English", "es": "Español"},
    "es": {"en": "English", "es": "Español"},
}


def normalize_language(value: str | None) -> str:
    """Normalize a language code and fall back to English."""
    if not value:
        return DEFAULT_LANGUAGE
    code = value.strip().lower().replace("_", "-").split("-", 1)[0]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def detect_system_language() -> str:
    """Choose Spanish for Spanish locales and English otherwise."""
    try:
        language, _encoding = locale.getlocale()
    except ValueError:
        language = None
    return normalize_language(language)


@dataclass(slots=True)
class Translator:
    """Small formatting-aware translation helper."""

    language: str = DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        self.language = normalize_language(self.language)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)

    def text(self, key: str, **values: object) -> str:
        template = TRANSLATIONS.get(self.language, TRANSLATIONS[DEFAULT_LANGUAGE]).get(
            key,
            TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key),
        )
        return template.format(**values)

    def language_label(self, code: str) -> str:
        return LANGUAGE_LABELS[self.language].get(code, code)
