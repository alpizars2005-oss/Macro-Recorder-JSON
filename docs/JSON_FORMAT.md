# JSON Format

## Top-level object

```json
{
  "app": "Macro Recorder JSON",
  "version": "1.1.0",
  "schema_version": 1,
  "created_at": "2026-07-21T00:00:00+00:00",
  "screen": {
    "x": 0,
    "y": 0,
    "width": 1920,
    "height": 1080
  },
  "settings": {
    "record_mouse_move": true,
    "record_printable_keys": false,
    "emergency_stop": "F12"
  },
  "event_count": 1,
  "events": []
}
```

## Top-level fields

- `app`: application name.
- `version`: application version that wrote the file.
- `schema_version`: macro-document schema version.
- `created_at`: UTC creation timestamp in ISO 8601 format.
- `screen`: virtual desktop bounds recorded for diagnostics.
- `settings`: recording settings associated with the macro.
- `event_count`: number of entries in `events`.
- `events`: ordered macro event list.

Files without `schema_version` are treated as schema version `1` for compatibility with the first public release.

## Common event fields

Every event uses the following structure:

```json
{
  "t": 0.25,
  "type": "mouse_move",
  "data": {}
}
```

- `t` is the elapsed time in seconds from the start of the recording.
- `type` identifies how the event should be interpreted.
- `data` contains values required by that event type.

## Mouse movement

```json
{
  "t": 0.25,
  "type": "mouse_move",
  "data": {
    "x": 500,
    "y": 400
  }
}
```

## Mouse button

The same event type represents both press and release actions.

```json
{
  "t": 0.30,
  "type": "mouse_button",
  "data": {
    "x": 500,
    "y": 400,
    "button": "left",
    "pressed": true
  }
}
```

## Mouse scroll

```json
{
  "t": 0.50,
  "type": "mouse_scroll",
  "data": {
    "x": 500,
    "y": 400,
    "dx": 0,
    "dy": -2
  }
}
```

## Printable keyboard key

```json
{
  "t": 0.75,
  "type": "key_down",
  "data": {
    "key": {
      "kind": "char",
      "value": "a"
    }
  }
}
```

## Special keyboard key

```json
{
  "t": 0.80,
  "type": "key_up",
  "data": {
    "key": {
      "kind": "special",
      "value": "enter"
    }
  }
}
```

`F12` is reserved for emergency stop and is rejected during loading.

## Virtual-key representation

Some platform-specific keys may use a virtual-key code:

```json
{
  "kind": "vk",
  "value": "255"
}
```

## Validation rules

- `schema_version` must be supported.
- `event_count` must match the number of events when present.
- Event timestamps must be finite, non-negative, and in ascending order.
- Event types and required fields must match this document.
- Coordinates, scroll amounts, and virtual-key values must use valid integer representations.
- Boolean fields must be JSON booleans rather than strings or numbers.
- The reserved emergency-stop key cannot appear in a loaded macro.

## Editing guidelines

- Preserve matching press and release events.
- Use supported event-type names exactly as documented.
- Test edited macros in a safe window before using them in a real workflow.
- Keep the original file as a backup before making manual changes.
