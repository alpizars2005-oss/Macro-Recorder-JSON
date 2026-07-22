# Macro Recorder JSON

A visible, local-only desktop application for recording and replaying keyboard and mouse actions on **Windows** and **Linux**. Macros are stored as readable JSON files, making each automation easy to inspect, edit, version, and understand.

The interface can be launched in **English** or **Spanish**, while the repository documentation remains in English.

## Highlights

- Windows 10/11 and Linux desktop support.
- English and Spanish interface with a persistent language preference.
- Keyboard press/release recording.
- Mouse movement, click, release, and scroll recording.
- Human-readable JSON save/load support.
- Strict validation before any loaded macro can be replayed.
- Adjustable playback speed and countdown.
- Global `F12` emergency stop during recording and playback.
- Automatic release of held keys and mouse buttons after interruption.
- Three mouse-sampling modes to balance smoothness and file size.
- Virtual-screen metadata and monitor-layout mismatch warnings.
- Smart bootstrapper that installs dependencies only when missing or outdated.
- No API key, cloud account, or paid service required.
- Automated tests on Windows and Linux with Python 3.11, 3.12, and 3.13.

## Privacy and responsible use

The application is intentionally visible and local-only. It does not implement stealth recording, remote transmission, automatic startup, persistence, credential collection, or background-service installation.

Printable-key recording is disabled every time the application starts. Enable it only for a planned macro and never record passwords, payment data, private conversations, authentication codes, or confidential information.

Use the project only on computers, accounts, and workflows that you own or are explicitly authorized to automate.

## Requirements

- Python 3.11, 3.12, or 3.13
- Git, when cloning the repository
- A graphical desktop session
- Windows 10/11, or Linux with X11/Xwayland

## Windows: copy and paste

Open PowerShell and run:

```powershell
git clone https://github.com/alpizars2005-oss/Macro-Recorder-JSON.git; Set-Location Macro-Recorder-JSON; .\run.bat
```

Launch directly in Spanish:

```powershell
.\run.bat --language es
```

Launch directly in English:

```powershell
.\run.bat --language en
```

Repair the local environment:

```powershell
.\run.bat --repair
```

Verify everything without opening the interface:

```powershell
.\run.bat --check-only
```

> PowerShell does not run files from the current directory by name alone. Use `.\run.bat`, not `run.bat`.

### Install Python on Windows

```powershell
winget install --exact --id Python.Python.3.12
```

Close and reopen PowerShell after installation.

## Linux: copy and paste

### Ubuntu or Debian

```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-tk && git clone https://github.com/alpizars2005-oss/Macro-Recorder-JSON.git && cd Macro-Recorder-JSON && bash run_linux.sh
```

### Fedora

```bash
sudo dnf install -y git python3 python3-tkinter && git clone https://github.com/alpizars2005-oss/Macro-Recorder-JSON.git && cd Macro-Recorder-JSON && bash run_linux.sh
```

### Arch Linux

```bash
sudo pacman -S --needed git python tk && git clone https://github.com/alpizars2005-oss/Macro-Recorder-JSON.git && cd Macro-Recorder-JSON && bash run_linux.sh
```

Launch in Spanish or English:

```bash
bash run_linux.sh --language es
bash run_linux.sh --language en
```

Repair or verify the environment:

```bash
bash run_linux.sh --repair
bash run_linux.sh --check-only
```

## Smart dependency behavior

The launcher creates a project-local `.venv` environment on the first run. It calculates a hash of `requirements.txt`, verifies the installed `pynput` version, and runs `pip check`.

When the environment is already valid, it prints:

```text
Dependencies are already installed and valid. Skipping download.
```

It does not upgrade `pip` on every launch and does not reinstall packages unnecessarily. If the repository is moved between Windows and Linux, or the virtual environment is damaged, the bootstrapper detects the incompatible environment and recreates it.

## Basic use

1. Launch the application with the platform command above.
2. Select English or Spanish from the language control.
3. Choose whether mouse movement should be recorded.
4. Select a mouse-sampling mode:
   - **Smooth** for more movement detail.
   - **Balanced** for normal use.
   - **Compact** for smaller JSON files.
5. Enable printable-key recording only when the macro needs typed text.
6. Select **Start recording**.
7. Perform the desired actions.
8. Press `F12` to stop.
9. Select **Save JSON**.
10. Load the JSON later and select **Play macro**.
11. Focus the intended window before the countdown ends.

## Linux compatibility

`pynput` uses X or uinput on Linux. This project targets normal graphical desktop sessions through X11/Xwayland and does not request root access.

Under Wayland, input monitoring may be limited to applications running through Xwayland. For the most complete Linux behavior, use an X11 desktop session. Headless SSH sessions are not supported because no graphical display is available.

See [Linux support](docs/LINUX_SUPPORT.md) for details.

## Project structure

```text
Macro-Recorder-JSON/
├── .github/workflows/python-tests.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BOOTSTRAP.md
│   ├── JSON_FORMAT.md
│   ├── LINUX_SUPPORT.md
│   └── PRIVACY_AND_SAFETY.md
├── macro_app/
│   ├── __init__.py
│   ├── constants.py
│   ├── i18n.py
│   ├── model.py
│   ├── platform_support.py
│   ├── recorder.py
│   ├── settings.py
│   └── ui.py
├── tests/
│   ├── test_i18n.py
│   ├── test_model.py
│   └── test_settings.py
├── bootstrap.py
├── example_macro.json
├── macro_recorder.py
├── requirements.txt
├── run.bat
├── run_windows.bat
├── run.sh
└── run_linux.sh
```

## JSON safety limits

Loaded files are rejected when they exceed defined safety limits, including:

- 20 MB maximum file size.
- 250,000 maximum events.
- 24-hour maximum duration.
- Bounded coordinate and scroll values.
- Ordered, finite, non-negative timestamps.
- Supported event, key, and mouse-button types only.
- No embedded `F12`, because it is reserved for emergency stop.

See [JSON format](docs/JSON_FORMAT.md) for the complete schema.

## Development and tests

Create a local environment manually:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

## Troubleshooting

Windows:

```powershell
.\run.bat --repair
```

Linux:

```bash
bash run_linux.sh --repair
```

For environment details without launching the UI:

```text
--check-only
```

## Responsible development note

This project was developed as a personal learning project with AI-assisted guidance. The source code, behavior, documentation, testing, and safety constraints are reviewed and maintained as part of the author's Python and desktop-automation practice.

## License

This project is available under the [MIT License](LICENSE).
