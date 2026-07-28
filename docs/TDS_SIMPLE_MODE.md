# TDS simple mode

Version 3.3.0 adds a small hybrid interface for reusing a successful older Tower Defense Simulator recording without rebuilding the entire run manually.

## What is reused

The original macro remains the authoritative timeline. The importer reads and preserves:

- the complete recorded click, keyboard, scroll, and camera sequence;
- the original screen size and run duration;
- tower-slot key usage;
- candidate placement clicks after tower-slot selections;
- the first recorded `F` and `B` ability times.

The imported profile removes manual `F` and `B` events during preparation and starts the automatic ability workers at the first times detected in the source recording.

## Slot order for the Wrecked Battlefield recording

```text
1  DJ Booth
2  Commander
3  Minigunner
4  Golden Scout
5  Farm
```

Placement counts in the migration report represent attempts, not guaranteed successful towers. Repeated keys, rejected placements, camera movement, or corrections can create more attempts than the final number of towers.

## Open the simple interface

Installed Windows builds create this shortcut:

```text
TDS Macro - modo simple
```

A source checkout can use:

```powershell
.\run.bat --tds-simple --language es
```

## Workflow

1. Select **Choose earlier macro**.
2. Choose the old RAW or CLEAN JSON recording.
3. The app creates a hybrid strategy profile and a migration report under the private strategies folder.
4. Select **Start one run**.
5. Switch to Roblox during the countdown.
6. Keep `F12` ready and supervise the test.

The migration report is useful for the later semantic conversion because it already contains normalized candidate positions and exact timestamps.

## Why this is hybrid

A raw recording can be replayed immediately, but it cannot prove that a tower was successfully placed. The semantic engine can confirm actions, but translating every click without context would introduce false assumptions. Hybrid mode therefore reuses the reliable recorded timeline now and gradually replaces fragile sections with calibrated visual actions.

## Current limitation

The initial camera and Roblox layout must still match the original recording during recorded playback. Visual calibration and semantic camera preparation will progressively remove this restriction as the Wrecked Battlefield strategy is converted and verified.
