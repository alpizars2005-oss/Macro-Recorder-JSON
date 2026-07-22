"""Project paths used by the desktop application."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MACRO_DIRECTORY = PROJECT_ROOT / "macros"


def ensure_macro_directory(path: Path | None = None) -> Path:
    """Create and return the folder used for user macro files."""

    directory = (path or DEFAULT_MACRO_DIRECTORY).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()
