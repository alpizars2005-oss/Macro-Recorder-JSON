"""Command-line entry point for Macro Recorder JSON."""

from __future__ import annotations

import argparse
import sys

from macro_app.constants import APP_NAME, APP_VERSION, SUPPORTED_LANGUAGES
from macro_app.i18n import Translator, detect_system_language, normalize_language
from macro_app.platform_support import detect_platform_status
from macro_app.settings import load_settings, save_settings, settings_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--language",
        "-l",
        choices=SUPPORTED_LANGUAGES,
        help="Launch language: en or es.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()

    if args.language:
        settings.language = normalize_language(args.language)
    elif not settings_path().exists():
        settings.language = detect_system_language()

    save_settings(settings)
    translator = Translator(settings.language)
    platform_status = detect_platform_status()

    try:
        from macro_app.ui import App
    except ImportError as exc:
        print(f"{APP_NAME}: could not initialize the input backend: {exc}", file=sys.stderr)
        print(
            "Windows: run .\\run.bat --repair\n"
            "Linux: run bash run_linux.sh --repair from a graphical desktop terminal.",
            file=sys.stderr,
        )
        return 1

    app = App(settings, translator, platform_status)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
