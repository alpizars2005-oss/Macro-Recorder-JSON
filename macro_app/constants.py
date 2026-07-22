"""Application-wide constants."""

from __future__ import annotations

APP_NAME = "Macro Recorder JSON"
APP_VERSION = "2.0.0"
SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
SUPPORTED_LANGUAGES = ("en", "es")
DEFAULT_LANGUAGE = "en"

MIN_PYTHON = (3, 11)
MAX_TESTED_PYTHON = (3, 13)
REQUIRED_PYNPUT_VERSION = "1.8.2"

STOP_KEY_NAME = "f12"
MAX_MACRO_FILE_BYTES = 20 * 1024 * 1024
MAX_EVENTS = 250_000
MAX_DURATION_SECONDS = 24 * 60 * 60
MAX_ABS_COORDINATE = 100_000
MAX_ABS_SCROLL = 10_000
MAX_KEY_VALUE_LENGTH = 64

MOUSE_SAMPLE_INTERVALS_MS = {
    "smooth": 16,
    "balanced": 33,
    "compact": 75,
}
DEFAULT_MOUSE_SAMPLE_MODE = "balanced"

SUPPORTED_EVENT_TYPES = {
    "key_down",
    "key_up",
    "mouse_move",
    "mouse_button",
    "mouse_scroll",
}

SUPPORTED_MOUSE_BUTTONS = {
    "left",
    "middle",
    "right",
    "x1",
    "x2",
    "unknown",
}

SUPPORTED_SPECIAL_KEYS = {
    "alt", "alt_gr", "alt_l", "alt_r", "backspace", "caps_lock",
    "cmd", "cmd_l", "cmd_r", "ctrl", "ctrl_l", "ctrl_r", "delete",
    "down", "end", "enter", "esc", "f1", "f2", "f3", "f4", "f5",
    "f6", "f7", "f8", "f9", "f10", "f11", "f12", "f13", "f14",
    "f15", "f16", "f17", "f18", "f19", "f20", "home", "insert",
    "left", "media_next", "media_play_pause", "media_previous",
    "media_volume_down", "media_volume_mute", "media_volume_up", "menu",
    "num_lock", "page_down", "page_up", "pause", "print_screen", "right",
    "scroll_lock", "shift", "shift_l", "shift_r", "space", "tab", "up",
}
