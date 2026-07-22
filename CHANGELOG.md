# Changelog

All notable changes to this project are documented in this file.

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
