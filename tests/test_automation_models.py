"""Tests for Automation Studio profile validation and persistence."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macro_app.automation_models import (
    AutomationProfile,
    PixelTrigger,
    Point,
    RGBColor,
    load_profile,
    save_profile,
)


class AutomationModelTests(unittest.TestCase):
    def test_round_trip_profile(self) -> None:
        profile = AutomationProfile.default_tds()
        profile.triggers[0] = PixelTrigger(
            name="Restart",
            enabled=True,
            sample_point=Point(10, 20),
            click_point=Point(11, 21),
            target_color=RGBColor(10, 240, 20),
        )
        profile.commander.enabled = True
        profile.commander.commander_points = [Point(1, 2), Point(3, 4), Point(5, 6)]
        profile.commander.ability_point = Point(7, 8)

        restored = AutomationProfile.from_payload(profile.to_payload())

        self.assertEqual(restored.name, profile.name)
        self.assertEqual(restored.triggers[0].target_color, RGBColor(10, 240, 20))
        self.assertEqual(restored.commander.commander_points[2], Point(5, 6))

    def test_enabled_trigger_requires_capture(self) -> None:
        profile = AutomationProfile.default_tds()
        profile.triggers[0].enabled = True

        with self.assertRaisesRegex(ValueError, "sample point"):
            profile.validate_ready()

    def test_save_and_load_profile(self) -> None:
        profile = AutomationProfile.default_tds()
        profile.commander.enabled = True
        profile.commander.commander_points = [Point(1, 2)]
        profile.commander.ability_point = Point(3, 4)

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            save_profile(path, profile)
            loaded = load_profile(path)

            self.assertEqual(loaded.commander.ability_point, Point(3, 4))
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_rejects_invalid_color(self) -> None:
        payload = AutomationProfile.default_tds().to_payload()
        payload["triggers"][0]["enabled"] = True
        payload["triggers"][0]["sample_point"] = {"x": 1, "y": 2}
        payload["triggers"][0]["click_point"] = {"x": 1, "y": 2}
        payload["triggers"][0]["target_color"] = {"r": 256, "g": 1, "b": 2}

        with self.assertRaises(ValueError):
            AutomationProfile.from_payload(payload)


if __name__ == "__main__":
    unittest.main()
