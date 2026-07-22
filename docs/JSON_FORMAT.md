# JSON Format

## Schema version 2

```json
{
  "app": "Macro Recorder JSON",
  "version": "2.0.0",
  "schema_version": 2,
  "created_at": "2026-07-22T00:00:00+00:00",
  "platform": {
    "system": "Windows",
    "release": "11",
    "python": "3.12.0"
  },
  "screen": {
    "x": 0,
    "y": 0,
    "width": 1920,
    "height": 1080
  },
  "settings": {
    "record_mouse_move": true,
    "record_printable_keys": false,
    "mouse_sample_mode": "balanced",
    "emergency_stop": "F12"
  },
  "event_count": 0,
  "duration_seconds": 0.0,
  "events": []
}
```

## Compatibility

Files without `schema_version` are treated as schema version 1. Version 2 adds platform metadata, mouse-sampling metadata, and a declared duration while preserving the version 1 event structure.

## Event structure

```json
{
  "t": 0.25,
  "type": "mouse_move",
  "data": {}
}
```

- `t`: finite, non-negative elapsed seconds.
- `type`: supported event category.
- `data`: event-specific values.

Supported event types:

- `key_down`
- `key_up`
- `mouse_move`
- `mouse_button`
- `mouse_scroll`

## Keyboard event

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

Key kinds:

- `char`: exactly one character.
- `special`: a supported `pynput.keyboard.Key` name.
- `vk`: an integer virtual-key value encoded as a string.

`F12` is reserved for emergency stop and is rejected during loading.

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

## Validation limits

- Maximum file size: 20 MB.
- Maximum events: 250,000.
- Maximum duration: 24 hours.
- Timestamps must be finite, non-negative, and ordered.
- Coordinates and scroll values must remain within configured bounds.
- Event-specific fields must use the expected JSON types.
- Unsupported event types, keys, buttons, and schema versions are rejected.

## Editing guidance

- Preserve matching press/release pairs.
- Keep event timestamps ordered.
- Test edited files in a harmless target such as a text editor.
- Keep a backup of the original JSON.
