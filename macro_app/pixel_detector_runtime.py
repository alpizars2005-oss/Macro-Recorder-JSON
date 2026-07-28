"""Runtime support for semantic visual detectors backed by pixel signatures."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .client_geometry import ClientRect, NormalizedPoint
from .pixel_signatures import PixelSignature, PixelSignatureMatcher, load_pixel_signature
from .semantic_strategy import VisualDetector


@dataclass(frozen=True, slots=True)
class DetectorObservation:
    name: str
    matched: bool
    score: float
    matched_samples: int
    total_samples: int


@dataclass(frozen=True, slots=True)
class LoadedPixelDetector:
    definition: VisualDetector
    signature: PixelSignature


class PixelDetectorRuntime:
    """Load and evaluate named semantic detectors from local signature files."""

    def __init__(
        self,
        detectors: list[VisualDetector],
        *,
        base_directory: Path,
        matcher: PixelSignatureMatcher | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_directory = base_directory.expanduser().resolve()
        self.matcher = matcher or PixelSignatureMatcher()
        self.clock = clock
        self.detectors: dict[str, LoadedPixelDetector] = {}

        for detector in detectors:
            path = (self.base_directory / detector.template_path).resolve()
            try:
                path.relative_to(self.base_directory)
            except ValueError as exc:
                raise ValueError(
                    f"Detector '{detector.name}' points outside the strategy folder."
                ) from exc
            if path.suffix.casefold() != ".json" or not path.name.casefold().endswith(
                ".pixels.json"
            ):
                raise ValueError(
                    f"Detector '{detector.name}' must use a .pixels.json signature in this release."
                )
            signature = load_pixel_signature(path)
            self.detectors[detector.name.casefold()] = LoadedPixelDetector(detector, signature)

    def observe(self, name: str, rect: ClientRect) -> DetectorObservation:
        loaded = self._get(name)
        result = self.matcher.evaluate(
            loaded.signature,
            rect,
            threshold=loaded.definition.threshold,
        )
        return DetectorObservation(
            name=loaded.definition.name,
            matched=result.score >= 1.0,
            score=result.score,
            matched_samples=result.matched_samples,
            total_samples=result.total_samples,
        )

    def matches(self, name: str, rect: ClientRect) -> bool:
        return self.observe(name, rect).matched

    def wait_for(
        self,
        name: str,
        *,
        rect_provider: Callable[[], ClientRect],
        stop_event: threading.Event,
        timeout_seconds: float,
        window_allowed: Callable[[], bool],
    ) -> DetectorObservation | None:
        loaded = self._get(name)
        deadline = self.clock() + max(0.0, timeout_seconds)
        consecutive = 0
        last: DetectorObservation | None = None

        while not stop_event.is_set() and self.clock() <= deadline:
            if not window_allowed():
                return None
            last = self.observe(name, rect_provider())
            if last.matched:
                consecutive += 1
                if consecutive >= loaded.definition.required_matches:
                    return last
            else:
                consecutive = 0
            stop_event.wait(loaded.definition.poll_interval)
        return None

    def click_point(self, name: str, rect: ClientRect) -> tuple[int, int]:
        detector = self._get(name).definition
        return NormalizedPoint(
            (detector.region.left + detector.region.right) / 2,
            (detector.region.top + detector.region.bottom) / 2,
        ).to_desktop(rect)

    def detector_names(self) -> tuple[str, ...]:
        return tuple(loaded.definition.name for loaded in self.detectors.values())

    def close(self) -> None:
        self.matcher.close()

    def _get(self, name: str) -> LoadedPixelDetector:
        key = name.strip().casefold()
        if not key or key not in self.detectors:
            raise KeyError(f"Unknown visual detector: {name!r}.")
        return self.detectors[key]
