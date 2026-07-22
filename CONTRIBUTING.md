# Contributing

Thank you for your interest in improving Macro Recorder JSON.

## Development setup

Use Python 3.11, 3.12, or 3.13.

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

## Guidelines

- Keep source code, comments, commit messages, and repository documentation in English.
- Add both English and Spanish UI strings for every new user-facing message.
- Keep translation key sets identical; the tests enforce this.
- Preserve visible, local-only operation.
- Do not add stealth capture, credential collection, remote transmission, persistence, automatic startup, or security-control bypasses.
- Do not require root access on Linux.
- Preserve `F12` as the emergency-stop key.
- Treat macro JSON as untrusted input.
- Add validation limits for new schema fields.
- Never commit personal macros, `.venv`, logs, caches, or sensitive information.
- Update the changelog and relevant documentation with behavior changes.
- Add tests for schema, translation, settings, or bootstrap logic.

## Pull request checklist

- [ ] Python source compiles on supported versions.
- [ ] Unit tests pass.
- [ ] English and Spanish UI translations are complete.
- [ ] Windows and Linux behavior was considered.
- [ ] Privacy and safety boundaries remain intact.
- [ ] Documentation was updated.
