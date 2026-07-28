"""Tests for explicit TDS strategy documents."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macro_app.client_geometry import NormalizedPoint
from macro_app.retry_policy import RetryPolicy
from macro_app.semantic_strategy import (
    AlignCameraAction,
    EnableAbilityAction,
    ExpectResultAction,
    PlaceTowerAction,
    SemanticStrategy,
    StrategyRequirements,
    StrategySource,
    UpgradeTowerAction,
    UpgradeTowerToLevelAction,
    VisualDetector,
    load_semantic_strategy,
    save_semantic_strategy,
)


class SemanticStrategyTests(unittest.TestCase):
    def test_round_trip_semantic_strategy(self) -> None:
        strategy = SemanticStrategy(
            name="Wrecked Battlefield - Molten Farm",
            map_name="Wrecked Battlefield",
            difficulty="Molten",
            source=StrategySource(
                author="Pizzaroles",
                license_name="MIT",
                tags=("coins", "solo"),
            ),
            requirements=StrategyRequirements(
                loadout=("Farm", "Scout", "Minigunner", "Commander", "DJ Booth"),
                modifiers=("Hidden Enemies",),
            ),
            detectors=[
                VisualDetector(
                    name="tower-panel",
                    template_path="templates/tower-panel.png",
                    priority=50,
                ),
                VisualDetector(
                    name="triumph",
                    template_path="templates/triumph.png",
                    priority=100,
                ),
            ],
            actions=[
                AlignCameraAction(),
                PlaceTowerAction(
                    "scout-1",
                    2,
                    NormalizedPoint(0.45, 0.55),
                    retry=RetryPolicy(attempts=8, jitter_radius=0.01),
                    confirmation_detector="tower-panel",
                ),
                UpgradeTowerToLevelAction(
                    "scout-1",
                    target_level=2,
                    level_detector="tower-panel",
                ),
                EnableAbilityAction("Call to Arms", "f"),
                ExpectResultAction(detector="triumph"),
            ],
        )

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "strategy.json"
            save_semantic_strategy(path, strategy)
            restored = load_semantic_strategy(path)

        self.assertEqual(restored.name, strategy.name)
        self.assertEqual(restored.map_name, "Wrecked Battlefield")
        self.assertEqual(restored.source.author, "Pizzaroles")
        self.assertEqual(restored.requirements.loadout[0], "Farm")
        self.assertEqual(len(restored.detectors), 2)
        self.assertEqual(len(restored.actions), 5)
        self.assertIsInstance(restored.actions[1], PlaceTowerAction)
        self.assertEqual(restored.actions[1].retry.attempts, 8)

    def test_upgrade_before_placement_is_rejected(self) -> None:
        strategy = SemanticStrategy(
            name="Invalid",
            actions=[UpgradeTowerAction("farm-1")],
        )

        with self.assertRaisesRegex(ValueError, "unknown tower_id"):
            strategy.validate()

    def test_target_level_upgrade_before_placement_is_rejected(self) -> None:
        strategy = SemanticStrategy(
            name="Invalid",
            actions=[UpgradeTowerToLevelAction("farm-1", target_level=5)],
        )

        with self.assertRaisesRegex(ValueError, "unknown tower_id"):
            strategy.validate()

    def test_duplicate_tower_identifier_is_rejected(self) -> None:
        strategy = SemanticStrategy(
            name="Invalid",
            actions=[
                PlaceTowerAction("farm-1", 1, NormalizedPoint(0.2, 0.5)),
                PlaceTowerAction("FARM-1", 1, NormalizedPoint(0.3, 0.5)),
            ],
        )

        with self.assertRaisesRegex(ValueError, "duplicate tower_id"):
            strategy.validate()

    def test_duplicate_automatic_ability_key_is_rejected(self) -> None:
        strategy = SemanticStrategy(
            name="Invalid",
            actions=[
                EnableAbilityAction("Call to Arms", "f"),
                EnableAbilityAction("Another Ability", "F"),
            ],
        )

        with self.assertRaisesRegex(ValueError, "reuses automatic ability key"):
            strategy.validate()

    def test_unknown_detector_reference_is_rejected(self) -> None:
        strategy = SemanticStrategy(
            name="Invalid",
            actions=[
                PlaceTowerAction(
                    "farm-1",
                    1,
                    NormalizedPoint(0.2, 0.5),
                    confirmation_detector="missing",
                )
            ],
        )

        with self.assertRaisesRegex(ValueError, "unknown detector"):
            strategy.validate()

    def test_unsafe_template_path_is_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "name": "Invalid",
            "detectors": [
                {
                    "name": "bad",
                    "template_path": "../outside.png",
                }
            ],
            "actions": [],
        }

        with self.assertRaisesRegex(ValueError, "safe relative path"):
            SemanticStrategy.from_payload(payload)

    def test_legacy_retry_fields_still_load(self) -> None:
        payload = {
            "schema_version": 1,
            "name": "Legacy",
            "actions": [
                {
                    "type": "place_tower",
                    "tower_id": "farm-1",
                    "slot": 1,
                    "point": {"x": 0.2, "y": 0.5},
                    "retries": 7,
                    "retry_delay": 0.3,
                }
            ],
        }

        restored = SemanticStrategy.from_payload(payload)
        action = restored.actions[0]

        self.assertIsInstance(action, PlaceTowerAction)
        self.assertEqual(action.retry.attempts, 7)
        self.assertEqual(action.retry.initial_delay, 0.3)

    def test_unknown_action_type_is_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "name": "Invalid",
            "actions": [{"type": "teleport_tower"}],
        }

        with self.assertRaisesRegex(ValueError, "unsupported"):
            SemanticStrategy.from_payload(payload)


if __name__ == "__main__":
    unittest.main()
