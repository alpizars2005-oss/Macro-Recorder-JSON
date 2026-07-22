# Macro Recorder JSON

A visible, local-only Windows desktop application for recording and replaying keyboard and mouse actions. Recorded events are stored as readable JSON files, making each automation easy to inspect, edit, version, and understand.

## Project goals

This project was created as a practical Python desktop-automation exercise. It demonstrates event-driven programming, global input listeners, JSON serialization and validation, background threads, a Tkinter interface, atomic file writing, and defensive safety controls.

## Features

- Records keyboard press and release events.
- Records mouse movement, clicks, button releases, and scroll events.
- Saves and loads macros as human-readable JSON.
- Validates untrusted JSON before playback.
- Replays recorded actions with adjustable speed.
- Provides a configurable countdown before playback.
- Uses `F12` as a global emergency stop during recording and playback.
- Releases held keys and mouse buttons when playback stops or fails.
- Keeps printable-key recording disabled by default.
- Records virtual desktop bounds to help diagnose coordinate mismatches.
- Shows recording and playback status in a visible interface.
- Runs without an API key or cloud service.
- Includes a debug launcher and automated tests.

## Safety and privacy

This application is intentionally visible and local-only. It does not include stealth operation, remote transmission, automatic startup, persistence, or background-service installation.

Printable-key recording can capture typed text. Keep that option disabled unless a macro genuinely needs text input. Never record passwords, payment information, private conversations, authentication codes, or other sensitive data.

Use this project only on systems and applications that you own or are authorized to automate.

> The application does not transmit macro data. The first run may access the internet only to download the declared Python dependency through `pip`.

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or Python 3.12
- A standard desktop session

Install Python 3.12 from PowerShell:

```powershell
winget install --exact --id Python.Python.3.12
```

Close and reopen the terminal after installation.

## Quick start

1. Download or clone the repository.
2. Double-click `run.bat`.
3. Wait while the virtual environment and dependency are prepared.
4. Choose whether mouse movement should be recorded.
5. Enable printable-key recording only when necessary.
6. Select **Start recording**.
7. Perform the desired actions.
8. Press `F12` to stop.
9. Select **Save JSON** to store the macro.
10. Load the file later and select **Play macro**.
11. Focus the target window during the countdown.

## Clone with Git

```powershell
git clone https://github.com/alpizars2005-oss/Macro-Recorder-JSON.git
cd Macro-Recorder-JSON
run.bat
```

## Project structure

```text
Macro-Recorder-JSON/
├── .github/workflows/python-tests.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── JSON_FORMAT.md
│   └── PRIVACY_AND_SAFETY.md
├── tests/
│   ├── test_example_macro.py
│   └── test_validation.py
├── .editorconfig
├── .gitattributes
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── example_macro.json
├── macro_recorder.py
├── requirements.txt
├── run.bat
└── run_debug.bat
```

## JSON event model

Each event contains:

- `t`: elapsed seconds from the beginning of the recording.
- `type`: the event category.
- `data`: event-specific values.

Supported event types:

- `key_down`
- `key_up`
- `mouse_move`
- `mouse_button`
- `mouse_scroll`

See [`docs/JSON_FORMAT.md`](docs/JSON_FORMAT.md) for the complete format.

## Known limitations

- Mouse coordinates depend on resolution, display scaling, monitor layout, and window position.
- A macro may behave differently after the interface or target application changes.
- The recorder may need the same permission level as an elevated target application.
- Windows secure screens, User Account Control dialogs, lock screens, and some protected applications cannot be automated.
- Global input hooks may be blocked by security software or restricted environments.
- The `F12` stop listener is best-effort; the visible emergency-stop button remains available if a global listener is blocked.

## Troubleshooting

Run:

```text
run_debug.bat
```

The terminal will remain open and display Python, environment, and application errors.

## Running the tests

```powershell
python -m unittest discover -s tests -v
```

The repository also includes a GitHub Actions workflow that compiles the source and runs the tests on Windows with Python 3.11 and 3.12.

## Responsible development note

This project was developed as a personal learning project with AI-assisted guidance. The source code, behavior, documentation, testing, and safety constraints are reviewed and maintained as part of the author's Python and desktop-automation practice.

## License

This project is available under the [MIT License](LICENSE).
