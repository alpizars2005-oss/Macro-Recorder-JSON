"""Persistent, non-sensitive application settings."""

from __future__ import annotations

import json
import os
import platform
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .constants import DEFAULT_LANGUAGE, DEFAULT_MOUSE_SAMPLE_MODE, MOUSE_SAMPLE_INTERVALS_MS
from .i18n import normalize_language


@dataclass(slots=True)
class AppSettings:
    """User preferences that are safe to persist locally."""

    language: str = DEFAULT_LANGUAGE
    record_mouse_move: bool = True
    keep_on_top: bool = True
    mouse_sample_mode: str = DEFAULT_MOUSE_SAMPLE_MODE
    playback_speed: float = 1.0
    playback_delay: float = 3.0

    @classmethod
    def from_mapping(cls, raw: Any) -> "AppSettings":
        if not isinstance(raw, dict):
            return cls()

        language = normalize_language(str(raw.get("language", DEFAULT_LANGUAGE)))
        sample_mode = str(raw.get("mouse_sample_mode", DEFAULT_MOUSE_SAMPLE_MODE))
        if sample_mode not in MOUSE_SAMPLE_INTERVALS_MS:
            sample_mode = DEFAULT_MOUSE_SAMPLE_MODE

        return cls(
            language=language,
            record_mouse_move=bool(raw.get("record_mouse_move", True)),
            keep_on_top=bool(raw.get("keep_on_top", True)),
            mouse_sample_mode=sample_mode,
            playback_speed=_bounded_float(raw.get("playback_speed"), 1.0, 0.1, 10.0),
            playback_delay=_bounded_float(raw.get("playback_delay"), 3.0, 0.0, 60.0),
        )


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if minimum <= number <= maximum else default


def config_directory() -> Path:
    """Return a per-user config directory without extra dependencies."""

    system = platform.system().lower()
    if system == "windows":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "MacroRecorderJSON"
        return Path.home() / "AppData" / "Roaming" / "MacroRecorderJSON"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "macro-recorder-json"
    return Path.home() / ".config" / "macro-recorder-json"


def settings_path() -> Path:
    return config_directory() / "settings.json"


def load_settings() -> AppSettings:
    path = settings_path()
    try:
        if not path.exists():
            return AppSettings()
        if path.stat().st_size > 128 * 1024:
            return AppSettings()
        return AppSettings.from_mapping(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """Atomically save preferences. Printable-key recording is never persisted."""

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n"
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=".settings.",
            suffix=".tmp",
        ) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)
