"""Tests for Roblox client-relative coordinate conversion."""

from __future__ import annotations

import unittest

from macro_app.client_geometry import ClientRect, NormalizedPoint


class ClientGeometryTests(unittest.TestCase):
    def test_normalized_point_converts_inside_offset_client(self) -> None:
        rect = ClientRect(left=100, top=50, width=1920, height=1080)

        self.assertEqual(NormalizedPoint(0.0, 0.0).to_desktop(rect), (100, 50))
        self.assertEqual(NormalizedPoint(1.0, 1.0).to_desktop(rect), (2019, 1129))
        self.assertEqual(NormalizedPoint(0.5, 0.5).to_desktop(rect), (1060, 590))

    def test_point_can_be_normalized_from_client_pixels(self) -> None:
        point = NormalizedPoint.from_client_pixels(959, 539, width=1920, height=1080)
        restored = point.to_desktop(ClientRect(0, 0, 1920, 1080))

        self.assertEqual(restored, (959, 539))

    def test_invalid_geometry_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ClientRect(0, 0, 0, 1080)
        with self.assertRaises(ValueError):
            NormalizedPoint(1.1, 0.5)


if __name__ == "__main__":
    unittest.main()
