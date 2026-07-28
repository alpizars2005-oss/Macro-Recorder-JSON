"""Foreground application client-area discovery."""

from __future__ import annotations

import ctypes
import platform
import shutil
import subprocess
from ctypes import wintypes
from dataclasses import dataclass

from .client_geometry import ClientRect
from .window_guard import WindowCheck, check_foreground


@dataclass(frozen=True, slots=True)
class ClientWindowCheck:
    """Foreground-title result together with a usable client rectangle."""

    window: WindowCheck
    rect: ClientRect | None

    @property
    def ready(self) -> bool:
        return self.window.allowed and self.rect is not None


def check_foreground_client(required_substring: str) -> ClientWindowCheck:
    """Return the current foreground client area when its title is allowed."""

    window = check_foreground(required_substring)
    if not window.allowed:
        return ClientWindowCheck(window=window, rect=None)
    return ClientWindowCheck(window=window, rect=foreground_client_rect())


def foreground_client_rect() -> ClientRect | None:
    system = platform.system().lower()
    if system == "windows":
        return _windows_foreground_client_rect()
    if system == "linux":
        return _linux_foreground_window_rect()
    return None


def _windows_foreground_client_rect() -> ClientRect | None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL

    handle = user32.GetForegroundWindow()
    if not handle:
        return None

    bounds = RECT()
    if not user32.GetClientRect(handle, ctypes.byref(bounds)):
        return None

    origin = POINT(0, 0)
    if not user32.ClientToScreen(handle, ctypes.byref(origin)):
        return None

    width = int(bounds.right - bounds.left)
    height = int(bounds.bottom - bounds.top)
    if width <= 0 or height <= 0:
        return None
    return ClientRect(int(origin.x), int(origin.y), width, height)


def _linux_foreground_window_rect() -> ClientRect | None:
    """Return the active X11 window bounds as a conservative client proxy."""

    if shutil.which("xdotool") is None:
        return None
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowgeometry", "--shell"],
            check=True,
            capture_output=True,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_xdotool_geometry(result.stdout)


def parse_xdotool_geometry(output: str) -> ClientRect | None:
    values: dict[str, int] = {}
    for raw_line in output.splitlines():
        key, separator, raw_value = raw_line.partition("=")
        if not separator or key not in {"X", "Y", "WIDTH", "HEIGHT"}:
            continue
        try:
            values[key] = int(raw_value.strip())
        except ValueError:
            return None
    if set(values) != {"X", "Y", "WIDTH", "HEIGHT"}:
        return None
    try:
        return ClientRect(values["X"], values["Y"], values["WIDTH"], values["HEIGHT"])
    except ValueError:
        return None
