# Architecture

## Overview

Macro Recorder JSON is a single-process Windows desktop application built with Python.

The application contains two main layers:

1. `Recorder`: captures, validates, stores, loads, saves, and replays input events.
2. `App`: provides the Tkinter user interface and processes messages from worker threads.

## Recording flow

1. The user starts a recording from the interface.
2. `pynput.keyboard.Listener` receives keyboard events.
3. `pynput.mouse.Listener` receives mouse events.
4. Each accepted event is timestamped with `time.perf_counter()`.
5. Events are stored in memory as `MacroEvent` objects.
6. The user stops the recording with the interface or `F12`.
7. Events can be serialized to JSON through an atomic file replacement.

## Loading and validation flow

1. The selected JSON file is parsed.
2. The schema version, event count, settings, timestamps, event types, and event-specific fields are validated.
3. Unsupported keys, mouse buttons, malformed values, and the reserved `F12` key are rejected.
4. Only validated `MacroEvent` objects are stored for playback.

## Playback flow

1. The user loads or records a macro.
2. Playback starts in a daemon worker thread.
3. The worker calculates the delay between consecutive event timestamps.
4. `pynput.keyboard.Controller` and `pynput.mouse.Controller` reproduce the events.
5. Progress messages are placed in a thread-safe queue.
6. The Tkinter main thread reads the queue and updates the interface.
7. Held keys and mouse buttons are released in a `finally` block when playback ends, stops, or fails.

## Emergency-stop model

- During recording, the recording keyboard listener recognizes `F12` and requests a stop.
- During playback, a separate listener watches only for `F12`.
- The visible emergency-stop button remains available when global hooks are restricted.
- Macro files containing `F12` events are rejected so the reserved stop key cannot be replayed.

## Threading model

Tkinter must be updated from its main thread. Playback therefore runs in a worker thread, while interface updates are delivered through `queue.Queue`.

The application polls the queue with `after(100, ...)`, avoiding direct cross-thread widget access.

## Privacy model

- Events remain in memory until the user explicitly saves them.
- Saved macros are local JSON files selected by the user.
- Printable-character recording is disabled by default.
- The application contains no code that transmits macro data.
- Personal macro files are excluded by the repository `.gitignore` pattern.
