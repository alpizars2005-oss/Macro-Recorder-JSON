# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and the project uses semantic versioning where practical.

## [1.1.0] - 2026-07-21

### Added

- Strict validation for loaded macro JSON files.
- Schema-version and virtual-screen metadata.
- Global `F12` emergency stop during playback.
- Automatic release of held keys and mouse buttons when playback stops or fails.
- Atomic JSON file saving.
- Validation-focused automated tests.
- DPI-awareness setup for more accurate coordinates on scaled Windows displays.

### Changed

- Improved error messages, interface text, and documentation.
- The speed selector now accepts only the listed playback speeds.
- Starting a new recording now warns before clearing the current macro.

## [1.0.0] - 2026-07-21

### Added

- Visible Tkinter desktop interface.
- Keyboard press and release recording.
- Mouse movement, click, release, and scroll recording.
- Human-readable JSON save and load support.
- Adjustable playback speed and start delay.
- `F12` emergency stop during recording.
- Printable-key privacy warning and opt-in control.
- Windows launcher and debug launcher.
- English project documentation.
- Basic automated validation for the example macro.
