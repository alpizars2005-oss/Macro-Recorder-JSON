# Smart Bootstrapper

`bootstrap.py` provides the same environment-management behavior on Windows and Linux.

## Goals

- Keep setup close to click-and-play.
- Use a project-local `.venv`.
- Avoid reinstalling dependencies on every launch.
- Avoid upgrading `pip` unnecessarily.
- Detect virtual environments copied between operating systems.
- Provide actionable errors for missing Python, Tkinter, virtual-environment support, or graphical Linux sessions.

## Dependency check

Before running `pip install`, the bootstrapper verifies:

1. The `.venv` interpreter exists and can run.
2. The interpreter uses Python 3.11, 3.12, or 3.13.
3. The SHA-256 hash stored in `.venv/.requirements.sha256` matches the current `requirements.txt`.
4. The installed `pynput` version matches the pinned version.
5. `python -m pip check` reports no broken dependencies.

Only a failed check triggers dependency installation.

## Commands

```text
--language en
--language es
--repair
--check-only
```

`--repair` deletes and rebuilds only the disposable `.venv` directory. It does not delete source files, settings, or macro JSON files.

`--check-only` performs the platform, Python, Tkinter, virtual-environment, and dependency checks without opening the application.

## Why activation is not required

The launchers call the virtual environment's Python executable directly. Users do not need to activate `.venv` before running the application.
