"""Macro document model and validation independent of the input backend."""

from __future__ import annotations

import math
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .constants import (
    APP_NAME,
    APP_VERSION,
    MAX_ABS_COORDINATE,
    MAX_ABS_SCROLL,
    MAX_DURATION_SECONDS,
    MAX_EVENTS,
    MAX_KEY_VALUE_LENGTH,
    SCHEMA_VERSION,
    STOP_KEY_NAME,
    SUPPORTED_EVENT_TYPES,
    SUPPORTED_MOUSE_BUTTONS,
    SUPPORTED_SCHEMA_VERSIONS,
    SUPPORTED_SPECIAL_KEYS,
)


@dataclass(slots=True)
class MacroEvent:
    """One timestamped input event."""

    t: float
    type: str
    data: dict[str, Any]


@dataclass(slots=True)
class MacroDocument:
    """Validated macro document and recording metadata."""

    events: list[MacroEvent]
    record_mouse_move: bool = True
    record_printable_keys: bool = False
    mouse_sample_mode: str = "balanced"
    source_schema_version: int = SCHEMA_VERSION
    source_screen: dict[str, int | None] | None = None

    def to_payload(self, screen: dict[str, int | None]) -> dict[str, Any]:
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "python": platform.python_version(),
            },
            "screen": screen,
            "settings": {
                "record_mouse_move": self.record_mouse_move,
                "record_printable_keys": self.record_printable_keys,
                "mouse_sample_mode": self.mouse_sample_mode,
                "emergency_stop": "F12",
            },
            "event_count": len(self.events),
            "duration_seconds": self.events[-1].t if self.events else 0.0,
            "events": [asdict(event) for event in self.events],
        }


def validate_payload(payload: Any) -> MacroDocument:
    """Validate untrusted JSON before it can be replayed."""

    if not isinstance(payload, dict):
        raise ValueError("The macro file must contain a JSON object.")

    schema_version = _require_int(payload.get("schema_version", 1), "schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        expected = ", ".join(str(value) for value in sorted(SUPPORTED_SCHEMA_VERSIONS))
        raise ValueError(
            f"Unsupported schema version: {schema_version}. Supported versions: {expected}."
        )

    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("The macro file must contain an events list.")
    if len(raw_events) > MAX_EVENTS:
        raise ValueError(f"The macro contains more than {MAX_EVENTS:,} events.")

    declared_count = payload.get("event_count")
    if declared_count is not None:
        count = _require_int(declared_count, "event_count")
        if count != len(raw_events):
            raise ValueError("event_count does not match the events list.")

    events: list[MacroEvent] = []
    previous_timestamp = 0.0
    for index, raw_event in enumerate(raw_events):
        event = validate_event(raw_event, index)
        if event.t < previous_timestamp:
            raise ValueError("Event timestamps must be in ascending order.")
        previous_timestamp = event.t
        events.append(event)

    if events and events[-1].t > MAX_DURATION_SECONDS:
        raise ValueError("The macro duration exceeds the 24-hour safety limit.")

    raw_settings = payload.get("settings", {})
    if not isinstance(raw_settings, dict):
        raise ValueError("settings must be a JSON object.")

    sample_mode = str(raw_settings.get("mouse_sample_mode", "balanced"))
    if sample_mode not in {"smooth", "balanced", "compact"}:
        sample_mode = "balanced"

    screen = payload.get("screen")
    if screen is not None and not isinstance(screen, dict):
        raise ValueError("screen must be a JSON object when present.")

    return MacroDocument(
        events=events,
        record_mouse_move=_require_bool(
            raw_settings.get("record_mouse_move", True),
            "settings.record_mouse_move",
        ),
        record_printable_keys=_require_bool(
            raw_settings.get("record_printable_keys", False),
            "settings.record_printable_keys",
        ),
        mouse_sample_mode=sample_mode,
        source_schema_version=schema_version,
        source_screen=screen,
    )


def validate_event(raw_event: Any, index: int) -> MacroEvent:
    label = f"events[{index}]"
    if not isinstance(raw_event, dict):
        raise ValueError(f"{label} must be a JSON object.")

    timestamp = _require_number(raw_event.get("t"), f"{label}.t")
    if timestamp < 0:
        raise ValueError(f"{label}.t must be non-negative.")

    event_type = raw_event.get("type")
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"{label}.type is not supported: {event_type}")

    data = raw_event.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"{label}.data must be a JSON object.")

    if event_type in {"key_down", "key_up"}:
        normalized = {"key": validate_key_data(data.get("key"), f"{label}.data.key")}
    elif event_type == "mouse_move":
        normalized = {
            "x": _require_coordinate(data.get("x"), f"{label}.data.x"),
            "y": _require_coordinate(data.get("y"), f"{label}.data.y"),
        }
    elif event_type == "mouse_button":
        button = data.get("button")
        if not isinstance(button, str) or button not in SUPPORTED_MOUSE_BUTTONS:
            raise ValueError(f"{label}.data.button is unsupported: {button}")
        normalized = {
            "x": _require_coordinate(data.get("x"), f"{label}.data.x"),
            "y": _require_coordinate(data.get("y"), f"{label}.data.y"),
            "button": button,
            "pressed": _require_bool(data.get("pressed"), f"{label}.data.pressed"),
        }
    else:
        normalized = {
            "x": _require_coordinate(data.get("x"), f"{label}.data.x"),
            "y": _require_coordinate(data.get("y"), f"{label}.data.y"),
            "dx": _require_bounded_int(data.get("dx"), f"{label}.data.dx", MAX_ABS_SCROLL),
            "dy": _require_bounded_int(data.get("dy"), f"{label}.data.dy", MAX_ABS_SCROLL),
        }

    return MacroEvent(timestamp, str(event_type), normalized)


def validate_key_data(raw: Any, field: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError(f"{field} must be a JSON object.")

    kind = raw.get("kind")
    value = raw.get("value")
    if not isinstance(kind, str) or kind not in {"char", "special", "vk"}:
        raise ValueError(f"{field}.kind is invalid.")
    if not isinstance(value, str) or not value or len(value) > MAX_KEY_VALUE_LENGTH:
        raise ValueError(f"{field}.value is invalid.")

    if kind == "char" and len(value) != 1:
        raise ValueError(f"{field}.value must contain one printable character.")
    if kind == "special":
        if value not in SUPPORTED_SPECIAL_KEYS:
            raise ValueError(f"Unsupported special key: {value}")
        if value == STOP_KEY_NAME:
            raise ValueError("F12 is reserved for the emergency stop.")
    if kind == "vk":
        try:
            virtual_key = int(value)
        except ValueError as exc:
            raise ValueError(f"{field}.value must contain an integer virtual-key code.") from exc
        if not 0 <= virtual_key <= 65_535:
            raise ValueError(f"{field}.value is outside the supported virtual-key range.")

    return {"kind": kind, "value": value}


def optimize_mouse_moves(events: Iterable[MacroEvent], minimum_interval: float) -> list[MacroEvent]:
    """Coalesce redundant consecutive mouse-move events."""

    optimized: list[MacroEvent] = []
    for event in events:
        if (
            event.type == "mouse_move"
            and optimized
            and optimized[-1].type == "mouse_move"
            and event.t - optimized[-1].t < minimum_interval
        ):
            optimized[-1] = event
        else:
            optimized.append(event)
    return optimized


def _require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite.")
    return result


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer.")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean.")
    return value


def _require_coordinate(value: Any, field: str) -> int:
    return _require_bounded_int(value, field, MAX_ABS_COORDINATE)


def _require_bounded_int(value: Any, field: str, maximum: int) -> int:
    number = _require_int(value, field)
    if abs(number) > maximum:
        raise ValueError(f"{field} exceeds the supported range.")
    return number
