# TDS visual calibration

Version 3.2.0 adds private client-relative pixel signatures for confirming important Tower Defense Simulator states without distributing screenshots, OCR models, or third-party visual assets.

## Why several points are used

One screen pixel is easy to match accidentally. A signature combines several points from the same visible state. Each point stores:

- its position relative to the Roblox client area;
- its average RGB color;
- an allowed RGB tolerance;
- a small sampling radius.

A detector matches only when its configured percentage of points matches. The default is 80 percent.

## Open the wizard

Installed Windows builds create the shortcut:

```text
Calibrar TDS
```

Source checkouts can use:

```powershell
.\run.bat --visual-calibration --language es
```

## Capture one detector

1. Open Roblox and make the target state visible.
2. Open **Calibrar TDS**.
3. Choose or type a detector name.
4. Keep the default tolerance of `30`, radius of `1`, and minimum match of `0.80` for the first calibration.
5. Select **Capturar punto (3 s)**.
6. During the countdown, switch to Roblox and place the pointer over one stable solid-color area.
7. Repeat for at least three points, preferably five to eight.
8. Select **Probar detector (3 s)** and confirm that the detector matches when the state is visible.
9. Hide the state and test again; it should not match.
10. Save the file.

## Good sample locations

Prefer:

- flat-color areas inside an icon or button;
- static corners of a panel;
- two or more target points plus one or two nearby background points;
- points that remain visible at the same Roblox UI scale.

Avoid:

- text edges and antialiasing;
- animated glows;
- enemies, particles, shadows, and damage numbers;
- points covered by the cursor;
- translucent areas over a moving game scene.

## Recommended detector set for Wrecked Battlefield

Create these signatures from the successful run and its end screen:

```text
camera-ready
tower-panel
farm-level-5
insufficient-funds
call-to-arms-ready
drop-the-beat-ready
skip-wave
triumph
game-over
play-again
restart-match
```

Level-specific detectors may later be expanded to individual tower types, for example:

```text
farm-level-2
farm-level-3
farm-level-4
farm-level-5
minigunner-level-4
commander-level-2
dj-level-3
```

## File location

Installed builds save private signatures under:

```text
%LOCALAPPDATA%\MacroRecorderJSON\strategies\visuals\
```

These files are ignored by Git by default. They contain only normalized points and RGB values, not full screenshots.

## Signature file example

```json
{
  "schema_version": 1,
  "name": "call-to-arms-ready",
  "minimum_ratio": 0.8,
  "samples": [
    {
      "x": 0.08,
      "y": 0.54,
      "color": {"r": 76, "g": 186, "b": 92},
      "tolerance": 30,
      "radius": 1
    }
  ]
}
```

Real signatures should contain at least three samples. Five to eight well-chosen points are usually more reliable than increasing the tolerance.

## Fail-closed behavior

The new visual adapter does not assume that a mouse click succeeded. A critical semantic placement or upgrade must reference a detector. When the expected state is not confirmed, the action returns a bounded retryable failure. When retries or time limits are exhausted, the strategy stops instead of continuing with a corrupted run.

This release intentionally supports `.pixels.json` detector assets first. Image-template and OCR adapters can be added later behind the same semantic detector interface after their dependency, licensing, and packaging impact is reviewed.
