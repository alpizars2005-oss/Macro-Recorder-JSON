"""Validation tests for macro JSON documents."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from macro_recorder import Recorder


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_FILE = ROOT / "example_macro.json"


class MacroValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))

    def test_example_payload_is_accepted(self) -> None:
        events, settings = Recorder.validate_payload(self.payload)
        self.assertEqual(len(events), self.payload["event_count"])
        self.assertTrue(settings["record_mouse_move"])
        self.assertFalse(settings["record_printable_keys"])

    def test_event_count_mismatch_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["event_count"] += 1
        with self.assertRaisesRegex(ValueError, "event_count"):
            Recorder.validate_payload(payload)

    def test_out_of_order_timestamp_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["events"][2]["t"] = 0.1
        with self.assertRaisesRegex(ValueError, "ascending order"):
            Recorder.validate_payload(payload)

    def test_unknown_event_type_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["events"][0]["type"] = "unknown"
        with self.assertRaisesRegex(ValueError, "not supported"):
            Recorder.validate_payload(payload)

    def test_reserved_f12_key_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["events"] = [
            {
                "t": 0.0,
                "type": "key_down",
                "data": {
                    "key": {
                        "kind": "special",
                        "value": "f12",
                    }
                },
            }
        ]
        payload["event_count"] = 1
        with self.assertRaisesRegex(ValueError, "reserved"):
            Recorder.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
