# Architecture

## Overview

Macro Recorder JSON 2.0 uses a small package instead of a single large source file.

- `macro_recorder.py`: command-line entry point and language selection.
- `bootstrap.py`: cross-platform environment and dependency manager.
- `macro_app/constants.py`: versions, safety limits, and supported values.
- `macro_app/i18n.py`: English and Spanish translations.
- `macro_app/settings.py`: non-sensitive persistent preferences.
- `macro_app/platform_support.py`: Windows/Linux session detection.
- `macro_app/model.py`: backend-independent schema validation and optimization.
- `macro_app/recorder.py`: `pynput` capture and playback backend.
- `macro_app/ui.py`: bilingual Tkinter interface.

## Startup flow

1. A platform launcher chooses a compatible Python interpreter.
2. `bootstrap.py` checks Python, Tkinter, desktop availability, `.venv`, and dependencies.
3. Dependencies are installed only when the requirements hash or package health check fails.
4. `macro_recorder.py` loads settings and resolves the requested language.
5. The Tkinter interface initializes the input backend.

## Recording flow

1. The user confirms recording options.
2. `pynput` listeners receive keyboard and mouse events.
3. Printable characters are ignored unless the user explicitly enabled them.
4. Mouse movement is sampled at the selected interval.
5. Events are timestamped with `time.perf_counter()` and stored in memory.
6. `F12` or the visible emergency-stop button stops the listeners.

## Save flow

1. The in-memory event list is copied under a lock.
2. Redundant consecutive mouse movements are coalesced.
3. Platform and virtual-screen metadata are added.
4. The complete document is serialized as UTF-8 JSON.
5. A temporary file is written in the destination directory.
6. `os.replace` atomically replaces the destination.

## Load flow

1. File size is checked before reading.
2. JSON is parsed.
3. Schema version, event count, duration, timestamps, event types, fields, coordinates, keys, and buttons are validated.
4. Only validated events are placed in memory.
5. The UI compares recorded and current virtual-screen dimensions and warns about mismatches.

## Playback flow

1. The user confirms playback and receives a countdown.
2. Playback runs in a daemon worker thread.
3. Delays are derived from the original event timestamps and selected speed.
4. A thread-safe queue sends progress updates to Tkinter.
5. `F12` sets a cancellation event.
6. A `finally` block releases held keys and mouse buttons after success, interruption, or failure.

## Internationalization

Interface strings are referenced by stable keys. `Translator` formats the English or Spanish template at runtime. The language can be selected through the UI or `--language en|es` and is stored in the per-user settings file.

Sensitive printable-key recording is never persisted as an enabled startup preference.
