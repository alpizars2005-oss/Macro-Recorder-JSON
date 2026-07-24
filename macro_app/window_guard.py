"""Foreground-window checks used to avoid clicking the wrong application."""

from __future__ import annotations

import ctypes
import platform
import shutil
import subprocess
from ctypes import wintypes
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class WindowCheck:
    allowed: bool
    title: str | None
    supported: bool


def foreground_window_title() -> str | None:
    system = platform.system().lower()
    if system == "windows":
        return _windows_foreground_title()
    if system == "linux":
        return _linux_foreground_title()
    return None


def check_foreground(required_substring: str) -> WindowCheck:
    required = required_substring.strip()
    if not required:
        return WindowCheck(allowed=True, title=foreground_window_title(), supported=True)
    title = foreground_window_title()
    if title is None:
        return WindowCheck(allowed=False, title=None, supported=False)
    return WindowCheck(allowed=required.casefold() in title.casefold(), title=title, supported=True)


def _windows_foreground_title() -> str | None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int

    handle = user32.GetForegroundWindow()
    if not handle:
        return None
    length = user32.GetWindowTextLengthW(handle)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    copied = user32.GetWindowTextW(handle, buffer, len(buffer))
    if copied <= 0:
        return ""
    return buffer.value


def _linux_foreground_title() -> str | None:
    if shutil.which("xdotool") is None:
        return None
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            check=True,
            capture_output=True,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()
