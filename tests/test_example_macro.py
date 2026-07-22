"""Basic validation for the public example macro file."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_FILE = ROOT / "example_macro.json"
SUPPORTED_EVENT_TYPES = {
    "key_down",
    "key_up",
    "mouse_move",
    "mouse_button",
    "mouse_scroll",
}


class ExampleMacroTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))

    def test_schema_version_is_supported(self) -> None:
        self.assertEqual(self.payload["schema_version"], 1)

    def test_event_count_matches_event_list(self) -> None:
        self.assertEqual(self.payload["event_count"], len(self.payload["events"]))

    def test_timestamps_are_non_negative_and_ordered(self) -> None:
        timestamps = [float(event["t"]) for event in self.payload["events"]]
        self.assertTrue(all(timestamp >= 0 for timestamp in timestamps))
        self.assertEqual(timestamps, sorted(timestamps))

    def test_event_types_are_supported(self) -> None:
        for event in self.payload["events"]:
            self.assertIn(event["type"], SUPPORTED_EVENT_TYPES)
            self.assertIsInstance(event["data"], dict)

    def test_example_does_not_record_printable_keys(self) -> None:
        self.assertFalse(self.payload["settings"]["record_printable_keys"])


if __name__ == "__main__":
    unittest.main()
