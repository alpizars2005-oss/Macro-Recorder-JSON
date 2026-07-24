"""Validated configuration models for visible local automation workflows."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROFILE_SCHEMA_VERSION = 1
MAX_COORDINATE = 100_000
MAX_TRIGGER_COUNT = 8
MAX_TITLE_LENGTH = 200


@dataclass(slots=True, frozen=True)
class Point:
    """One absolute virtual-screen coordinate."""

    x: int
    y: int

    @classmethod
    def from_value(cls, value: Any, field_name: str) -> "Point":
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object with x and y values.")
        x = value.get("x")
        y = value.get("y")
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError(f"{field_name}.x must be an integer.")
        if isinstance(y, bool) or not isinstance(y, int):
            raise ValueError(f"{field_name}.y must be an integer.")
        if abs(x) > MAX_COORDINATE or abs(y) > MAX_COORDINATE:
            raise ValueError(f"{field_name} is outside the allowed coordinate range.")
        return cls(x=x, y=y)


@dataclass(slots=True, frozen=True)
class RGBColor:
    """An RGB color used by a pixel trigger."""

    r: int
    g: int
    b: int

    @classmethod
    def from_value(cls, value: Any, field_name: str) -> "RGBColor":
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an RGB object.")
        channels: list[int] = []
        for channel_name in ("r", "g", "b"):
            channel = value.get(channel_name)
            if isinstance(channel, bool) or not isinstance(channel, int):
                raise ValueError(f"{field_name}.{channel_name} must be an integer.")
            if not 0 <= channel <= 255:
                raise ValueError(f"{field_name}.{channel_name} must be between 0 and 255.")
            channels.append(channel)
        return cls(*channels)

    def as_tuple(self) -> tuple[int, int, int]:
        return self.r, self.g, self.b


@dataclass(slots=True)
class PixelTrigger:
    """A visible screen condition that clicks one configured location."""

    name: str
    enabled: bool = False
    sample_point: Point | None = None
    click_point: Point | None = None
    target_color: RGBColor | None = None
    tolerance: int = 30
    sample_radius: int = 1
    required_matches: int = 3
    poll_interval: float = 0.08
    cooldown: float = 3.0

    @classmethod
    def from_value(cls, value: Any, index: int) -> "PixelTrigger":
        field_name = f"triggers[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object.")
        name = str(value.get("name", "")).strip()
        if not name or len(name) > 80:
            raise ValueError(f"{field_name}.name must contain 1 to 80 characters.")
        trigger = cls(
            name=name,
            enabled=_bool_value(value.get("enabled", False), f"{field_name}.enabled"),
            sample_point=(
                Point.from_value(value["sample_point"], f"{field_name}.sample_point")
                if value.get("sample_point") is not None
                else None
            ),
            click_point=(
                Point.from_value(value["click_point"], f"{field_name}.click_point")
                if value.get("click_point") is not None
                else None
            ),
            target_color=(
                RGBColor.from_value(value["target_color"], f"{field_name}.target_color")
                if value.get("target_color") is not None
                else None
            ),
            tolerance=_bounded_int(value.get("tolerance", 30), 0, 255, f"{field_name}.tolerance"),
            sample_radius=_bounded_int(value.get("sample_radius", 1), 0, 5, f"{field_name}.sample_radius"),
            required_matches=_bounded_int(
                value.get("required_matches", 3), 1, 20, f"{field_name}.required_matches"
            ),
            poll_interval=_bounded_float(
                value.get("poll_interval", 0.08), 0.02, 5.0, f"{field_name}.poll_interval"
            ),
            cooldown=_bounded_float(value.get("cooldown", 3.0), 0.0, 300.0, f"{field_name}.cooldown"),
        )
        trigger.validate_ready(allow_disabled=True)
        return trigger

    def validate_ready(self, *, allow_disabled: bool = False) -> None:
        if allow_disabled and not self.enabled:
            return
        if self.sample_point is None:
            raise ValueError(f"Trigger '{self.name}' has no sample point.")
        if self.click_point is None:
            raise ValueError(f"Trigger '{self.name}' has no click point.")
        if self.target_color is None:
            raise ValueError(f"Trigger '{self.name}' has no target color.")


@dataclass(slots=True)
class CommanderChain:
    """Cycles through Commander positions and presses the ability button."""

    enabled: bool = False
    commander_points: list[Point] = field(default_factory=list)
    ability_point: Point | None = None
    interval_seconds: float = 10.0
    click_delay: float = 0.18
    cycle_pause: float = 0.35

    @classmethod
    def from_value(cls, value: Any) -> "CommanderChain":
        if not isinstance(value, dict):
            raise ValueError("commander must be an object.")
        raw_points = value.get("commander_points", [])
        if not isinstance(raw_points, list) or len(raw_points) > 6:
            raise ValueError("commander.commander_points must be a list with at most 6 points.")
        chain = cls(
            enabled=_bool_value(value.get("enabled", False), "commander.enabled"),
            commander_points=[
                Point.from_value(point, f"commander.commander_points[{index}]")
                for index, point in enumerate(raw_points)
            ],
            ability_point=(
                Point.from_value(value["ability_point"], "commander.ability_point")
                if value.get("ability_point") is not None
                else None
            ),
            interval_seconds=_bounded_float(
                value.get("interval_seconds", 10.0), 0.5, 120.0, "commander.interval_seconds"
            ),
            click_delay=_bounded_float(value.get("click_delay", 0.18), 0.02, 5.0, "commander.click_delay"),
            cycle_pause=_bounded_float(value.get("cycle_pause", 0.35), 0.0, 10.0, "commander.cycle_pause"),
        )
        chain.validate_ready(allow_disabled=True)
        return chain

    def validate_ready(self, *, allow_disabled: bool = False) -> None:
        if allow_disabled and not self.enabled:
            return
        if not self.commander_points:
            raise ValueError("Commander chain has no Commander positions.")
        if self.ability_point is None:
            raise ValueError("Commander chain has no ability-button position.")


@dataclass(slots=True)
class AutomationProfile:
    """One local automation workflow profile."""

    name: str = "TDS Commander"
    window_title_contains: str = "Roblox"
    start_macro: str = ""
    run_macro_on_start: bool = False
    load_delay: float = 8.0
    max_runs: int = 0
    triggers: list[PixelTrigger] = field(default_factory=list)
    commander: CommanderChain = field(default_factory=CommanderChain)

    @classmethod
    def default_tds(cls) -> "AutomationProfile":
        return cls(
            name="TDS Commander",
            window_title_contains="Roblox",
            triggers=[
                PixelTrigger(name="Restart", enabled=False),
                PixelTrigger(name="Replay", enabled=False),
            ],
        )

    @classmethod
    def from_payload(cls, payload: Any) -> "AutomationProfile":
        if not isinstance(payload, dict):
            raise ValueError("Automation profile must be a JSON object.")
        schema = payload.get("schema_version")
        if schema != PROFILE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported automation profile schema: {schema!r}.")
        raw_triggers = payload.get("triggers", [])
        if not isinstance(raw_triggers, list) or len(raw_triggers) > MAX_TRIGGER_COUNT:
            raise ValueError(f"triggers must be a list with at most {MAX_TRIGGER_COUNT} items.")
        name = str(payload.get("name", "")).strip()
        if not name or len(name) > 100:
            raise ValueError("name must contain 1 to 100 characters.")
        title = str(payload.get("window_title_contains", "")).strip()
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"window_title_contains must be at most {MAX_TITLE_LENGTH} characters.")
        profile = cls(
            name=name,
            window_title_contains=title,
            start_macro=str(payload.get("start_macro", "")).strip(),
            run_macro_on_start=_bool_value(payload.get("run_macro_on_start", False), "run_macro_on_start"),
            load_delay=_bounded_float(payload.get("load_delay", 8.0), 0.0, 600.0, "load_delay"),
            max_runs=_bounded_int(payload.get("max_runs", 0), 0, 100_000, "max_runs"),
            triggers=[PixelTrigger.from_value(item, index) for index, item in enumerate(raw_triggers)],
            commander=CommanderChain.from_value(payload.get("commander", {})),
        )
        if len(profile.start_macro) > 4096:
            raise ValueError("start_macro must be at most 4096 characters.")
        names = [trigger.name.casefold() for trigger in profile.triggers]
        if len(names) != len(set(names)):
            raise ValueError("Trigger names must be unique.")
        return profile

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = PROFILE_SCHEMA_VERSION
        return payload

    def validate_ready(self) -> None:
        names = [trigger.name.casefold() for trigger in self.triggers]
        if len(names) != len(set(names)):
            raise ValueError("Trigger names must be unique.")
        enabled_triggers = [trigger for trigger in self.triggers if trigger.enabled]
        if not enabled_triggers and not self.commander.enabled and not self.run_macro_on_start:
            raise ValueError("Enable at least one trigger, the Commander chain, or the start macro.")
        for trigger in enabled_triggers:
            trigger.validate_ready()
        self.commander.validate_ready(allow_disabled=True)
        if self.run_macro_on_start and not self.start_macro:
            raise ValueError("Choose a start macro or disable 'run macro on start'.")

    def resolved_macro_path(self, profile_path: Path | None = None) -> Path | None:
        if not self.start_macro:
            return None
        path = Path(self.start_macro).expanduser()
        if not path.is_absolute() and profile_path is not None:
            path = profile_path.parent / path
        return path.resolve()


def load_profile(path: Path) -> AutomationProfile:
    if path.stat().st_size > 512 * 1024:
        raise ValueError("Automation profile is larger than the 512 KB limit.")
    return AutomationProfile.from_payload(json.loads(path.read_text(encoding="utf-8")))


def save_profile(path: Path, profile: AutomationProfile) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(profile.to_payload(), ensure_ascii=False, indent=2) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(serialized)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink(missing_ok=True)


def _bool_value(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be true or false.")
    return value


def _bounded_int(value: Any, minimum: int, maximum: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


def _bounded_float(value: Any, minimum: float, maximum: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number.")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}.")
    return number
