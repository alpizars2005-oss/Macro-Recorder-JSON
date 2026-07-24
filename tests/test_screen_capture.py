"""Tests for small-region screen color sampling."""

from __future__ import annotations

import unittest

from macro_app.automation_models import Point, RGBColor
from macro_app.screen_capture import ScreenSampler, color_distance, color_matches


class Shot:
    def __init__(self, bgra: bytes) -> None:
        self.bgra = bgra


class FakeGrabber:
    def __init__(self, pixels: bytes) -> None:
        self.pixels = pixels
        self.monitors: list[dict[str, int]] = []
        self.closed = False

    def grab(self, monitor: dict[str, int]) -> Shot:
        self.monitors.append(monitor)
        return Shot(self.pixels)

    def close(self) -> None:
        self.closed = True


class ScreenCaptureTests(unittest.TestCase):
    def test_average_bgra_to_rgb(self) -> None:
        pixels = bytes([0, 0, 255, 255])
        grabber = FakeGrabber(pixels)
        sampler = ScreenSampler(lambda: grabber)

        result = sampler.sample(Point(10, 20), radius=0)

        self.assertEqual(result.color, RGBColor(255, 0, 0))

    def test_three_by_three_average(self) -> None:
        pixel = bytes([30, 20, 10, 255])
        grabber = FakeGrabber(pixel * 9)
        sampler = ScreenSampler(lambda: grabber)

        result = sampler.sample(Point(-5, 7), radius=1)

        self.assertEqual(result.color, RGBColor(10, 20, 30))
        self.assertEqual(
            grabber.monitors[0],
            {"left": -6, "top": 6, "width": 3, "height": 3},
        )

    def test_color_tolerance(self) -> None:
        left = RGBColor(10, 20, 30)
        right = RGBColor(15, 18, 40)

        self.assertEqual(color_distance(left, right), 10)
        self.assertTrue(color_matches(left, right, 10))
        self.assertFalse(color_matches(left, right, 9))


if __name__ == "__main__":
    unittest.main()
