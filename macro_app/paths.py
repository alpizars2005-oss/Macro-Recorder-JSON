"""Project paths used by the desktop application."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MACRO_DIRECTORY = PROJECT_ROOT / "macros"
AUTOMATION_DIRECTORY = PROJECT_ROOT / "automations"


def ensure_directory(path: Path) -> Path:
    """Create and return one project data directory."""

    directory = path.expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()


def ensure_macro_directory(path: Path | None = None) -> Path:
    """Create and return the folder used for user macro files."""

    return ensure_directory(path or DEFAULT_MACRO_DIRECTORY)


def ensure_automation_directory(path: Path | None = None) -> Path:
    """Create and return the folder used for automation profiles."""

    return ensure_directory(path or AUTOMATION_DIRECTORY)
