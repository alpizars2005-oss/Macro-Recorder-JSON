# TDS macro ecosystem review

This document records the public repositories reviewed while designing the semantic TDS runner. It is a curated engineering review, not a claim that every GitHub repository with `tds` or `macro` in its name is unique or trustworthy. Empty repositories, fixed-coordinate personal scripts, obvious forks, and duplicate mirrors are grouped instead of counted as separate architectures.

## Licensing rule

Macro Recorder JSON remains MIT licensed. GPL-licensed projects are used only to understand publicly documented behavior and architecture. Their code, assets, OCR models, image templates, and strategy files are not copied, translated, bundled, or redistributed.

MIT-licensed projects may inform implementation more directly, but borrowed source must preserve its license and attribution. The preferred approach remains an independent Python implementation with tests.

## Reviewed project families

### DarksenDev/tds-macro and mirrors

License: GPL-3.0.

Useful ideas:

- Explicit tower placement and upgrade actions instead of one long raw input recording.
- Roblox client-relative coordinates and scaling.
- Deterministic camera alignment before strategy execution.
- Image-search confirmation of tower UI, Restart, and Play Again.
- Automatic ability lifecycles, timescale handling, strategy rotation, auto-equip, rewards, recovery, and community strategy browsing.

Adopt independently:

- Semantic strategy actions.
- Client-relative coordinates.
- Camera normalization.
- Bounded visual confirmation and retries.
- Ability lifecycle actions and final-screen detection.

Do not copy:

- AHK source, image templates, OCR code, strategy files, UI assets, updater code, or GPL libraries.

### dajalepep/tdsmacro-oss and forks

License: MIT.

Useful ideas:

- A reusable macro class rather than one monolithic strategy.
- Camera calibration.
- Placement retries with small positional noise when a point is blocked.
- Configurable patience and iterative confirmation reads for high-ping environments.
- Upgrade-until-level semantics.
- Automatic skip detection.
- Map, modifier, mode, and difficulty metadata.
- Result detection, screenshots, reconnect/hang recovery, private-server launch, and optional timescale use.
- Strategies stored separately from the execution framework.

Adopt:

- Reusable retry policy with bounded jitter and backoff.
- Target-level upgrades rather than blind click counts.
- Strategy requirements and game metadata.
- Watchdog timeouts and bounded recovery policies.
- Separate strategy documents and runtime engine.

### Kullaners/TinyKullan

License: GPL-3.0.

Useful ideas:

- Priority-based image-detection targets.
- Live testing of visual targets.
- Pause/resume hotkeys.
- Run manager, favorites, tags, and shareable configurations.
- Auto-recovery and session statistics.
- Portable import/export that includes referenced images.

Adopt independently:

- Priority detector scheduler.
- Visual-target test mode.
- Pause/resume and visible session statistics.
- Strategy library metadata, favorites, and safe import/export.

Do not adopt as designed:

- Embedding arbitrary images and full recordings in unbounded clipboard strings. Our importer will use size limits, hashes, and explicit user review.

### ryanmaki/TDS-Macros

License: no license was found during the review, so its source must be treated as all-rights-reserved.

Useful observations:

- Small ability-specific workflows can be useful alongside full strategies.
- User-configured coordinate lists are easier to calibrate than hard-coded coordinates.
- Fixed delays without visual confirmation fail under lag.

Adopt independently:

- Reusable micro-actions for special abilities.
- Calibration helpers for action-specific point lists.

### Marshall0947/TDS-Roblox-Macro and similar personal scripts

License: no license was found during the review.

Useful observation:

- Fixed-coordinate, fixed-sleep scripts are simple to understand but are fragile across camera, resolution, ping, UI, and economy changes.

Do not adopt:

- Blind desktop coordinates.
- Long fixed sleeps as the main synchronization mechanism.
- Infinite loops without foreground checks, confirmations, or bounded recovery.

## Chosen architecture

### Strategy document

A strategy describes intent:

- map, mode, difficulty, modifiers, and required loadout;
- camera preparation;
- tower identifiers and client-relative points;
- target-level upgrades;
- automatic abilities;
- wave or visual waits;
- result and repeat policy.

### Runtime engine

The engine owns safety and reliability:

- Roblox foreground and client-area checks;
- deterministic camera preparation;
- bounded retry policy with optional positional jitter;
- priority-based visual detectors;
- critical-action confirmations;
- stop, pause, and input cleanup;
- watchdog and recovery limits;
- visible logs and per-run statistics.

### Strategy library

Community strategies will be treated as untrusted data:

- strict schema and size limits;
- no executable code;
- source, author, license, and compatibility metadata;
- referenced images stored separately and hash-verified;
- explicit preview before import;
- private local strategies excluded from Git by default.

## Feature order

1. Retry policies, target-level upgrades, strategy requirements, and detector priorities.
2. Semantic runner with camera preparation and F12 cleanup.
3. Visual confirmation of placement, panel opening, level, funds, and ability readiness.
4. Restart/Play Again, wave skip, and result handling.
5. Map/loadout/modifier automation and bounded recovery.
6. Strategy editor, library, favorites, import/export, and compatibility reporting.
7. Convert the Wrecked Battlefield Molten recording into a verified semantic strategy.
