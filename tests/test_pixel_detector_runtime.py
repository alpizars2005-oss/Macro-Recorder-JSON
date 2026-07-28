"""Tests for semantic detector runtime backed by pixel signatures."""

from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import unittest

from macro_app.automation_models import Point, RGBColor
from macro_app.client_geometry import ClientRect, NormalizedPoint
from macro_app.pixel_detector_runtime import PixelDetectorRuntime
from macro_app.pixel_signatures import (
    PixelSignature,
    PixelSignatureMatcher,
    PixelSignatureSample,
    save_pixel_signature,
)
from macro_app.screen_capture import SampleResult
from macro_app.semantic_strategy import NormalizedRegion, VisualDetector


class FakeSampler:
    def __init__(self, color: RGBColor) -> None:
        self.color = color
        self.closed = False

    def sample(self, point: Point, radius: int = 1) -> SampleResult:
        return SampleResult(self.color, point, radius)

    def close(self) -> None:
        self.closed = True


class PixelDetectorRuntimeTests(unittest.TestCase):
    def _runtime(self, folder: str, *, required_matches: int = 1) -> PixelDetectorRuntime:
        path = Path(folder) / "ready.pixels.json"
        save_pixel_signature(
            path,
            PixelSignature(
                name="ready",
                samples=(
                    PixelSignatureSample(
                        NormalizedPoint(0.5, 0.5),
                        RGBColor(10, 20, 30),
                    ),
                ),
            ),
        )
        detector = VisualDetector(
            name="ready",
            template_path=path.name,
            threshold=1.0,
            required_matches=required_matches,
            poll_interval=0.02,
            region=NormalizedRegion(0.4, 0.4, 0.6, 0.6),
        )
        return PixelDetectorRuntime(
            [detector],
            base_directory=Path(folder),
            matcher=PixelSignatureMatcher(FakeSampler(RGBColor(10, 20, 30))),
        )

    def test_observation_matches_signature(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            runtime = self._runtime(folder)
            observation = runtime.observe("READY", ClientRect(0, 0, 101, 101))

        self.assertTrue(observation.matched)
        self.assertEqual(observation.matched_samples, 1)

    def test_wait_for_requires_consecutive_matches(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            runtime = self._runtime(folder, required_matches=2)
            rect = ClientRect(0, 0, 101, 101)
            result = runtime.wait_for(
                "ready",
                rect_provider=lambda: rect,
                stop_event=threading.Event(),
                timeout_seconds=0.20,
                window_allowed=lambda: True,
            )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.matched)

    def test_click_point_uses_detector_region_center(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            runtime = self._runtime(folder)
            point = runtime.click_point("ready", ClientRect(100, 200, 101, 101))

        self.assertEqual(point, (150, 250))

    def test_non_signature_assets_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ready.png"
            path.write_bytes(b"not-an-image")
            detector = VisualDetector(name="ready", template_path=path.name)

            with self.assertRaisesRegex(ValueError, "pixels.json"):
                PixelDetectorRuntime([detector], base_directory=Path(folder))


if __name__ == "__main__":
    unittest.main()
