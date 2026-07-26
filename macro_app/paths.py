"""Project and per-user data paths used by the desktop application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DATA_DIRECTORY_NAME = "MacroRecorderJSON"
DATA_DIRECTORY_OVERRIDE = "MACRO_RECORDER_DATA_DIR"


def running_from_bundle() -> bool:
    """Return whether the application is running from a frozen executable."""

    return bool(getattr(sys, "frozen", False))


def default_data_root() -> Path:
    """Return a writable data root for source and packaged executions.

    Source checkouts keep their existing project-local ``macros`` and
    ``automations`` folders. Packaged Windows builds use LocalAppData so the
    application remains writable even when installed under a protected folder.
    A dedicated environment variable is available for tests and portable use.
    """

    override = os.environ.get(DATA_DIRECTORY_OVERRIDE)
    if override:
        return Path(override).expanduser()

    if running_from_bundle():
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_DATA_DIRECTORY_NAME
        return Path.home() / "AppData" / "Local" / APP_DATA_DIRECTORY_NAME

    return PROJECT_ROOT


DATA_ROOT = default_data_root()
DEFAULT_MACRO_DIRECTORY = DATA_ROOT / "macros"
AUTOMATION_DIRECTORY = DATA_ROOT / "automations"


def ensure_directory(path: Path) -> Path:
    """Create and return one application data directory."""

    directory = path.expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()


def ensure_macro_directory(path: Path | None = None) -> Path:
    """Create and return the folder used for user macro files."""

    return ensure_directory(path or DEFAULT_MACRO_DIRECTORY)


def ensure_automation_directory(path: Path | None = None) -> Path:
    """Create and return the folder used for automation profiles."""

    return ensure_directory(path or AUTOMATION_DIRECTORY)
