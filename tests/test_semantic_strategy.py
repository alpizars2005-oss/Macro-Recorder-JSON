"""Tests for explicit TDS strategy documents."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macro_app.client_geometry import NormalizedPoint
from macro_app.semantic_strategy import (
    AlignCameraAction,
    EnableAbilityAction,
    PlaceTowerAction,
    SemanticStrategy,
    UpgradeTowerAction,
    load_semantic_strategy,
    save_semantic_strategy,
)


class SemanticStrategyTests(unittest.TestCase):
    def test_round_trip_semantic_strategy(self) -> None:
        strategy = SemanticStrategy(
            name="Wrecked Battlefield - Molten Farm",
            map_name="Wrecked Battlefield",
            difficulty="Molten",
            actions=[
                AlignCameraAction(),
                PlaceTowerAction("scout-1", 2, NormalizedPoint(0.45, 0.55)),
                UpgradeTowerAction("scout-1", levels=2),
                EnableAbilityAction("Call to Arms", "f"),
            ],
        )

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "strategy.json"
            save_semantic_strategy(path, strategy)
            restored = load_semantic_strategy(path)

        self.assertEqual(restored.name, strategy.name)
        self.assertEqual(restored.map_name, "Wrecked Battlefield")
        self.assertEqual(len(restored.actions), 4)
        self.assertIsInstance(restored.actions[1], PlaceTowerAction)

    def test_upgrade_before_placement_is_rejected(self) -> None:
        strategy = SemanticStrategy(
            name="Invalid",
            actions=[UpgradeTowerAction("farm-1")],
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
