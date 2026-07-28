"""Tests for importing useful data from older recorded TDS macros."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from macro_app.legacy_tds_import import analyze_legacy_macro, build_recorded_profile


class LegacyTDSImportTests(unittest.TestCase):
    def _write_macro(self, folder: str) -> Path:
        path = Path(folder) / "legacy.json"
        path.write_text(
            json.dumps(
                {
                    "screen": {"width": 1920, "height": 1080},
                    "duration_seconds": 12.0,
                    "events": [
                        {"t": 1.0, "type": "key_down", "data": {"key": {"kind": "char", "value": "5"}}},
                        {"t": 1.5, "type": "mouse_button", "data": {"x": 960, "y": 540, "button": "left", "pressed": True}},
                        {"t": 4.0, "type": "key_down", "data": {"key": {"kind": "char", "value": "2"}}},
                        {"t": 8.0, "type": "key_down", "data": {"key": {"kind": "char", "value": "f"}}},
                        {"t": 9.0, "type": "key_down", "data": {"key": {"kind": "char", "value": "b"}}},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_detects_candidate_and_unpaired_placement_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            report = analyze_legacy_macro(self._write_macro(folder))

        self.assertEqual(report.event_count, 5)
        self.assertEqual(len(report.placement_attempts), 2)
        farm, commander = report.placement_attempts
        self.assertEqual(farm.tower, "Farm")
        self.assertEqual(farm.confidence, "candidate")
        self.assertAlmostEqual(farm.normalized_x or 0.0, 960 / 1919)
        self.assertEqual(commander.tower, "Commander")
        self.assertEqual(commander.confidence, "unpaired")

    def test_builds_hybrid_profile_from_recorded_ability_times(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = self._write_macro(folder)
            report = analyze_legacy_macro(path)
            profile = build_recorded_profile(path, report)

        self.assertEqual(profile.macro_path, str(path.resolve()))
        self.assertEqual(profile.required_screen_width, 1920)
        self.assertEqual(profile.required_screen_height, 1080)
        self.assertEqual(profile.max_runs, 1)
        self.assertEqual(profile.post_macro_wait, 0.0)
        starts = {pulse.key: pulse.start_after_seconds for pulse in profile.key_pulses}
        self.assertEqual(starts["f"], 8.0)
        self.assertEqual(starts["b"], 9.0)


if __name__ == "__main__":
    unittest.main()
