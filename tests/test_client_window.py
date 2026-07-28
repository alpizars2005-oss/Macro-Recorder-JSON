"""Tests for foreground client-area parsing."""

from __future__ import annotations

import unittest

from macro_app.client_window import parse_xdotool_geometry


class ClientWindowTests(unittest.TestCase):
    def test_xdotool_geometry_is_parsed(self) -> None:
        rect = parse_xdotool_geometry("X=10\nY=20\nWIDTH=1280\nHEIGHT=720\n")

        self.assertIsNotNone(rect)
        assert rect is not None
        self.assertEqual((rect.left, rect.top, rect.width, rect.height), (10, 20, 1280, 720))

    def test_incomplete_xdotool_geometry_is_rejected(self) -> None:
        self.assertIsNone(parse_xdotool_geometry("X=10\nY=20\nWIDTH=1280\n"))


if __name__ == "__main__":
    unittest.main()
