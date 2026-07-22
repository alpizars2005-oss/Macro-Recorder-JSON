"""English and Spanish translations for the desktop interface."""

from __future__ import annotations

import locale
from dataclasses import dataclass

from .constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_subtitle": "Visible, local-only keyboard and mouse macro recorder.",
        "language": "Language",
        "english": "English",
        "spanish": "Español",
        "privacy_title": "Privacy and safety",
        "privacy_text": "Printable-key recording is disabled by default. Do not record passwords, payment details, private chats, authentication codes, or other sensitive information.",
        "platform_title": "Platform status",
        "platform_ready": "Desktop input automation is available.",
        "recording_options": "Recording options",
        "record_mouse": "Record mouse movement",
        "record_text": "Record printable keys (typed text)",
        "keep_top": "Keep window on top",
        "mouse_sampling": "Mouse sampling",
        "sampling_smooth": "Smooth (16 ms)",
        "sampling_balanced": "Balanced (33 ms)",
        "sampling_compact": "Compact (75 ms)",
        "controls": "Controls",
        "start_recording": "Start recording",
        "stop_recording": "Stop recording",
        "play_macro": "Play macro",
        "emergency_stop": "Emergency stop (F12)",
        "save_json": "Save JSON",
        "load_json": "Load JSON",
        "clear": "Clear",
        "playback": "Playback",
        "speed": "Speed",
        "start_delay": "Start delay (seconds)",
        "status_title": "Status",
        "ready": "Ready",
        "events": "Events: {count}",
        "no_file": "No file selected",
        "unsaved": "Unsaved recording",
        "recording_status": "RECORDING — press F12 to stop",
        "recording_started": "Recording started.",
        "recording_stopped": "Recording stopped — {count} events",
        "recording_stopped_log": "Recording stopped with {count} events.",
        "countdown": "Playback begins in {seconds:g} seconds",
        "countdown_log": "Playback countdown started.",
        "playing": "PLAYING — press F12 to stop",
        "playback_started": "Playback started.",
        "playing_event": "Playing event {current} of {total}",
        "playback_finished": "Playback finished",
        "playback_finished_log": "Playback finished.",
        "playback_stopped": "Playback stopped",
        "playback_stopped_log": "Playback stopped.",
        "stop_requested": "Stop requested",
        "stop_requested_log": "Emergency stop requested.",
        "application_started": "Application started.",
        "f12_help": "Press F12 at any time to stop recording or playback.",
        "global_stop_unavailable": "Global F12 listener is unavailable. Use the Emergency stop button instead: {error}",
        "busy_stop_first": "Stop recording or playback first.",
        "new_recording_title": "Start new recording",
        "new_recording_warning": "Starting a new recording clears the current macro. Continue?",
        "typed_text_title": "Typed text recording",
        "typed_text_warning": "This option may capture everything you type while recording. Do not type passwords or sensitive information. Continue?",
        "cannot_start": "Could not start recording:\n{error}",
        "invalid_numbers": "Speed and delay must be valid numbers.",
        "invalid_playback_values": "Speed must be greater than zero and delay cannot be negative.",
        "record_or_load": "Record or load a macro first.",
        "play_title": "Play macro",
        "play_warning": "Playback begins in {seconds:g} seconds. Focus the target window. Press F12 to stop. Continue?",
        "no_events_save": "There are no events to save.",
        "save_title": "Save macro",
        "json_files": "JSON files",
        "all_files": "All files",
        "saved_log": "Saved {count} events to {path}.",
        "cannot_save": "Could not save the file:\n{error}",
        "load_title": "Load macro",
        "loaded_log": "Loaded {count} events from {path}.",
        "cannot_load": "Could not load the file:\n{error}",
        "clear_warning": "Delete all recorded events from memory?",
        "cleared_log": "Macro cleared.",
        "exit_warning": "Stop the active operation and exit?",
        "error": "Error",
        "warning": "Warning",
        "information": "Information",
        "file_label": "File: {path}",
        "wayland_warning": "Wayland session detected. pynput normally works through Xwayland and may only see applications running through Xwayland. X11 provides the most complete Linux support.",
        "linux_no_display": "No graphical display was detected. Start the app from a Linux desktop terminal, not a headless SSH session.",
        "unsupported_os": "This operating system is not officially supported: {system}.",
        "x11_ready": "Linux X11/Xwayland display detected.",
        "windows_ready": "Windows desktop detected.",
        "mac_experimental": "macOS is not officially supported in this release.",
        "platform_unknown": "Desktop environment detected with limited platform information.",
        "macro_too_large": "The macro file is larger than the allowed {size_mb} MB limit.",
        "settings_saved": "Language preference saved.",
        "language_busy": "Stop recording or playback before changing the language.",
        "platform_blocked": "Input automation is unavailable in the current desktop session.",
        "screen_mismatch": "The macro was recorded with different virtual-screen dimensions. Verify monitor positions before playback.",
    },
    "es": {
        "app_subtitle": "Grabador visible y local de macros de teclado y ratón.",
        "language": "Idioma",
        "english": "English",
        "spanish": "Español",
        "privacy_title": "Privacidad y seguridad",
        "privacy_text": "El registro de teclas imprimibles está desactivado por defecto. No grabes contraseñas, datos de pago, conversaciones privadas, códigos de autenticación ni información sensible.",
        "platform_title": "Estado de la plataforma",
        "platform_ready": "La automatización de entrada del escritorio está disponible.",
        "recording_options": "Opciones de grabación",
        "record_mouse": "Grabar movimiento del ratón",
        "record_text": "Grabar teclas imprimibles (texto escrito)",
        "keep_top": "Mantener ventana al frente",
        "mouse_sampling": "Muestreo del ratón",
        "sampling_smooth": "Suave (16 ms)",
        "sampling_balanced": "Equilibrado (33 ms)",
        "sampling_compact": "Compacto (75 ms)",
        "controls": "Controles",
        "start_recording": "Iniciar grabación",
        "stop_recording": "Detener grabación",
        "play_macro": "Reproducir macro",
        "emergency_stop": "Parada de emergencia (F12)",
        "save_json": "Guardar JSON",
        "load_json": "Cargar JSON",
        "clear": "Limpiar",
        "playback": "Reproducción",
        "speed": "Velocidad",
        "start_delay": "Retraso inicial (segundos)",
        "status_title": "Estado",
        "ready": "Listo",
        "events": "Eventos: {count}",
        "no_file": "Ningún archivo seleccionado",
        "unsaved": "Grabación sin guardar",
        "recording_status": "GRABANDO — presiona F12 para detener",
        "recording_started": "Grabación iniciada.",
        "recording_stopped": "Grabación detenida — {count} eventos",
        "recording_stopped_log": "Grabación detenida con {count} eventos.",
        "countdown": "La reproducción comienza en {seconds:g} segundos",
        "countdown_log": "Cuenta regresiva de reproducción iniciada.",
        "playing": "REPRODUCIENDO — presiona F12 para detener",
        "playback_started": "Reproducción iniciada.",
        "playing_event": "Reproduciendo evento {current} de {total}",
        "playback_finished": "Reproducción terminada",
        "playback_finished_log": "Reproducción terminada.",
        "playback_stopped": "Reproducción detenida",
        "playback_stopped_log": "Reproducción detenida.",
        "stop_requested": "Parada solicitada",
        "stop_requested_log": "Parada de emergencia solicitada.",
        "application_started": "Aplicación iniciada.",
        "f12_help": "Presiona F12 en cualquier momento para detener la grabación o reproducción.",
        "global_stop_unavailable": "El listener global de F12 no está disponible. Usa el botón de parada de emergencia: {error}",
        "busy_stop_first": "Primero detén la grabación o reproducción.",
        "new_recording_title": "Iniciar nueva grabación",
        "new_recording_warning": "Iniciar una nueva grabación borrará la macro actual. ¿Continuar?",
        "typed_text_title": "Grabación de texto escrito",
        "typed_text_warning": "Esta opción puede capturar todo lo que escribas durante la grabación. No escribas contraseñas ni información sensible. ¿Continuar?",
        "cannot_start": "No se pudo iniciar la grabación:\n{error}",
        "invalid_numbers": "La velocidad y el retraso deben ser números válidos.",
        "invalid_playback_values": "La velocidad debe ser mayor que cero y el retraso no puede ser negativo.",
        "record_or_load": "Primero graba o carga una macro.",
        "play_title": "Reproducir macro",
        "play_warning": "La reproducción comienza en {seconds:g} segundos. Enfoca la ventana de destino. Presiona F12 para detener. ¿Continuar?",
        "no_events_save": "No hay eventos para guardar.",
        "save_title": "Guardar macro",
        "json_files": "Archivos JSON",
        "all_files": "Todos los archivos",
        "saved_log": "Se guardaron {count} eventos en {path}.",
        "cannot_save": "No se pudo guardar el archivo:\n{error}",
        "load_title": "Cargar macro",
        "loaded_log": "Se cargaron {count} eventos desde {path}.",
        "cannot_load": "No se pudo cargar el archivo:\n{error}",
        "clear_warning": "¿Eliminar de la memoria todos los eventos grabados?",
        "cleared_log": "Macro eliminada de la memoria.",
        "exit_warning": "¿Detener la operación activa y salir?",
        "error": "Error",
        "warning": "Advertencia",
        "information": "Información",
        "file_label": "Archivo: {path}",
        "wayland_warning": "Se detectó una sesión Wayland. pynput normalmente funciona mediante Xwayland y podría ver únicamente aplicaciones ejecutadas con Xwayland. X11 ofrece el soporte Linux más completo.",
        "linux_no_display": "No se detectó una pantalla gráfica. Inicia la aplicación desde una terminal del escritorio Linux, no desde una sesión SSH sin interfaz gráfica.",
        "unsupported_os": "Este sistema operativo no cuenta con soporte oficial: {system}.",
        "x11_ready": "Se detectó una pantalla Linux X11/Xwayland.",
        "windows_ready": "Se detectó un escritorio Windows.",
        "mac_experimental": "macOS no cuenta con soporte oficial en esta versión.",
        "platform_unknown": "Se detectó un escritorio con información limitada de la plataforma.",
        "macro_too_large": "El archivo de macro supera el límite permitido de {size_mb} MB.",
        "settings_saved": "Preferencia de idioma guardada.",
        "language_busy": "Detén la grabación o reproducción antes de cambiar el idioma.",
        "platform_blocked": "La automatización de entrada no está disponible en la sesión de escritorio actual.",
        "screen_mismatch": "La macro fue grabada con dimensiones de pantalla virtual diferentes. Verifica las posiciones de los monitores antes de reproducirla.",
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
