# Semantic TDS strategy architecture

Macro Recorder JSON is moving from long, coordinate-only recordings toward explicit strategy actions that can be validated and retried.

## Goals

- Address Roblox using client-relative coordinates instead of desktop coordinates.
- Normalize camera pitch and zoom before a strategy begins.
- Represent tower actions explicitly: place, upgrade, change path, activate ability, wait, and align camera.
- Confirm important actions visually and retry within bounded limits.
- Keep all automation visible, local-only, foreground-guarded, and stoppable with F12.
- Preserve the recorded-strategy runner as a migration and debugging tool.

## Coordinate system

Strategy coordinates are normalized to the Roblox client area:

```text
normalized_x = client_x / client_width
normalized_y = client_y / client_height
```

At runtime:

```text
client_x = round(normalized_x * current_client_width)
client_y = round(normalized_y * current_client_height)
```

Normalized coordinates use the inclusive range 0.0 to 1.0. They are converted to desktop coordinates only immediately before a visible mouse action.

## Camera preparation

The first implementation uses deterministic camera saturation rather than trying to infer an arbitrary camera state:

1. Bring Roblox to the foreground.
2. Move the pointer to a known client-relative anchor.
3. Hold the right mouse button and drag vertically past the client boundary so pitch reaches a game-defined limit.
4. Release the right mouse button.
5. Hold the configured zoom key for a bounded duration to reach a zoom limit.
6. Optionally apply a configured number of wheel steps away from the limit.
7. Move the pointer to the client center.
8. Verify one or more visual anchors before strategy actions begin.

A preparation failure must stop the strategy instead of attempting placements from an unknown camera state.

## Semantic strategy document

A version 1 document has this shape:

```json
{
  "schema_version": 1,
  "name": "Wrecked Battlefield - Molten Farm",
  "window_title_contains": "Roblox",
  "camera": {
    "enabled": true,
    "anchor": {"x": 0.70, "y": 0.22},
    "pitch_drag": 1.25,
    "zoom_key": "o",
    "zoom_hold_seconds": 1.0,
    "zoom_back_steps": 0
  },
  "actions": [
    {"type": "align_camera"},
    {"type": "place_tower", "tower_id": "scout-1", "slot": 2, "point": {"x": 0.45, "y": 0.55}},
    {"type": "upgrade_tower", "tower_id": "scout-1", "levels": 1},
    {"type": "enable_ability", "name": "Call to Arms", "key": "f"}
  ]
}
```

## Validation and retry rules

- Unknown action types are rejected before execution.
- Coordinates outside the normalized client area are rejected.
- Tower identifiers must be unique after successful placement.
- Retries are bounded and visible in the status log.
- The active foreground window is checked before each input sequence.
- A failed confirmation never silently advances to the next critical action.

## Licensing boundary

The implementation is written independently in Python. The external GPL project was used to understand publicly documented behavior and architecture, not as a source of copied code. No GPL source file is imported, bundled, or translated into this MIT-licensed repository.
