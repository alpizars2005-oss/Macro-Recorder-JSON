# Privacy and Safety

## Local-only macro data

Macro Recorder JSON does not require an online account, API key, or cloud service. Recorded events remain on the local computer unless the user manually copies or uploads a JSON file.

The first launcher run may download the declared Python dependency with `pip`. The application itself does not transmit recorded macro data.

## Printable keys

Printable-key recording is disabled by default because typed characters may reveal sensitive information. Enable it only for a planned macro and disable it again afterward.

Never record while entering:

- Passwords or passphrases.
- Authentication codes.
- Banking or payment information.
- Private messages.
- Personal identifiers.
- Confidential workplace information.

## Visible operation

The application is designed to remain visible while recording or replaying. It does not implement hidden recording, automatic startup, remote control, or background persistence.

## Emergency stop

Press `F12` to request an immediate stop during recording or playback. A visible emergency-stop button is also provided. Test the stop behavior before running a long automation.

When playback stops or fails, the application attempts to release keyboard keys and mouse buttons that the macro still holds.

## Safe playback practices

- Test new macros in a non-destructive application such as Notepad.
- Confirm the correct window is focused before the countdown ends.
- Avoid playback while file-deletion dialogs, payment forms, terminals, or administrative tools are open.
- Keep backups of important files.
- Stop playback if the target interface changes unexpectedly.
- Inspect JSON files from other people before loading them.

## Authorization

Use the application only on computers, accounts, and workflows that you own or are explicitly authorized to automate.
