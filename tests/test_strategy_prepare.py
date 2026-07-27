"""Tests for cleaning recorded strategy input streams."""

from __future__ import annotations

import unittest

from macro_app.model import MacroEvent
from macro_app.strategy_prepare import prepare_recorded_strategy


class StrategyPreparationTests(unittest.TestCase):
    def test_removes_ability_keys_and_idle_mouse_noise(self) -> None:
        events = [
            MacroEvent(0.1, "mouse_move", {"x": 10, "y": 10}),
            MacroEvent(0.2, "key_down", {"key": {"kind": "char", "value": "f"}}),
            MacroEvent(0.3, "key_up", {"key": {"kind": "char", "value": "f"}}),
            MacroEvent(0.4, "mouse_button", {"x": 20, "y": 20, "button": "right", "pressed": True}),
            MacroEvent(0.5, "mouse_move", {"x": 25, "y": 25}),
            MacroEvent(0.6, "mouse_button", {"x": 25, "y": 25, "button": "right", "pressed": False}),
        ]

        prepared, stats = prepare_recorded_strategy(events, automatic_keys={"f"})

        self.assertEqual([event.type for event in prepared], ["mouse_button", "mouse_move", "mouse_button"])
        self.assertEqual(stats.removed_idle_mouse_moves, 1)
        self.assertEqual(stats.removed_ability_key_events, 2)

    def test_collapses_key_repeat_and_balances_release(self) -> None:
        events = [
            MacroEvent(0.1, "key_down", {"key": {"kind": "char", "value": "a"}}),
            MacroEvent(0.2, "key_down", {"key": {"kind": "char", "value": "a"}}),
            MacroEvent(0.3, "key_down", {"key": {"kind": "char", "value": "d"}}),
            MacroEvent(0.4, "key_up", {"key": {"kind": "char", "value": "a"}}),
        ]

        prepared, stats = prepare_recorded_strategy(events)

        self.assertEqual(stats.collapsed_repeated_key_down, 1)
        self.assertEqual(stats.added_key_releases, 1)
        self.assertEqual(prepared[-1].type, "key_up")
        self.assertEqual(prepared[-1].data["key"]["value"], "d")


if __name__ == "__main__":
    unittest.main()
