"""Cross-platform desktop environment detection."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PlatformStatus:
    system: str
    session: str
    supported: bool
    warning_key: str | None
    status_key: str


def detect_platform_status() -> PlatformStatus:
    system = platform.system().lower()

    if system == "windows":
        return PlatformStatus("windows", "desktop", True, None, "windows_ready")

    if system == "linux":
        session = (os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()
        display = os.environ.get("DISPLAY")
        wayland_display = os.environ.get("WAYLAND_DISPLAY")

        if not display and not wayland_display:
            return PlatformStatus(
                "linux", session or "headless", False,
                "linux_no_display", "linux_no_display",
            )

        if session == "wayland" or wayland_display:
            return PlatformStatus(
                "linux", "wayland", True,
                "wayland_warning", "x11_ready",
            )

        return PlatformStatus("linux", session or "x11", True, None, "x11_ready")

    if system == "darwin":
        return PlatformStatus(
            "macos", "desktop", False,
            "mac_experimental", "mac_experimental",
        )

    return PlatformStatus(
        system or "unknown", "unknown", False,
        "unsupported_os", "platform_unknown",
    )
