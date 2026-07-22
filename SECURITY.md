# Security Policy

## Supported version

The latest release on `main` is supported.

## Reporting a concern

Do not publish passwords, tokens, private macros, personal information, or detailed exploit steps in a public issue. Use a private GitHub security advisory when available.

Include:

- A clear description.
- Reproduction steps.
- The affected version or commit.
- Expected and observed behavior.
- A suggested mitigation when possible.

## Security boundaries

The project must not add:

- Hidden or deceptive input capture.
- Credential collection.
- Remote transmission of recordings.
- Persistence or automatic startup.
- Root requirements on Linux.
- Automation of secure desktops, authentication prompts, or security-control bypasses.

## Untrusted macro files

Loaded JSON files are untrusted. The application enforces file-size, event-count, duration, timestamp, coordinate, scroll, key, button, and schema validation before playback.

## Dependency policy

Runtime dependencies are pinned in `requirements.txt`. The bootstrapper verifies the requirements hash, exact package version, and `pip check` before deciding whether installation is necessary.
