"""Validated semantic strategy documents for Tower Defense Simulator."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, TypeAlias

from .camera_alignment import CameraAlignmentConfig
from .client_geometry import NormalizedPoint
from .retry_policy import RetryPolicy

SEMANTIC_STRATEGY_SCHEMA_VERSION = 1
MAX_STRATEGY_BYTES = 2 * 1024 * 1024
MAX_ACTIONS = 10_000
MAX_DETECTORS = 100
MAX_LIST_ITEMS = 100


@dataclass(frozen=True, slots=True)
class StrategySource:
    """Attribution and discovery metadata for one strategy document."""

    author: str = ""
    url: str = ""
    license_name: str = ""
    tags: tuple[str, ...] = ()

    @classmethod
    def from_value(cls, value: Any) -> "StrategySource":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("source must be an object.")
        return cls(
            author=_text(value.get("author", ""), "source.author", maximum=120),
            url=_text(value.get("url", ""), "source.url", maximum=2048),
            license_name=_text(
                value.get("license", ""),
                "source.license",
                maximum=120,
            ),
            tags=_text_tuple(value.get("tags", []), "source.tags", maximum_items=30),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "url": self.url,
            "license": self.license_name,
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class StrategyRequirements:
    """Compatibility requirements shown before a strategy is executed."""

    game_mode: str = "Survival"
    goal: str = "Triumph"
    loadout: tuple[str, ...] = ()
    modifiers: tuple[str, ...] = ()
    recommended_width: int = 1920
    recommended_height: int = 1080
    windows_scale_percent: int = 100
    roblox_ui_scale: str = "Large"
    screen_shake_disabled: bool = True
    vertical_upgrades: str = "either"
    taskbar_visible: bool = True

    @classmethod
    def from_value(cls, value: Any) -> "StrategyRequirements":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("requirements must be an object.")
        vertical = _choice(
            value.get("vertical_upgrades", "either"),
            {"enabled", "disabled", "either"},
            "requirements.vertical_upgrades",
        )
        return cls(
            game_mode=_text(
                value.get("game_mode", "Survival"),
                "requirements.game_mode",
                maximum=80,
            ),
            goal=_choice(
                value.get("goal", "Triumph"),
                {"Triumph", "Lose", "Either"},
                "requirements.goal",
                case_sensitive=False,
            ).title(),
            loadout=_text_tuple(
                value.get("loadout", []),
                "requirements.loadout",
                maximum_items=10,
            ),
            modifiers=_text_tuple(
                value.get("modifiers", []),
                "requirements.modifiers",
                maximum_items=30,
            ),
            recommended_width=_integer(
                value.get("recommended_width", 1920),
                320,
                100_000,
                "requirements.recommended_width",
            ),
            recommended_height=_integer(
                value.get("recommended_height", 1080),
                240,
                100_000,
                "requirements.recommended_height",
            ),
            windows_scale_percent=_integer(
                value.get("windows_scale_percent", 100),
                50,
                500,
                "requirements.windows_scale_percent",
            ),
            roblox_ui_scale=_text(
                value.get("roblox_ui_scale", "Large"),
                "requirements.roblox_ui_scale",
                maximum=40,
            ),
            screen_shake_disabled=_bool(
                value.get("screen_shake_disabled", True),
                "requirements.screen_shake_disabled",
            ),
            vertical_upgrades=vertical,
            taskbar_visible=_bool(
                value.get("taskbar_visible", True),
                "requirements.taskbar_visible",
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "game_mode": self.game_mode,
            "goal": self.goal,
            "loadout": list(self.loadout),
            "modifiers": list(self.modifiers),
            "recommended_width": self.recommended_width,
            "recommended_height": self.recommended_height,
            "windows_scale_percent": self.windows_scale_percent,
            "roblox_ui_scale": self.roblox_ui_scale,
            "screen_shake_disabled": self.screen_shake_disabled,
            "vertical_upgrades": self.vertical_upgrades,
            "taskbar_visible": self.taskbar_visible,
        }


@dataclass(frozen=True, slots=True)
class NormalizedRegion:
    """One normalized client-relative rectangle for visual searches."""

    left: float = 0.0
    top: float = 0.0
    right: float = 1.0
    bottom: float = 1.0

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("Normalized detector regions must stay between 0.0 and 1.0.")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("Normalized detector regions must have positive width and height.")

    @classmethod
    def from_value(cls, value: Any, field_name: str) -> "NormalizedRegion":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object.")
        return cls(
            left=_number(value.get("left", 0.0), 0.0, 1.0, f"{field_name}.left"),
            top=_number(value.get("top", 0.0), 0.0, 1.0, f"{field_name}.top"),
            right=_number(value.get("right", 1.0), 0.0, 1.0, f"{field_name}.right"),
            bottom=_number(value.get("bottom", 1.0), 0.0, 1.0, f"{field_name}.bottom"),
        )

    def to_payload(self) -> dict[str, float]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
        }


@dataclass(frozen=True, slots=True)
class VisualDetector:
    """One priority-scheduled image template used by semantic actions."""

    name: str
    template_path: str
    priority: int = 0
    threshold: float = 0.80
    region: NormalizedRegion = field(default_factory=NormalizedRegion)
    required_matches: int = 2
    poll_interval: float = 0.10
    cooldown: float = 1.0

    @classmethod
    def from_value(cls, value: Any, index: int) -> "VisualDetector":
        label = f"detectors[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object.")
        template = _safe_relative_path(value.get("template_path"), f"{label}.template_path")
        return cls(
            name=_text(value.get("name"), f"{label}.name", maximum=100, required=True),
            template_path=template,
            priority=_integer(value.get("priority", 0), -1000, 1000, f"{label}.priority"),
            threshold=_number(value.get("threshold", 0.80), 0.0, 1.0, f"{label}.threshold"),
            region=NormalizedRegion.from_value(value.get("region"), f"{label}.region"),
            required_matches=_integer(
                value.get("required_matches", 2),
                1,
                20,
                f"{label}.required_matches",
            ),
            poll_interval=_number(
                value.get("poll_interval", 0.10),
                0.02,
                60.0,
                f"{label}.poll_interval",
            ),
            cooldown=_number(value.get("cooldown", 1.0), 0.0, 300.0, f"{label}.cooldown"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "template_path": self.template_path,
            "priority": self.priority,
            "threshold": self.threshold,
            "region": self.region.to_payload(),
            "required_matches": self.required_matches,
            "poll_interval": self.poll_interval,
            "cooldown": self.cooldown,
        }


@dataclass(frozen=True, slots=True)
class AlignCameraAction:
    type: str = "align_camera"


@dataclass(frozen=True, slots=True)
class WaitAction:
    seconds: float
    type: str = "wait"


@dataclass(frozen=True, slots=True)
class WaitForWaveAction:
    wave: int
    timeout_seconds: float = 180.0
    poll_interval: float = 0.20
    type: str = "wait_for_wave"


@dataclass(frozen=True, slots=True)
class PlaceTowerAction:
    tower_id: str
    slot: int
    point: NormalizedPoint
    retry: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(attempts=5, initial_delay=0.20)
    )
    expected_cost: int = 0
    wait_for_funds: bool = True
    confirmation_detector: str = ""
    cancel_key: str = "q"
    type: str = "place_tower"


@dataclass(frozen=True, slots=True)
class UpgradeTowerAction:
    tower_id: str
    levels: int = 1
    path: int = 0
    retry: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(attempts=10, initial_delay=0.20)
    )
    confirmation_detector: str = ""
    type: str = "upgrade_tower"


@dataclass(frozen=True, slots=True)
class UpgradeTowerToLevelAction:
    tower_id: str
    target_level: int
    path: int = 0
    retry: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(attempts=20, initial_delay=0.25)
    )
    level_detector: str = ""
    type: str = "upgrade_tower_to_level"


@dataclass(frozen=True, slots=True)
class SetAutoSkipAction:
    enabled: bool = True
    detector: str = ""
    type: str = "set_auto_skip"


@dataclass(frozen=True, slots=True)
class EnableAbilityAction:
    name: str
    key: str
    interval_seconds: float = 0.50
    press_duration: float = 0.05
    ready_detector: str = ""
    type: str = "enable_ability"


@dataclass(frozen=True, slots=True)
class DisableAbilityAction:
    name: str
    type: str = "disable_ability"


@dataclass(frozen=True, slots=True)
class ExpectResultAction:
    result: str = "Triumph"
    timeout_seconds: float = 600.0
    detector: str = ""
    type: str = "expect_result"


SemanticAction: TypeAlias = (
    AlignCameraAction
    | WaitAction
    | WaitForWaveAction
    | PlaceTowerAction
    | UpgradeTowerAction
    | UpgradeTowerToLevelAction
    | SetAutoSkipAction
    | EnableAbilityAction
    | DisableAbilityAction
    | ExpectResultAction
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
    source: StrategySource = field(default_factory=StrategySource)
    requirements: StrategyRequirements = field(default_factory=StrategyRequirements)
    detectors: list[VisualDetector] = field(default_factory=list)

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
        raw_detectors = payload.get("detectors", [])
        if not isinstance(raw_detectors, list) or len(raw_detectors) > MAX_DETECTORS:
            raise ValueError(f"detectors must contain at most {MAX_DETECTORS} items.")

        camera = CameraAlignmentConfig(
            enabled=_bool(raw_camera.get("enabled", True), "camera.enabled"),
            anchor=_normalized_point(
                raw_camera.get("anchor", {"x": 0.70, "y": 0.22}),
                "camera.anchor",
            ),
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
            source=StrategySource.from_value(payload.get("source")),
            requirements=StrategyRequirements.from_value(payload.get("requirements")),
            detectors=[
                VisualDetector.from_value(item, index)
                for index, item in enumerate(raw_detectors)
            ],
        )
        strategy.validate()
        return strategy

    def validate(self) -> None:
        placed: set[str] = set()
        enabled_abilities: set[str] = set()
        ability_keys: set[str] = set()
        detector_names = {detector.name.casefold() for detector in self.detectors}
        if len(detector_names) != len(self.detectors):
            raise ValueError("Detector names must be unique.")

        for index, action in enumerate(self.actions):
            if isinstance(action, PlaceTowerAction):
                key = action.tower_id.casefold()
                if key in placed:
                    raise ValueError(f"actions[{index}] places duplicate tower_id '{action.tower_id}'.")
                placed.add(key)
                self._validate_detector_reference(
                    action.confirmation_detector,
                    detector_names,
                    f"actions[{index}].confirmation_detector",
                )
            elif isinstance(action, (UpgradeTowerAction, UpgradeTowerToLevelAction)):
                if action.tower_id.casefold() not in placed:
                    raise ValueError(
                        f"actions[{index}] upgrades unknown tower_id '{action.tower_id}'."
                    )
                detector = (
                    action.confirmation_detector
                    if isinstance(action, UpgradeTowerAction)
                    else action.level_detector
                )
                self._validate_detector_reference(
                    detector,
                    detector_names,
                    f"actions[{index}].detector",
                )
            elif isinstance(action, EnableAbilityAction):
                name = action.name.casefold()
                key = action.key.casefold()
                if name in enabled_abilities:
                    raise ValueError(f"actions[{index}] enables ability '{action.name}' twice.")
                if key in ability_keys:
                    raise ValueError(f"actions[{index}] reuses automatic ability key '{action.key}'.")
                self._validate_detector_reference(
                    action.ready_detector,
                    detector_names,
                    f"actions[{index}].ready_detector",
                )
                enabled_abilities.add(name)
                ability_keys.add(key)
            elif isinstance(action, DisableAbilityAction):
                enabled_abilities.discard(action.name.casefold())
            elif isinstance(action, SetAutoSkipAction):
                self._validate_detector_reference(
                    action.detector,
                    detector_names,
                    f"actions[{index}].detector",
                )
            elif isinstance(action, ExpectResultAction):
                self._validate_detector_reference(
                    action.detector,
                    detector_names,
                    f"actions[{index}].detector",
                )

    @staticmethod
    def _validate_detector_reference(
        name: str,
        known: set[str],
        field_name: str,
    ) -> None:
        if name and name.casefold() not in known:
            raise ValueError(f"{field_name} references unknown detector '{name}'.")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SEMANTIC_STRATEGY_SCHEMA_VERSION,
            "name": self.name,
            "map_name": self.map_name,
            "difficulty": self.difficulty,
            "window_title_contains": self.window_title_contains,
            "source": self.source.to_payload(),
            "requirements": self.requirements.to_payload(),
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
            "detectors": [detector.to_payload() for detector in self.detectors],
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
        return WaitAction(
            seconds=_number(value.get("seconds"), 0.0, 24 * 60 * 60, f"{label}.seconds")
        )
    if action_type == "wait_for_wave":
        return WaitForWaveAction(
            wave=_integer(value.get("wave"), 1, 10_000, f"{label}.wave"),
            timeout_seconds=_number(
                value.get("timeout_seconds", 180.0),
                1.0,
                24 * 60 * 60,
                f"{label}.timeout_seconds",
            ),
            poll_interval=_number(
                value.get("poll_interval", 0.20),
                0.02,
                60.0,
                f"{label}.poll_interval",
            ),
        )
    if action_type == "place_tower":
        retry = _retry_from_action(
            value,
            label,
            default_attempts=5,
            default_delay=0.20,
        )
        return PlaceTowerAction(
            tower_id=_text(value.get("tower_id"), f"{label}.tower_id", maximum=100, required=True),
            slot=_integer(value.get("slot"), 1, 10, f"{label}.slot"),
            point=_normalized_point(value.get("point"), f"{label}.point"),
            retry=retry,
            expected_cost=_integer(value.get("expected_cost", 0), 0, 10**12, f"{label}.expected_cost"),
            wait_for_funds=_bool(value.get("wait_for_funds", True), f"{label}.wait_for_funds"),
            confirmation_detector=_text(
                value.get("confirmation_detector", ""),
                f"{label}.confirmation_detector",
                maximum=100,
            ),
            cancel_key=_key(value.get("cancel_key", "q"), f"{label}.cancel_key"),
        )
    if action_type == "upgrade_tower":
        retry = _retry_from_action(
            value,
            label,
            default_attempts=10,
            default_delay=0.20,
        )
        return UpgradeTowerAction(
            tower_id=_text(value.get("tower_id"), f"{label}.tower_id", maximum=100, required=True),
            levels=_integer(value.get("levels", 1), 1, 20, f"{label}.levels"),
            path=_integer(value.get("path", 0), 0, 2, f"{label}.path"),
            retry=retry,
            confirmation_detector=_text(
                value.get("confirmation_detector", ""),
                f"{label}.confirmation_detector",
                maximum=100,
            ),
        )
    if action_type == "upgrade_tower_to_level":
        return UpgradeTowerToLevelAction(
            tower_id=_text(value.get("tower_id"), f"{label}.tower_id", maximum=100, required=True),
            target_level=_integer(value.get("target_level"), 1, 20, f"{label}.target_level"),
            path=_integer(value.get("path", 0), 0, 2, f"{label}.path"),
            retry=RetryPolicy.from_value(
                value.get("retry"),
                f"{label}.retry",
                default_attempts=20,
                default_delay=0.25,
            ),
            level_detector=_text(
                value.get("level_detector", ""),
                f"{label}.level_detector",
                maximum=100,
            ),
        )
    if action_type == "set_auto_skip":
        return SetAutoSkipAction(
            enabled=_bool(value.get("enabled", True), f"{label}.enabled"),
            detector=_text(value.get("detector", ""), f"{label}.detector", maximum=100),
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
            ready_detector=_text(
                value.get("ready_detector", ""),
                f"{label}.ready_detector",
                maximum=100,
            ),
        )
    if action_type == "disable_ability":
        return DisableAbilityAction(
            name=_text(value.get("name"), f"{label}.name", maximum=100, required=True)
        )
    if action_type == "expect_result":
        return ExpectResultAction(
            result=_choice(
                value.get("result", "Triumph"),
                {"Triumph", "Lose", "Either"},
                f"{label}.result",
                case_sensitive=False,
            ).title(),
            timeout_seconds=_number(
                value.get("timeout_seconds", 600.0),
                1.0,
                24 * 60 * 60,
                f"{label}.timeout_seconds",
            ),
            detector=_text(value.get("detector", ""), f"{label}.detector", maximum=100),
        )
    raise ValueError(f"{label}.type is unsupported: {action_type!r}.")


def _retry_from_action(
    value: dict[str, Any],
    label: str,
    *,
    default_attempts: int,
    default_delay: float,
) -> RetryPolicy:
    if "retry" in value:
        return RetryPolicy.from_value(
            value.get("retry"),
            f"{label}.retry",
            default_attempts=default_attempts,
            default_delay=default_delay,
        )
    # Compatibility with the first semantic prototype.
    attempts = value.get("retries", default_attempts)
    delay = value.get("retry_delay", default_delay)
    return RetryPolicy(
        attempts=_integer(attempts, 1, 100, f"{label}.retries"),
        initial_delay=_number(delay, 0.0, 30.0, f"{label}.retry_delay"),
    )


def _action_to_payload(action: SemanticAction) -> dict[str, Any]:
    if isinstance(action, AlignCameraAction):
        return {"type": action.type}
    if isinstance(action, WaitAction):
        return {"type": action.type, "seconds": action.seconds}
    if isinstance(action, WaitForWaveAction):
        return {
            "type": action.type,
            "wave": action.wave,
            "timeout_seconds": action.timeout_seconds,
            "poll_interval": action.poll_interval,
        }
    if isinstance(action, PlaceTowerAction):
        return {
            "type": action.type,
            "tower_id": action.tower_id,
            "slot": action.slot,
            "point": {"x": action.point.x, "y": action.point.y},
            "retry": action.retry.to_payload(),
            "expected_cost": action.expected_cost,
            "wait_for_funds": action.wait_for_funds,
            "confirmation_detector": action.confirmation_detector,
            "cancel_key": action.cancel_key,
        }
    if isinstance(action, UpgradeTowerAction):
        return {
            "type": action.type,
            "tower_id": action.tower_id,
            "levels": action.levels,
            "path": action.path,
            "retry": action.retry.to_payload(),
            "confirmation_detector": action.confirmation_detector,
        }
    if isinstance(action, UpgradeTowerToLevelAction):
        return {
            "type": action.type,
            "tower_id": action.tower_id,
            "target_level": action.target_level,
            "path": action.path,
            "retry": action.retry.to_payload(),
            "level_detector": action.level_detector,
        }
    if isinstance(action, SetAutoSkipAction):
        return {
            "type": action.type,
            "enabled": action.enabled,
            "detector": action.detector,
        }
    if isinstance(action, EnableAbilityAction):
        return {
            "type": action.type,
            "name": action.name,
            "key": action.key,
            "interval_seconds": action.interval_seconds,
            "press_duration": action.press_duration,
            "ready_detector": action.ready_detector,
        }
    if isinstance(action, DisableAbilityAction):
        return {"type": action.type, "name": action.name}
    if isinstance(action, ExpectResultAction):
        return {
            "type": action.type,
            "result": action.result,
            "timeout_seconds": action.timeout_seconds,
            "detector": action.detector,
        }
    raise TypeError(f"Unsupported action model: {type(action).__name__}")


def _normalized_point(value: Any, field_name: str) -> NormalizedPoint:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object with x and y values.")
    return NormalizedPoint(
        _number(value.get("x"), 0.0, 1.0, f"{field_name}.x"),
        _number(value.get("y"), 0.0, 1.0, f"{field_name}.y"),
    )


def _safe_relative_path(value: Any, field_name: str) -> str:
    text = _text(value, field_name, maximum=4096, required=True).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field_name} must be a safe relative path.")
    return str(path)


def _text_tuple(
    value: Any,
    field_name: str,
    *,
    maximum_items: int = MAX_LIST_ITEMS,
) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise ValueError(f"{field_name} must be a list with at most {maximum_items} items.")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _text(item, f"{field_name}[{index}]", maximum=120, required=True)
        key = text.casefold()
        if key in seen:
            raise ValueError(f"{field_name} contains duplicate value '{text}'.")
        seen.add(key)
        result.append(text)
    return tuple(result)


def _choice(
    value: Any,
    choices: set[str],
    field_name: str,
    *,
    case_sensitive: bool = True,
) -> str:
    text = _text(value, field_name, maximum=100, required=True)
    if case_sensitive:
        if text not in choices:
            raise ValueError(f"{field_name} must be one of: {', '.join(sorted(choices))}.")
        return text
    mapping = {choice.casefold(): choice for choice in choices}
    try:
        return mapping[text.casefold()]
    except KeyError as exc:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(choices))}.") from exc


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
