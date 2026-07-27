"""Validated profiles for deterministic recorded strategy playback."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .automation_models import PixelTrigger

STRATEGY_SCHEMA_VERSION = 1
MAX_PROFILE_BYTES = 512 * 1024
MAX_PULSES = 8


@dataclass(slots=True)
class KeyPulse:
    """Repeatedly presses one key after a configured point in each run."""

    name: str
    key: str
    enabled: bool = True
    start_after_seconds: float = 0.0
    interval_seconds: float = 0.5
    press_duration: float = 0.05

    @classmethod
    def from_value(cls, value: Any, index: int) -> "KeyPulse":
        label = f"key_pulses[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object.")
        name = str(value.get("name", "")).strip()
        key = str(value.get("key", "")).strip()
        if not name or len(name) > 80:
            raise ValueError(f"{label}.name must contain 1 to 80 characters.")
        if len(key) != 1 or not key.isprintable():
            raise ValueError(f"{label}.key must contain one printable character.")
        return cls(
            name=name,
            key=key,
            enabled=_bool(value.get("enabled", True), f"{label}.enabled"),
            start_after_seconds=_number(
                value.get("start_after_seconds", 0.0),
                0.0,
                24 * 60 * 60,
                f"{label}.start_after_seconds",
            ),
            interval_seconds=_number(
                value.get("interval_seconds", 0.5),
                0.1,
                300.0,
                f"{label}.interval_seconds",
            ),
            press_duration=_number(
                value.get("press_duration", 0.05),
                0.01,
                1.0,
                f"{label}.press_duration",
            ),
        )


@dataclass(slots=True)
class RecordedStrategyProfile:
    """One repeatable strategy made from a human macro recording."""

    name: str = "Wrecked Battlefield - Molten"
    window_title_contains: str = "Roblox"
    macro_path: str = ""
    required_screen_width: int = 1920
    required_screen_height: int = 1080
    arming_delay: float = 3.0
    load_delay: float = 12.0
    max_runs: int = 1
    optimize_recording: bool = True
    key_pulses: list[KeyPulse] = field(default_factory=list)
    end_triggers: list[PixelTrigger] = field(default_factory=list)

    @classmethod
    def default_wrecked_battlefield(cls) -> "RecordedStrategyProfile":
        return cls(
            name="Wrecked Battlefield - Molten Farm",
            window_title_contains="Roblox",
            required_screen_width=1920,
            required_screen_height=1080,
            arming_delay=3.0,
            load_delay=12.0,
            max_runs=1,
            optimize_recording=True,
            key_pulses=[
                KeyPulse(
                    name="Call to Arms",
                    key="f",
                    enabled=True,
                    start_after_seconds=300.0,
                    interval_seconds=0.5,
                ),
                KeyPulse(
                    name="Drop The Beat",
                    key="b",
                    enabled=True,
                    start_after_seconds=337.0,
                    interval_seconds=0.5,
                ),
            ],
            end_triggers=[
                PixelTrigger(name="Restart Match", enabled=False),
                PixelTrigger(name="Play Again", enabled=False),
            ],
        )

    @classmethod
    def from_payload(cls, payload: Any) -> "RecordedStrategyProfile":
        if not isinstance(payload, dict):
            raise ValueError("Strategy profile must be a JSON object.")
        if payload.get("schema_version") != STRATEGY_SCHEMA_VERSION:
            raise ValueError("Unsupported strategy profile schema.")

        name = str(payload.get("name", "")).strip()
        title = str(payload.get("window_title_contains", "")).strip()
        macro_path = str(payload.get("macro_path", "")).strip()
        raw_pulses = payload.get("key_pulses", [])
        raw_triggers = payload.get("end_triggers", [])
        if not name or len(name) > 100:
            raise ValueError("name must contain 1 to 100 characters.")
        if len(title) > 200:
            raise ValueError("window_title_contains must be at most 200 characters.")
        if len(macro_path) > 4096:
            raise ValueError("macro_path is too long.")
        if not isinstance(raw_pulses, list) or len(raw_pulses) > MAX_PULSES:
            raise ValueError(f"key_pulses must contain at most {MAX_PULSES} items.")
        if not isinstance(raw_triggers, list) or len(raw_triggers) > 8:
            raise ValueError("end_triggers must contain at most 8 items.")

        profile = cls(
            name=name,
            window_title_contains=title,
            macro_path=macro_path,
            required_screen_width=_integer(
                payload.get("required_screen_width", 1920),
                320,
                100_000,
                "required_screen_width",
            ),
            required_screen_height=_integer(
                payload.get("required_screen_height", 1080),
                240,
                100_000,
                "required_screen_height",
            ),
            arming_delay=_number(payload.get("arming_delay", 3.0), 0.0, 60.0, "arming_delay"),
            load_delay=_number(payload.get("load_delay", 12.0), 0.0, 600.0, "load_delay"),
            max_runs=_integer(payload.get("max_runs", 1), 0, 100_000, "max_runs"),
            optimize_recording=_bool(
                payload.get("optimize_recording", True),
                "optimize_recording",
            ),
            key_pulses=[KeyPulse.from_value(item, index) for index, item in enumerate(raw_pulses)],
            end_triggers=[PixelTrigger.from_value(item, index) for index, item in enumerate(raw_triggers)],
        )
        profile.validate_ready(require_file=False)
        return profile

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = STRATEGY_SCHEMA_VERSION
        return payload

    def resolved_macro_path(self, profile_path: Path | None = None) -> Path | None:
        if not self.macro_path:
            return None
        path = Path(self.macro_path).expanduser()
        if not path.is_absolute() and profile_path is not None:
            path = profile_path.parent / path
        return path.resolve()

    def validate_ready(
        self,
        *,
        profile_path: Path | None = None,
        require_file: bool = True,
    ) -> None:
        if not self.macro_path:
            raise ValueError("Choose the recorded macro JSON file.")
        path = self.resolved_macro_path(profile_path)
        if require_file and (path is None or not path.is_file()):
            raise ValueError(f"Recorded macro not found: {path}")

        enabled_pulses = [pulse for pulse in self.key_pulses if pulse.enabled]
        keys = [pulse.key.casefold() for pulse in enabled_pulses]
        if len(keys) != len(set(keys)):
            raise ValueError("Enabled automatic abilities must use unique keys.")
        for trigger in self.end_triggers:
            trigger.validate_ready(allow_disabled=True)


def load_strategy_profile(path: Path) -> RecordedStrategyProfile:
    if path.stat().st_size > MAX_PROFILE_BYTES:
        raise ValueError("Strategy profile is larger than the 512 KB limit.")
    return RecordedStrategyProfile.from_payload(json.loads(path.read_text(encoding="utf-8")))


def save_strategy_profile(path: Path, profile: RecordedStrategyProfile) -> None:
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


def _bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be true or false.")
    return value


def _integer(value: Any, minimum: int, maximum: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


def _number(value: Any, minimum: float, maximum: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number.")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}.")
    return number
