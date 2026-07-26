# Changelog

All notable changes to this project are documented in this file.

## [3.0.1] - 2026-07-26

### Added

- Added a standalone Windows build that bundles Python and all runtime dependencies.
- Added a one-click per-user Windows installer with desktop and Start Menu shortcuts for Macro Recorder JSON and Automation Studio.
- Added a portable ZIP package and SHA-256 checksums.
- Added a local `build_windows_installer.bat` command for maintainers.
- Added a GitHub Actions workflow that builds and smoke-tests the packaged application and installer.

### Changed

- Packaged builds now save macros and automation profiles in a writable per-user LocalAppData folder.
- The frozen executable can relaunch itself from Automation Studio without requiring a Python installation.

### Security

- The installer does not request administrator privileges.
- Uninstalling preserves personal macros, profiles, and preferences.
- UPX compression is disabled in the Windows build to keep the package easier to inspect and reduce avoidable antivirus heuristics.

## [3.0.0] - 2026-07-24

### Added

- Added Automation Studio as an optional `--automation` launch mode.
- Added validated, private JSON profiles for combining saved macros, pixel-color triggers, and timed actions.
- Added configurable Restart and Replay watchers with consecutive-match confirmation, color tolerance, click revalidation, latching, and cooldown protection.
- Added a three-position Commander chain that selects each configured tower and presses one configured ability button.
- Added foreground-window checks before automated clicks and during saved-macro playback.
- Added Windows and Linux Automation Studio launchers.
- Added automated tests for profile validation, screen sampling, trigger behavior, and automation directories.
- Added the `mss` screen-capture dependency.

### Security

- Automation Studio remains visible, local-only, and stoppable globally with `F12`.
- Personal automation profiles inside `automations/` are ignored by Git.
- Saved macros stop when the configured foreground window loses focus.
- Trigger colors are rechecked immediately before clicking to reduce accidental input.

## [2.0.2] - 2026-07-22

### Added

- Added a dedicated `macros` folder for personal macro files.
- The application now creates and uses that folder as the default location for saving and opening macros.
- Added tests for the macro-folder path helper.

### Security

- Personal JSON macro files inside `macros/` are ignored by Git to reduce the chance of uploading private recordings.

## [2.0.1] - 2026-07-22

### Changed

- Rewrote the English and Spanish interface text with shorter, clearer wording.
- Replaced literal translations and technical terms with natural everyday language.
- Changed labels such as `Record printable keys` to `Record what I type` and `Grabar lo que escribo`.
- Simplified platform messages to `Windows detected` / `Windows detectado` and similar status text.
- Renamed visible actions to clearer terms such as `Run macro`, `Open macro`, and `Detener ahora`.
- Added bilingual launcher messages that follow the saved or requested interface language.
- Added tests that guard the natural wording in both languages.

## [2.0.0] - 2026-07-22

### Added

- Linux desktop support through X11/Xwayland.
- English and Spanish interface selection.
- Persistent non-sensitive preferences.
- `--language en|es`, `--repair`, and `--check-only` launcher options.
- Smart cross-platform bootstrapper.
- Windows and Linux copy/paste launch commands.
- Mouse sampling modes: smooth, balanced, and compact.
- Schema version 2 with platform, duration, and sampling metadata.
- Monitor-layout mismatch warnings.
- File-size, event-count, duration, coordinate, scroll, key, and button limits.
- Linux, bootstrap, and expanded architecture documentation.
- CI coverage for Windows and Ubuntu with Python 3.11, 3.12, and 3.13.

### Changed

- Refactored the single-file application into the `macro_app` package.
- Updated `pynput` from 1.7.7 to 1.8.2.
- Removed automatic `pip` upgrades from normal startup.
- Dependencies are now installed only when missing, outdated, or broken.
- Printable-key recording is never restored as an enabled startup preference.
- Mouse movement is sampled and coalesced to reduce JSON size.
- Windows documentation now uses the PowerShell-safe `.\run.bat` command.

### Security

- Macro JSON is treated as untrusted input.
- `F12` remains reserved and cannot be embedded in a macro.
- Playback cleanup releases held inputs after interruption or failure.
- Virtual environments copied between operating systems are detected and recreated.

## [1.1.0] - 2026-07-21

### Added

- Strict JSON validation.
- Global `F12` emergency stop during playback.
- Atomic JSON saving.
- DPI-awareness and virtual-screen metadata.
- Automated tests and Windows CI.

## [1.0.0] - 2026-07-21

### Added

- Initial visible Tkinter application.
- Keyboard and mouse event recording.
- JSON save/load and playback.
