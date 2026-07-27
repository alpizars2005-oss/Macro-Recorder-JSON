"""Tests for recorded strategy profile validation and storage."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macro_app.strategy_models import (
    RecordedStrategyProfile,
    load_strategy_profile,
    save_strategy_profile,
)


class StrategyModelTests(unittest.TestCase):
    def test_default_wrecked_profile_has_automatic_abilities(self) -> None:
        profile = RecordedStrategyProfile.default_wrecked_battlefield()

        self.assertEqual(profile.required_screen_width, 1920)
        self.assertEqual(profile.required_screen_height, 1080)
        self.assertEqual([pulse.key for pulse in profile.key_pulses], ["f", "b"])
        self.assertEqual(profile.key_pulses[0].start_after_seconds, 300.0)
        self.assertEqual(profile.key_pulses[1].start_after_seconds, 337.0)
        self.assertEqual(profile.post_macro_wait, 60.0)

    def test_round_trip_profile(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            macro_path = Path(folder) / "run.json"
            macro_path.write_text("{}", encoding="utf-8")
            profile_path = Path(folder) / "strategy.json"
            profile = RecordedStrategyProfile.default_wrecked_battlefield()
            profile.macro_path = str(macro_path)

            save_strategy_profile(profile_path, profile)
            restored = load_strategy_profile(profile_path)

            self.assertEqual(restored.name, profile.name)
            self.assertEqual(restored.post_macro_wait, 60.0)
            self.assertEqual(restored.key_pulses[0].key, "f")

    def test_duplicate_enabled_keys_are_rejected(self) -> None:
        profile = RecordedStrategyProfile.default_wrecked_battlefield()
        profile.macro_path = "macro.json"
        profile.key_pulses[1].key = "F"

        with self.assertRaisesRegex(ValueError, "unique keys"):
            profile.validate_ready(require_file=False)


if __name__ == "__main__":
    unittest.main()
