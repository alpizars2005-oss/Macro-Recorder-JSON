# Windows installer and portable package

Macro Recorder JSON can be distributed on Windows without asking end users to install Python or run commands.

## Packages

The Windows packaging workflow creates three files:

- `Macro-Recorder-JSON-Setup-<version>.exe`: recommended one-click installer.
- `Macro-Recorder-JSON-Portable.zip`: extracted application for users who prefer not to install it.
- `SHA256SUMS.txt`: checksums for verifying both downloads.

The installer places the application under the current user's LocalAppData Programs folder, creates Start Menu and desktop shortcuts, and does not request administrator privileges.

Two shortcuts are created:

- **Macro Recorder JSON** opens the normal recorder.
- **Automation Studio** opens the same bundled executable with `--automation --language es`.

Python, `pynput`, `mss`, Tkinter support, and the project modules are bundled in the packaged application. End users do not need the source checkout, a virtual environment, pip, or a separate Python installation.

## Personal data

Installed builds store writable data under:

```text
%LOCALAPPDATA%\MacroRecorderJSON\
├── macros\
└── automations\
```

Preferences remain under the existing per-user configuration directory. Uninstalling the application intentionally leaves macros, automation profiles, and preferences in place so an upgrade or reinstall cannot erase user work.

For a portable or test-specific data location, set the environment variable:

```powershell
$env:MACRO_RECORDER_DATA_DIR = "D:\My Macro Recorder Data"
```

## Build locally

Maintainers can build the installer with:

```powershell
.\build_windows_installer.bat
```

Required build tools:

- Python 3.12
- NSIS

The script creates `.venv-build`, installs the pinned build dependency, runs unit tests, builds the standalone application with PyInstaller, and compiles the NSIS setup executable.

Install the build tools with WinGet when needed:

```powershell
winget install --exact --id Python.Python.3.12
winget install --exact --id NSIS.NSIS
```

## Build through GitHub Actions

Run the **Build Windows installer** workflow manually, open a packaging-related pull request, or push a version tag such as:

```text
v3.0.1
```

Pull-request and manual runs publish a downloadable workflow artifact. Tagged runs also attach the setup executable, portable ZIP, and checksum file to the GitHub Release.

## Signing and Windows warnings

The build is not digitally code-signed by default. Windows SmartScreen or antivirus software may therefore show an unfamiliar-publisher warning, especially for a newly released executable with little reputation. The SHA-256 checksum confirms file integrity but does not replace code signing.

A future signed release can provide an Authenticode certificate to the packaging workflow without changing the application architecture.
