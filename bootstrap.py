"""Cross-platform dependency bootstrapper for Macro Recorder JSON."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
STAMP_FILE = VENV_DIR / ".requirements.sha256"
SUPPORTED_LANGUAGES = ("en", "es")
MIN_PYTHON = (3, 11)
MAX_PYTHON = (3, 13)
REQUIRED_PYNPUT_VERSION = "1.8.2"


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Prepare and launch Macro Recorder JSON.",
        add_help=True,
    )
    parser.add_argument("--language", "-l", choices=SUPPORTED_LANGUAGES)
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Recreate the local virtual environment before launching.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify the environment without launching the desktop application.",
    )
    return parser.parse_known_args()


def run(
    command: Sequence[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        text=True,
        check=check,
        env=env,
    )


def validate_python() -> None:
    version = sys.version_info[:2]
    if version < MIN_PYTHON or version > MAX_PYTHON:
        raise RuntimeError(
            "Python 3.11, 3.12, or 3.13 is required. "
            f"Detected Python {sys.version_info.major}.{sys.version_info.minor}."
        )
    if sys.maxsize <= 2**32:
        print("WARNING: 64-bit Python is recommended.")


def validate_tkinter() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import tkinter"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return

    if platform.system().lower() == "linux":
        raise RuntimeError(
            "Tkinter is not installed. Install it and run the launcher again.\n"
            "Ubuntu/Debian: sudo apt update && sudo apt install -y python3-tk python3-venv\n"
            "Fedora: sudo dnf install -y python3-tkinter\n"
            "Arch Linux: sudo pacman -S --needed tk"
        )
    raise RuntimeError(
        "Tkinter is unavailable. Repair or reinstall Python from python.org and include Tcl/Tk support."
    )


def validate_linux_desktop() -> None:
    if platform.system().lower() != "linux":
        return
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        raise RuntimeError(
            "No graphical Linux display was detected. Start this launcher from a desktop terminal, "
            "not a headless SSH session."
        )
    session = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    if session == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        print(
            "WARNING: Wayland detected. pynput may operate through Xwayland with limited access. "
            "Use an X11 session for the most complete Linux support."
        )


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS_FILE.read_bytes()).hexdigest()


def recreate_environment() -> None:
    if VENV_DIR.exists():
        print("Removing the existing virtual environment...")
        shutil.rmtree(VENV_DIR)


def ensure_environment(repair: bool) -> Path:
    if repair:
        recreate_environment()

    python_path = venv_python()
    if VENV_DIR.exists() and not python_path.exists():
        print("The existing virtual environment belongs to another platform or is incomplete.")
        recreate_environment()

    if python_path.exists():
        health = subprocess.run(
            [
                str(python_path),
                "-c",
                "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) else 1)",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
        )
        if health.returncode != 0:
            print("The existing virtual environment is incompatible or damaged.")
            recreate_environment()

    python_path = venv_python()
    if not python_path.exists():
        print("Creating the local virtual environment...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])

    if not python_path.exists():
        raise RuntimeError("The virtual environment could not be created.")
    return python_path


def dependency_state_is_valid(python_path: Path) -> bool:
    if (
        not STAMP_FILE.exists()
        or STAMP_FILE.read_text(encoding="utf-8").strip() != requirements_hash()
    ):
        return False

    version_check = subprocess.run(
        [
            str(python_path),
            "-c",
            (
                "from importlib.metadata import version; "
                f"raise SystemExit(0 if version('pynput') == '{REQUIRED_PYNPUT_VERSION}' else 1)"
            ),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if version_check.returncode != 0:
        return False

    pip_check = subprocess.run(
        [str(python_path), "-m", "pip", "check"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    return pip_check.returncode == 0


def ensure_dependencies(python_path: Path) -> None:
    if dependency_state_is_valid(python_path):
        print("Dependencies are already installed and valid. Skipping download.")
        return

    print("Installing or repairing required dependencies...")
    pip_result = subprocess.run(
        [str(python_path), "-m", "pip", "--version"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if pip_result.returncode != 0:
        run([str(python_path), "-m", "ensurepip", "--upgrade"])

    run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "-r",
            str(REQUIREMENTS_FILE),
        ]
    )
    run([str(python_path), "-m", "pip", "check"])
    STAMP_FILE.write_text(requirements_hash() + "\n", encoding="utf-8")


def launch(python_path: Path, language: str | None, extra_args: list[str]) -> int:
    command = [str(python_path), str(PROJECT_ROOT / "macro_recorder.py")]
    if language:
        command.extend(["--language", language])
    command.extend(extra_args)
    return subprocess.call(command, cwd=PROJECT_ROOT)


def main() -> int:
    args, extra_args = parse_args()
    try:
        validate_python()
        validate_tkinter()
        validate_linux_desktop()
        python_path = ensure_environment(args.repair)
        ensure_dependencies(python_path)
        if args.check_only:
            print("Environment check completed successfully.")
            return 0
        return launch(python_path, args.language, extra_args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
