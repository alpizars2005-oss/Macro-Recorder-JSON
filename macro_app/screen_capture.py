"""Small, dependency-light screen sampling helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .automation_models import Point, RGBColor


class GrabResult(Protocol):
    bgra: bytes


class Grabber(Protocol):
    def grab(self, monitor: dict[str, int]) -> GrabResult: ...
    def close(self) -> None: ...


@dataclass(slots=True, frozen=True)
class SampleResult:
    color: RGBColor
    point: Point
    radius: int


class ScreenSampler:
    """Samples a tiny screen region and returns its average RGB color."""

    def __init__(self, grabber_factory: Callable[[], Grabber] | None = None) -> None:
        self._factory = grabber_factory or self._default_factory
        self._grabber: Grabber | None = None

    @staticmethod
    def _default_factory() -> Grabber:
        try:
            import mss  # type: ignore
        except ImportError as exc:  # pragma: no cover - launcher installs it
            raise RuntimeError("Screen capture support is not installed. Run the launcher with --repair.") from exc
        return mss.mss()

    def _get_grabber(self) -> Grabber:
        if self._grabber is None:
            self._grabber = self._factory()
        return self._grabber

    def sample(self, point: Point, radius: int = 1) -> SampleResult:
        if not 0 <= radius <= 5:
            raise ValueError("Sample radius must be between 0 and 5.")
        size = radius * 2 + 1
        monitor = {
            "left": point.x - radius,
            "top": point.y - radius,
            "width": size,
            "height": size,
        }
        shot = self._get_grabber().grab(monitor)
        expected_bytes = size * size * 4
        if len(shot.bgra) != expected_bytes:
            raise RuntimeError("The screen capture returned an unexpected pixel buffer size.")

        red = green = blue = 0
        pixels = size * size
        raw = shot.bgra
        for offset in range(0, len(raw), 4):
            blue += raw[offset]
            green += raw[offset + 1]
            red += raw[offset + 2]
        return SampleResult(
            color=RGBColor(
                r=round(red / pixels),
                g=round(green / pixels),
                b=round(blue / pixels),
            ),
            point=point,
            radius=radius,
        )

    def close(self) -> None:
        if self._grabber is not None:
            try:
                self._grabber.close()
            finally:
                self._grabber = None

    def __enter__(self) -> "ScreenSampler":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()


def color_distance(left: RGBColor, right: RGBColor) -> int:
    """Return the largest per-channel RGB difference."""

    return max(abs(left.r - right.r), abs(left.g - right.g), abs(left.b - right.b))


def color_matches(actual: RGBColor, target: RGBColor, tolerance: int) -> bool:
    if not 0 <= tolerance <= 255:
        raise ValueError("Color tolerance must be between 0 and 255.")
    return color_distance(actual, target) <= tolerance
