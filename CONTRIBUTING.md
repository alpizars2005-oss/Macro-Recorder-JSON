# Contributing

Thank you for your interest in improving Macro Recorder JSON.

## Development setup

1. Fork or clone the repository.
2. Install Python 3.11 or 3.12.
3. Create a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install the dependency:

```powershell
python -m pip install -r requirements.txt
```

5. Run the application:

```powershell
python macro_recorder.py
```

6. Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

## Contribution guidelines

- Keep all code comments, user-interface text, commit messages, and documentation in English.
- Preserve the visible, local-only design.
- Do not add stealth recording, credential capture, remote data transmission, persistence, or automatic startup.
- Do not commit personal macro recordings or sensitive information.
- Add or update documentation when behavior changes.
- Add tests for JSON validation, playback safety, or format changes.
- Preserve `F12` as the reserved emergency-stop key.
- Keep pull requests focused and explain the reason for each change.

## Commit message examples

```text
Add macro validation before playback
Fix emergency-stop status handling
Document the JSON event format
Improve Windows launcher diagnostics
```
