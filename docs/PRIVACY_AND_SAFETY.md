# Privacy and Safety

## Local data

Macro events remain in memory until the user explicitly saves a JSON file. The application does not upload macros and does not require an account or API key.

The bootstrapper may access the Python package index only when a required dependency is missing, outdated, or broken. Valid environments skip the download step.

## Printable keys

Printable-key recording is disabled on every application start and is never restored as an enabled preference. The application requires an additional confirmation before enabling it for a recording.

Never record passwords, authentication codes, payment information, private messages, personal identifiers, or confidential workplace data.

## Visible operation

The application has no stealth mode, persistence mechanism, remote-control feature, startup entry, service installation, or hidden data transmission.

## Loaded-file validation

Macro JSON is treated as untrusted input. File size, schema, counts, duration, timestamps, coordinates, scroll values, event types, buttons, and keys are validated before playback.

## Emergency stop

`F12` is reserved and cannot be embedded in a macro. Both recording and playback can be stopped with `F12` or the visible emergency-stop button.

The playback cleanup routine attempts to release every key and mouse button that remains held when playback stops or fails.

## Safe playback practices

- Test unfamiliar macros in a non-destructive application.
- Inspect files received from another person.
- Confirm the target window during the countdown.
- Keep payment forms, deletion dialogs, terminals, and administrative tools closed.
- Stop immediately when the interface differs from the recorded environment.
- Verify monitor layout after moving a macro between computers.
