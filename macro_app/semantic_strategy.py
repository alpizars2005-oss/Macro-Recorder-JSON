"""Validated semantic strategy documents for Tower Defense Simulator."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeAlias

from .camera_alignment import CameraAlignmentConfig
from .client_geometry import NormalizedPoint

SEMANTIC_STRATEGY_SCHEMA_VERSION = 1
MAX_STRATEGY_BYTES = 2 * 1024 * 1024
MAX_ACTIONS = 10_000


@dataclass(frozen=True, slots=True)
class AlignCameraAction:
    type: str = "align_camera"


@dataclass(frozen=True, slots=True)
class WaitAction:
    seconds: float
    type: str = "wait"


@dataclass(frozen=True, slots=True)
class PlaceTowerAction:
    tower_id: str
    slot: int
    point: NormalizedPoint
    retries: int = 5
    retry_delay: float = 0.20
    cancel_key: str = "q"
    type: str = "place_tower"


@dataclass(frozen=True, slots=True)
class UpgradeTowerAction:
    tower_id: str
    levels: int = 1
    path: int = 0
    retries: int = 10
    retry_delay: float = 0.20
    type: str = "upgrade_tower"


@dataclass(frozen=True, slots=True)
class EnableAbilityAction:
    name: str
    key: str
    interval_seconds: float = 0.50
    press_duration: float = 0.05
    type: str = "enable_ability"


@dataclass(frozen=True, slots=True)
class DisableAbilityAction:
    name: str
    type: str = "disable_ability"


SemanticAction: TypeAlias = (
    AlignCameraAction
    | WaitAction
    | PlaceTowerAction
    | UpgradeTowerAction
    | EnableAbilityAction
    | DisableAbilityAction
)


@dataclass(slots=True)
class SemanticStrategy:
    """One explicit, retryable TDS strategy."""

    name: str
    map_name: str = ""
    difficulty: str = ""
    window_title_contains: str = "Roblox"
    camera: CameraAlignmentConfig = field(default_factory=CameraAlignmentConfig)
    actions: list[SemanticAction] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Any) -> "SemanticStrategy":
        if not isinstance(payload, dict):
            raise ValueError("Semantic strategy must be a JSON object.")
        if payload.get("schema_version") != SEMANTIC_STRATEGY_SCHEMA_VERSION:
            raise ValueError("Unsupported semantic strategy schema.")

        name = _text(payload.get("name"), "name", maximum=120, required=True)
        map_name = _text(payload.get("map_name", ""), "map_name", maximum=120)
        difficulty = _text(payload.get("difficulty", ""), "difficulty", maximum=80)
        title = _text(
            payload.get("window_title_contains", "Roblox"),
            "window_title_contains",
            maximum=200,
        )
        raw_camera = payload.get("camera", {})
        if not isinstance(raw_camera, dict):
            raise ValueError("camera must be an object.")
        raw_actions = payload.get("actions", [])
        if not isinstance(raw_actions, list):
            raise ValueError("actions must be a list.")
        if len(raw_actions) > MAX_ACTIONS:
            raise ValueError(f"actions must contain at most {MAX_ACTIONS:,} items.")

        camera = CameraAlignmentConfig(
            enabled=_bool(raw_camera.get("enabled", True), "camera.enabled"),
            anchor=_normalized_point(raw_camera.get("anchor", {"x": 0.70, "y": 0.22}), "camera.anchor"),
            drag_overshoot_ratio=_number(
                raw_camera.get("drag_overshoot_ratio", 0.25),
                0.0,
                2.0,
                "camera.drag_overshoot_ratio",
            ),
            settle_seconds=_number(
                raw_camera.get("settle_seconds", 0.15),
                0.0,
                5.0,
                "camera.settle_seconds",
            ),
            zoom_key=_key(raw_camera.get("zoom_key", "o"), "camera.zoom_key"),
            zoom_passes=_integer(raw_camera.get("zoom_passes", 2), 0, 10, "camera.zoom_passes"),
            zoom_hold_seconds=_number(
                raw_camera.get("zoom_hold_seconds", 0.50),
                0.0,
                5.0,
                "camera.zoom_hold_seconds",
            ),
            zoom_back_steps=_integer(
                raw_camera.get("zoom_back_steps", 0),
                -50,
                50,
                "camera.zoom_back_steps",
            ),
            center_pointer_after=_bool(
                raw_camera.get("center_pointer_after", True),
                "camera.center_pointer_after",
            ),
        )
        strategy = cls(
            name=name,
            map_name=map_name,
            difficulty=difficulty,
            window_title_contains=title,
            camera=camera,
            actions=[_action_from_value(item, index) for index, item in enumerate(raw_actions)],
        )
        strategy.validate()
        return strategy

    def validate(self) -> None:
        placed: set[str] = set()
        enabled_abilities: set[str] = set()
        ability_keys: set[str] = set()

        for index, action in enumerate(self.actions):
            if isinstance(action, PlaceTowerAction):
                key = action.tower_id.casefold()
                if key in placed:
                    raise ValueError(f"actions[{index}] places duplicate tower_id '{action.tower_id}'.")
                placed.add(key)
            elif isinstance(action, UpgradeTowerAction):
                if action.tower_id.casefold() not in placed:
                    raise ValueError(
                        f"actions[{index}] upgrades unknown tower_id '{action.tower_id}'."
                    )
            elif isinstance(action, EnableAbilityAction):
                name = action.name.casefold()
                key = action.key.casefold()
                if name in enabled_abilities:
                    raise ValueError(f"actions[{index}] enables ability '{action.name}' twice.")
                if key in ability_keys:
                    raise ValueError(f"actions[{index}] reuses automatic ability key '{action.key}'.")
                enabled_abilities.add(name)
                ability_keys.add(key)
            elif isinstance(action, DisableAbilityAction):
                enabled_abilities.discard(action.name.casefold())

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SEMANTIC_STRATEGY_SCHEMA_VERSION,
            "name": self.name,
            "map_name": self.map_name,
            "difficulty": self.difficulty,
            "window_title_contains": self.window_title_contains,
            "camera": {
                "enabled": self.camera.enabled,
                "anchor": {"x": self.camera.anchor.x, "y": self.camera.anchor.y},
                "drag_overshoot_ratio": self.camera.drag_overshoot_ratio,
                "settle_seconds": self.camera.settle_seconds,
                "zoom_key": self.camera.zoom_key,
                "zoom_passes": self.camera.zoom_passes,
                "zoom_hold_seconds": self.camera.zoom_hold_seconds,
                "zoom_back_steps": self.camera.zoom_back_steps,
                "center_pointer_after": self.camera.center_pointer_after,
            },
            "actions": [_action_to_payload(action) for action in self.actions],
        }


def load_semantic_strategy(path: Path) -> SemanticStrategy:
    if path.stat().st_size > MAX_STRATEGY_BYTES:
        raise ValueError("Semantic strategy is larger than the 2 MB limit.")
    return SemanticStrategy.from_payload(json.loads(path.read_text(encoding="utf-8")))


def save_semantic_strategy(path: Path, strategy: SemanticStrategy) -> None:
    strategy.validate()
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(strategy.to_payload(), ensure_ascii=False, indent=2) + "\n"
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


def _action_from_value(value: Any, index: int) -> SemanticAction:
    label = f"actions[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    action_type = value.get("type")
    if action_type == "align_camera":
        return AlignCameraAction()
    if action_type == "wait":
        return WaitAction(seconds=_number(value.get("seconds"), 0.0, 24 * 60 * 60, f"{label}.seconds"))
    if action_type == "place_tower":
        return PlaceTowerAction(
            tower_id=_text(value.get("tower_id"), f"{label}.tower_id", maximum=100, required=True),
            slot=_integer(value.get("slot"), 1, 10, f"{label}.slot"),
            point=_normalized_point(value.get("point"), f"{label}.point"),
            retries=_integer(value.get("retries", 5), 1, 50, f"{label}.retries"),
            retry_delay=_number(value.get("retry_delay", 0.20), 0.0, 10.0, f"{label}.retry_delay"),
            cancel_key=_key(value.get("cancel_key", "q"), f"{label}.cancel_key"),
        )
    if action_type == "upgrade_tower":
        return UpgradeTowerAction(
            tower_id=_text(value.get("tower_id"), f"{label}.tower_id", maximum=100, required=True),
            levels=_integer(value.get("levels", 1), 1, 20, f"{label}.levels"),
            path=_integer(value.get("path", 0), 0, 2, f"{label}.path"),
            retries=_integer(value.get("retries", 10), 1, 100, f"{label}.retries"),
            retry_delay=_number(value.get("retry_delay", 0.20), 0.0, 10.0, f"{label}.retry_delay"),
        )
    if action_type == "enable_ability":
        return EnableAbilityAction(
            name=_text(value.get("name"), f"{label}.name", maximum=100, required=True),
            key=_key(value.get("key"), f"{label}.key"),
            interval_seconds=_number(
                value.get("interval_seconds", 0.50),
                0.10,
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
    if action_type == "disable_ability":
        return DisableAbilityAction(
            name=_text(value.get("name"), f"{label}.name", maximum=100, required=True)
        )
    raise ValueError(f"{label}.type is unsupported: {action_type!r}.")


def _action_to_payload(action: SemanticAction) -> dict[str, Any]:
    if isinstance(action, AlignCameraAction):
        return {"type": action.type}
    if isinstance(action, WaitAction):
        return {"type": action.type, "seconds": action.seconds}
    if isinstance(action, PlaceTowerAction):
        return {
            "type": action.type,
            "tower_id": action.tower_id,
            "slot": action.slot,
            "point": {"x": action.point.x, "y": action.point.y},
            "retries": action.retries,
            "retry_delay": action.retry_delay,
            "cancel_key": action.cancel_key,
        }
    if isinstance(action, UpgradeTowerAction):
        return {
            "type": action.type,
            "tower_id": action.tower_id,
            "levels": action.levels,
            "path": action.path,
            "retries": action.retries,
            "retry_delay": action.retry_delay,
        }
    if isinstance(action, EnableAbilityAction):
        return {
            "type": action.type,
            "name": action.name,
            "key": action.key,
            "interval_seconds": action.interval_seconds,
            "press_duration": action.press_duration,
        }
    if isinstance(action, DisableAbilityAction):
        return {"type": action.type, "name": action.name}
    raise TypeError(f"Unsupported action model: {type(action).__name__}")


def _normalized_point(value: Any, field_name: str) -> NormalizedPoint:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object with x and y values.")
    return NormalizedPoint(
        _number(value.get("x"), 0.0, 1.0, f"{field_name}.x"),
        _number(value.get("y"), 0.0, 1.0, f"{field_name}.y"),
    )


def _text(value: Any, field_name: str, *, maximum: int, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")
    result = value.strip()
    if required and not result:
        raise ValueError(f"{field_name} cannot be empty.")
    if len(result) > maximum:
        raise ValueError(f"{field_name} must be at most {maximum} characters.")
    return result


def _key(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 1 or not value.isprintable():
        raise ValueError(f"{field_name} must contain one printable character.")
    return value


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
    result = float(value)
    if not minimum <= result <= maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}.")
    return result
