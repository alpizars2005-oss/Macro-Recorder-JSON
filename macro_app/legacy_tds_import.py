"""Import useful timing and placement data from older recorded TDS macros.

The importer deliberately creates a migration report and a recorded-strategy
profile rather than pretending that every old click is a verified semantic
action. Camera movement, failed placement attempts, and lag can make individual
clicks ambiguous; the report preserves those candidates for later visual review.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .strategy_models import RecordedStrategyProfile

LEGACY_REPORT_SCHEMA_VERSION = 1
DEFAULT_SLOT_MAP: dict[int, str] = {
    1: "DJ Booth",
    2: "Commander",
    3: "Minigunner",
    4: "Golden Scout",
    5: "Farm",
}


@dataclass(frozen=True, slots=True)
class PlacementAttempt:
    time_seconds: float
    slot: int
    tower: str
    click_time_seconds: float | None
    desktop_x: int | None
    desktop_y: int | None
    normalized_x: float | None
    normalized_y: float | None
    confidence: str


@dataclass(frozen=True, slots=True)
class LegacyMacroReport:
    source_file: str
    duration_seconds: float
    screen_width: int
    screen_height: int
    event_count: int
    slot_map: dict[int, str]
    key_down_counts: dict[str, int]
    first_ability_times: dict[str, float]
    placement_attempts: tuple[PlacementAttempt, ...]
    caveats: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": LEGACY_REPORT_SCHEMA_VERSION,
            "source_file": self.source_file,
            "duration_seconds": self.duration_seconds,
            "screen": {"width": self.screen_width, "height": self.screen_height},
            "event_count": self.event_count,
            "slot_map": {str(key): value for key, value in self.slot_map.items()},
            "key_down_counts": self.key_down_counts,
            "first_ability_times": self.first_ability_times,
            "placement_attempts": [asdict(item) for item in self.placement_attempts],
            "caveats": list(self.caveats),
        }


def analyze_legacy_macro(
    path: Path,
    *,
    slot_map: Mapping[int, str] | None = None,
    placement_window_seconds: float = 3.0,
) -> LegacyMacroReport:
    """Return a conservative migration report for one recorded macro."""

    path = path.expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Legacy macro must be a JSON object.")
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("Legacy macro events must be a list.")

    screen = payload.get("screen") or {}
    width = _positive_int(screen.get("width"), "screen.width")
    height = _positive_int(screen.get("height"), "screen.height")
    duration = _number(payload.get("duration_seconds", 0.0), "duration_seconds")
    mapping = dict(slot_map or DEFAULT_SLOT_MAP)

    key_counts: Counter[str] = Counter()
    first_abilities: dict[str, float] = {}
    attempts: list[PlacementAttempt] = []

    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("type") != "key_down":
            continue
        key = _event_key(event)
        if not key:
            continue
        folded = key.casefold()
        key_counts[folded] += 1
        if folded in {"f", "b"} and folded not in first_abilities:
            first_abilities[folded] = _event_time(event)
        if not folded.isdigit():
            continue
        slot = int(folded)
        if slot not in mapping:
            continue

        click = _next_placement_click(
            events,
            index,
            start_time=_event_time(event),
            window_seconds=placement_window_seconds,
        )
        if click is None:
            attempts.append(
                PlacementAttempt(
                    time_seconds=_event_time(event),
                    slot=slot,
                    tower=mapping[slot],
                    click_time_seconds=None,
                    desktop_x=None,
                    desktop_y=None,
                    normalized_x=None,
                    normalized_y=None,
                    confidence="unpaired",
                )
            )
            continue

        click_time, x, y = click
        attempts.append(
            PlacementAttempt(
                time_seconds=_event_time(event),
                slot=slot,
                tower=mapping[slot],
                click_time_seconds=click_time,
                desktop_x=x,
                desktop_y=y,
                normalized_x=x / max(1, width - 1),
                normalized_y=y / max(1, height - 1),
                confidence="candidate",
            )
        )

    return LegacyMacroReport(
        source_file=str(path),
        duration_seconds=duration,
        screen_width=width,
        screen_height=height,
        event_count=len(events),
        slot_map=mapping,
        key_down_counts=dict(sorted(key_counts.items())),
        first_ability_times=first_abilities,
        placement_attempts=tuple(attempts),
        caveats=(
            "Placement entries are attempts, not guaranteed successful towers.",
            "Camera drags and failed clicks remain in the source macro and require visual review.",
            "The source recording remains the authoritative playback timeline.",
        ),
    )


def build_recorded_profile(path: Path, report: LegacyMacroReport) -> RecordedStrategyProfile:
    """Build a one-run hybrid profile that reuses the original recording."""

    profile = RecordedStrategyProfile.default_wrecked_battlefield()
    profile.name = "Wrecked Battlefield - imported legacy run"
    profile.macro_path = str(path.expanduser().resolve())
    profile.required_screen_width = report.screen_width
    profile.required_screen_height = report.screen_height
    profile.max_runs = 1
    profile.post_macro_wait = 0.0
    profile.optimize_recording = True

    for pulse in profile.key_pulses:
        first = report.first_ability_times.get(pulse.key.casefold())
        if first is not None:
            pulse.start_after_seconds = max(0.0, first)
    return profile


def save_migration_report(path: Path, report: LegacyMacroReport) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _next_placement_click(
    events: list[Any],
    start_index: int,
    *,
    start_time: float,
    window_seconds: float,
) -> tuple[float, int, int] | None:
    for event in events[start_index + 1 :]:
        if not isinstance(event, dict):
            continue
        event_time = _event_time(event)
        if event_time - start_time > window_seconds:
            return None
        if event.get("type") == "key_down":
            key = _event_key(event)
            if key and key.isdigit():
                return None
        if event.get("type") != "mouse_button":
            continue
        data = event.get("data") or {}
        if data.get("button") != "left" or data.get("pressed") is not True:
            continue
        x = data.get("x")
        y = data.get("y")
        if isinstance(x, int) and isinstance(y, int):
            return event_time, x, y
    return None


def _event_key(event: Mapping[str, Any]) -> str:
    data = event.get("data") or {}
    key = data.get("key") or {}
    value = key.get("value")
    return value if isinstance(value, str) else ""


def _event_time(event: Mapping[str, Any]) -> float:
    return _number(event.get("t", 0.0), "event.t")


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number.")
    number = float(value)
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return number


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value
