# Security Policy

## Supported version

The latest version on the `main` branch is the supported development version.

## Reporting a security concern

Do not publish passwords, tokens, private macro recordings, personal information, or exploit details in a public issue.

Report concerns through a private GitHub security advisory when that option is available for the repository. Include:

- A clear description of the concern.
- Steps required to reproduce it.
- The affected version or commit.
- The expected and observed behavior.
- Any suggested mitigation.

## Security boundaries

Macro Recorder JSON is designed for visible, local automation. The project must not add:

- Hidden or deceptive input capture.
- Credential collection.
- Remote transmission of recordings.
- Persistence or automatic startup without clear user control.
- Security-control bypasses.
- Automation of Windows secure desktops or authentication prompts.
