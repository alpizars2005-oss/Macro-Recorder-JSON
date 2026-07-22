"""Tests for macro schema validation and optimization."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from macro_app.constants import MAX_EVENTS
from macro_app.model import MacroEvent, optimize_mouse_moves, validate_payload


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "example_macro.json").read_text(encoding="utf-8"))


class MacroModelTests(unittest.TestCase):
    def test_example_is_valid(self) -> None:
        document = validate_payload(EXAMPLE)
        self.assertEqual(len(document.events), EXAMPLE["event_count"])
        self.assertEqual(document.source_schema_version, 2)

    def test_schema_one_remains_compatible(self) -> None:
        payload = copy.deepcopy(EXAMPLE)
        payload.pop("schema_version")
        payload["settings"].pop("mouse_sample_mode")
        document = validate_payload(payload)
        self.assertEqual(document.source_schema_version, 1)
        self.assertEqual(document.mouse_sample_mode, "balanced")

    def test_count_mismatch_is_rejected(self) -> None:
        payload = copy.deepcopy(EXAMPLE)
        payload["event_count"] += 1
        with self.assertRaisesRegex(ValueError, "event_count"):
            validate_payload(payload)

    def test_out_of_order_events_are_rejected(self) -> None:
        payload = copy.deepcopy(EXAMPLE)
        payload["events"][1]["t"] = -0.1
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_reserved_f12_is_rejected(self) -> None:
        payload = copy.deepcopy(EXAMPLE)
        payload["events"] = [
            {
                "t": 0.0,
                "type": "key_down",
                "data": {"key": {"kind": "special", "value": "f12"}},
            }
        ]
        payload["event_count"] = 1
        with self.assertRaisesRegex(ValueError, "reserved"):
            validate_payload(payload)

    def test_event_limit_is_enforced_without_allocating_all_events(self) -> None:
        payload = copy.deepcopy(EXAMPLE)
        payload["events"] = [None] * (MAX_EVENTS + 1)
        payload["event_count"] = MAX_EVENTS + 1
        with self.assertRaisesRegex(ValueError, "more than"):
            validate_payload(payload)

    def test_mouse_move_optimization(self) -> None:
        events = [
            MacroEvent(0.00, "mouse_move", {"x": 1, "y": 1}),
            MacroEvent(0.01, "mouse_move", {"x": 2, "y": 2}),
            MacroEvent(0.10, "mouse_move", {"x": 3, "y": 3}),
            MacroEvent(0.11, "mouse_button", {"x": 3, "y": 3, "button": "left", "pressed": True}),
        ]
        optimized = optimize_mouse_moves(events, 0.05)
        self.assertEqual(len(optimized), 3)
        self.assertEqual(optimized[0].data, {"x": 2, "y": 2})


if __name__ == "__main__":
    unittest.main()
