"""Tests for client-relative multi-point pixel signatures."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macro_app.automation_models import Point, RGBColor
from macro_app.client_geometry import ClientRect, NormalizedPoint
from macro_app.pixel_signatures import (
    PixelSignature,
    PixelSignatureMatcher,
    PixelSignatureSample,
    capture_signature_sample,
    load_pixel_signature,
    save_pixel_signature,
)
from macro_app.screen_capture import SampleResult


class FakeSampler:
    def __init__(self, colors: dict[tuple[int, int], RGBColor]) -> None:
        self.colors = colors
        self.closed = False

    def sample(self, point: Point, radius: int = 1) -> SampleResult:
        return SampleResult(self.colors[(point.x, point.y)], point, radius)

    def close(self) -> None:
        self.closed = True


class PixelSignatureTests(unittest.TestCase):
    def test_signature_matches_multiple_relative_points(self) -> None:
        rect = ClientRect(100, 200, 101, 101)
        sampler = FakeSampler(
            {
                (100, 200): RGBColor(5, 10, 15),
                (150, 250): RGBColor(20, 40, 60),
                (200, 300): RGBColor(200, 10, 10),
            }
        )
        signature = PixelSignature(
            name="ready",
            minimum_ratio=2 / 3,
            samples=(
                PixelSignatureSample(NormalizedPoint(0.0, 0.0), RGBColor(5, 10, 15)),
                PixelSignatureSample(NormalizedPoint(0.5, 0.5), RGBColor(20, 40, 60)),
                PixelSignatureSample(NormalizedPoint(1.0, 1.0), RGBColor(0, 0, 0)),
            ),
        )

        result = PixelSignatureMatcher(sampler).evaluate(signature, rect)

        self.assertEqual(result.matched_samples, 2)
        self.assertEqual(result.total_samples, 3)
        self.assertEqual(result.score, 1.0)

    def test_capture_converts_desktop_point_to_client_relative_point(self) -> None:
        rect = ClientRect(50, 75, 201, 101)
        sampler = FakeSampler({(150, 125): RGBColor(1, 2, 3)})

        sample = capture_signature_sample(
            rect,
            (150, 125),
            sampler,
            tolerance=25,
            radius=2,
        )

        self.assertAlmostEqual(sample.point.x, 0.5)
        self.assertAlmostEqual(sample.point.y, 0.5)
        self.assertEqual(sample.color, RGBColor(1, 2, 3))
        self.assertEqual(sample.tolerance, 25)
        self.assertEqual(sample.radius, 2)

    def test_signature_round_trip_is_atomic_and_validated(self) -> None:
        samples = tuple(
            PixelSignatureSample(
                NormalizedPoint(0.1 * index, 0.2),
                RGBColor(10 + index, 20, 30),
                tolerance=15,
            )
            for index in range(1, 4)
        )
        signature = PixelSignature(
            name="call-to-arms-ready",
            samples=samples,
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cta.pixels.json"
            save_pixel_signature(path, signature)
            restored = load_pixel_signature(path)

        self.assertEqual(restored, signature)

    def test_cursor_outside_client_is_rejected(self) -> None:
        rect = ClientRect(100, 100, 50, 50)
        sampler = FakeSampler({(99, 99): RGBColor(1, 1, 1)})

        with self.assertRaisesRegex(ValueError, "outside"):
            capture_signature_sample(rect, (99, 99), sampler)

    def test_signature_with_too_few_samples_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "3 to"):
            PixelSignature(
                name="unsafe",
                samples=(
                    PixelSignatureSample(NormalizedPoint(0.5, 0.5), RGBColor(1, 2, 3)),
                ),
            )


if __name__ == "__main__":
    unittest.main()
