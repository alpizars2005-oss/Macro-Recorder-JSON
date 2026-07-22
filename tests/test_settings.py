"""Tests for safe settings normalization."""

from __future__ import annotations

import unittest

from macro_app.settings import AppSettings


class SettingsTests(unittest.TestCase):
    def test_invalid_values_fall_back_to_defaults(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "language": "fr",
                "mouse_sample_mode": "invalid",
                "playback_speed": -5,
                "playback_delay": 1000,
            }
        )
        self.assertEqual(settings.language, "en")
        self.assertEqual(settings.mouse_sample_mode, "balanced")
        self.assertEqual(settings.playback_speed, 1.0)
        self.assertEqual(settings.playback_delay, 3.0)

    def test_valid_values_are_preserved(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "language": "es-MX",
                "record_mouse_move": False,
                "keep_on_top": False,
                "mouse_sample_mode": "compact",
                "playback_speed": 2,
                "playback_delay": 5,
            }
        )
        self.assertEqual(settings.language, "es")
        self.assertFalse(settings.record_mouse_move)
        self.assertFalse(settings.keep_on_top)
        self.assertEqual(settings.mouse_sample_mode, "compact")
        self.assertEqual(settings.playback_speed, 2.0)
        self.assertEqual(settings.playback_delay, 5.0)


if __name__ == "__main__":
    unittest.main()
