"""Cross-platform setup and launcher for Macro Recorder JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
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


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "description": "Set up and open Macro Recorder JSON.",
        "repair_help": "Rebuild the local environment before opening the app.",
        "check_help": "Check the setup without opening the app.",
        "python_required": "Python 3.11, 3.12, or 3.13 is required. Python {version} was detected.",
        "python_64": "NOTICE: 64-bit Python is recommended.",
        "tk_linux": "Tkinter is missing. Install it, then run the launcher again.\nUbuntu/Debian: sudo apt update && sudo apt install -y python3-tk python3-venv\nFedora: sudo dnf install -y python3-tkinter\nArch Linux: sudo pacman -S --needed tk",
        "tk_other": "Tkinter is missing. Repair or reinstall Python from python.org and include Tcl/Tk support.",
        "no_desktop": "No Linux desktop session was detected. Run this from a desktop terminal, not a headless SSH session.",
        "wayland": "NOTICE: Wayland detected. The app works best through Xwayland. Use an X11 session for full Linux support.",
        "remove_venv": "Removing the current local environment...",
        "wrong_platform": "The current local environment belongs to another system or is incomplete.",
        "damaged_venv": "The current local environment is damaged or incompatible.",
        "create_venv": "Creating the local environment...",
        "venv_failed": "The local environment could not be created.",
        "deps_ready": "Everything is ready. No download needed.",
        "deps_install": "Installing or repairing the required component...",
        "check_success": "Setup check completed successfully.",
        "error": "ERROR: {error}",
    },
    "es": {
        "description": "Prepara y abre Macro Recorder JSON.",
        "repair_help": "Vuelve a crear el entorno local antes de abrir la app.",
        "check_help": "Revisa la instalación sin abrir la app.",
        "python_required": "Se necesita Python 3.11, 3.12 o 3.13. Se detectó Python {version}.",
        "python_64": "AVISO: Se recomienda Python de 64 bits.",
        "tk_linux": "Falta Tkinter. Instálalo y vuelve a ejecutar la app.\nUbuntu/Debian: sudo apt update && sudo apt install -y python3-tk python3-venv\nFedora: sudo dnf install -y python3-tkinter\nArch Linux: sudo pacman -S --needed tk",
        "tk_other": "Falta Tkinter. Repara o reinstala Python desde python.org e incluye Tcl/Tk.",
        "no_desktop": "No se detectó una sesión de escritorio en Linux. Ejecuta esto desde una terminal del escritorio, no desde una sesión SSH sin interfaz.",
        "wayland": "AVISO: Wayland detectado. La app funciona mejor mediante Xwayland. Usa una sesión X11 para tener compatibilidad completa.",
        "remove_venv": "Eliminando el entorno local actual...",
        "wrong_platform": "El entorno local actual pertenece a otro sistema o está incompleto.",
        "damaged_venv": "El entorno local actual está dañado o no es compatible.",
        "create_venv": "Creando el entorno local...",
        "venv_failed": "No se pudo crear el entorno local.",
        "deps_ready": "Todo está listo. No es necesario descargar nada.",
        "deps_install": "Instalando o reparando el componente necesario...",
        "check_success": "La revisión terminó correctamente.",
        "error": "ERROR: {error}",
    },
}


def normalize_language(value: str | None) -> str:
    """Return a supported two-letter language code."""

    if not value:
        return "en"
    code = value.strip().lower().replace("_", "-").split("-", 1)[0]
    return code if code in SUPPORTED_LANGUAGES else "en"


def settings_file() -> Path:
    """Return the app settings path without importing runtime modules."""

    if platform.system().lower() == "windows":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "MacroRecorderJSON" / "settings.json"
        return Path.home() / "AppData" / "Roaming" / "MacroRecorderJSON" / "settings.json"

    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "macro-recorder-json" / "settings.json"
    return Path.home() / ".config" / "macro-recorder-json" / "settings.json"


def saved_language() -> str | None:
    """Read only the saved language preference when available."""

    path = settings_file()
    try:
        if not path.exists() or path.stat().st_size > 128 * 1024:
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            language = normalize_language(str(raw.get("language", "")))
            return language if language in SUPPORTED_LANGUAGES else None
    except (OSError, json.JSONDecodeError):
        return None
    return None


def requested_language(argv: Sequence[str] | None = None) -> str:
    """Use an explicit option, saved preference, or system language."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    for index, item in enumerate(arguments):
        if item.startswith("--language="):
            return normalize_language(item.split("=", 1)[1])
        if item in {"--language", "-l"} and index + 1 < len(arguments):
            return normalize_language(arguments[index + 1])

    stored = saved_language()
    if stored:
        return stored

    try:
        system_language, _encoding = locale.getlocale()
    except ValueError:
        system_language = None
    return normalize_language(system_language)


LANGUAGE = requested_language()


def tr(key: str, **values: object) -> str:
    """Return one formatted launcher message."""

    template = TEXT.get(LANGUAGE, TEXT["en"]).get(key, TEXT["en"].get(key, key))
    return template.format(**values)


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description=tr("description"), add_help=True)
    parser.add_argument("--language", "-l", choices=SUPPORTED_LANGUAGES)
    parser.add_argument("--repair", action="store_true", help=tr("repair_help"))
    parser.add_argument("--check-only", action="store_true", help=tr("check_help"))
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
        detected = f"{sys.version_info.major}.{sys.version_info.minor}"
        raise RuntimeError(tr("python_required", version=detected))
    if sys.maxsize <= 2**32:
        print(tr("python_64"))


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
        raise RuntimeError(tr("tk_linux"))
    raise RuntimeError(tr("tk_other"))


def validate_linux_desktop() -> None:
    if platform.system().lower() != "linux":
        return
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        raise RuntimeError(tr("no_desktop"))
    session = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    if session == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        print(tr("wayland"))


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS_FILE.read_bytes()).hexdigest()


def recreate_environment() -> None:
    if VENV_DIR.exists():
        print(tr("remove_venv"))
        shutil.rmtree(VENV_DIR)


def ensure_environment(repair: bool) -> Path:
    if repair:
        recreate_environment()

    python_path = venv_python()
    if VENV_DIR.exists() and not python_path.exists():
        print(tr("wrong_platform"))
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
            print(tr("damaged_venv"))
            recreate_environment()

    python_path = venv_python()
    if not python_path.exists():
        print(tr("create_venv"))
        run([sys.executable, "-m", "venv", str(VENV_DIR)])

    if not python_path.exists():
        raise RuntimeError(tr("venv_failed"))
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
        print(tr("deps_ready"))
        return

    print(tr("deps_install"))
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
    global LANGUAGE

    args, extra_args = parse_args()
    if args.language:
        LANGUAGE = normalize_language(args.language)

    try:
        validate_python()
        validate_tkinter()
        validate_linux_desktop()
        python_path = ensure_environment(args.repair)
        ensure_dependencies(python_path)
        if args.check_only:
            print(tr("check_success"))
            return 0
        return launch(python_path, args.language, extra_args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(tr("error", error=exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
