"""Client-relative multi-point visual signatures for TDS automation.

Pixel signatures are intentionally simple, local data. They avoid bundling
third-party screenshots or OCR models while still allowing important UI states
to be confirmed with several independent color samples.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .automation_models import Point, RGBColor
from .client_geometry import ClientRect, NormalizedPoint
from .screen_capture import ScreenSampler, color_matches

PIXEL_SIGNATURE_SCHEMA_VERSION = 1
MAX_SIGNATURE_BYTES = 256 * 1024
MAX_SIGNATURE_SAMPLES = 64


@dataclass(frozen=True, slots=True)
class PixelSignatureSample:
    point: NormalizedPoint
    color: RGBColor
    tolerance: int = 30
    radius: int = 1

    def __post_init__(self) -> None:
        if not 0 <= self.tolerance <= 255:
            raise ValueError("Pixel-signature tolerance must be between 0 and 255.")
        if not 0 <= self.radius <= 5:
            raise ValueError("Pixel-signature sample radius must be between 0 and 5.")

    @classmethod
    def from_value(cls, value: Any, index: int) -> "PixelSignatureSample":
        label = f"samples[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object.")
        return cls(
            point=NormalizedPoint(
                _number(value.get("x"), 0.0, 1.0, f"{label}.x"),
                _number(value.get("y"), 0.0, 1.0, f"{label}.y"),
            ),
            color=RGBColor.from_value(value.get("color"), f"{label}.color"),
            tolerance=_integer(value.get("tolerance", 30), 0, 255, f"{label}.tolerance"),
            radius=_integer(value.get("radius", 1), 0, 5, f"{label}.radius"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "x": self.point.x,
            "y": self.point.y,
            "color": {"r": self.color.r, "g": self.color.g, "b": self.color.b},
            "tolerance": self.tolerance,
            "radius": self.radius,
        }


@dataclass(frozen=True, slots=True)
class PixelSignature:
    name: str
    samples: tuple[PixelSignatureSample, ...]
    minimum_ratio: float = 0.80

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name or len(name) > 100:
            raise ValueError("Pixel-signature name must contain 1 to 100 characters.")
        if not 1 <= len(self.samples) <= MAX_SIGNATURE_SAMPLES:
            raise ValueError(
                f"Pixel signatures must contain 1 to {MAX_SIGNATURE_SAMPLES} samples."
            )
        if not 0.0 <= self.minimum_ratio <= 1.0:
            raise ValueError("Pixel-signature minimum ratio must be between 0 and 1.")

    @classmethod
    def from_payload(cls, payload: Any) -> "PixelSignature":
        if not isinstance(payload, dict):
            raise ValueError("Pixel signature must be a JSON object.")
        if payload.get("schema_version") != PIXEL_SIGNATURE_SCHEMA_VERSION:
            raise ValueError("Unsupported pixel-signature schema.")
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise ValueError("samples must be a list.")
        if len(samples) > MAX_SIGNATURE_SAMPLES:
            raise ValueError(
                f"samples must contain at most {MAX_SIGNATURE_SAMPLES} items."
            )
        return cls(
            name=_text(payload.get("name"), "name", maximum=100),
            samples=tuple(
                PixelSignatureSample.from_value(value, index)
                for index, value in enumerate(samples)
            ),
            minimum_ratio=_number(
                payload.get("minimum_ratio", 0.80),
                0.0,
                1.0,
                "minimum_ratio",
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": PIXEL_SIGNATURE_SCHEMA_VERSION,
            "name": self.name,
            "minimum_ratio": self.minimum_ratio,
            "samples": [sample.to_payload() for sample in self.samples],
        }


@dataclass(frozen=True, slots=True)
class PixelSignatureMatch:
    score: float
    matched_samples: int
    total_samples: int

    @property
    def matched(self) -> bool:
        return self.total_samples > 0 and self.score >= 1.0


class PixelSignatureMatcher:
    """Evaluate signatures against the current Roblox client area."""

    def __init__(self, sampler: ScreenSampler | None = None) -> None:
        self.sampler = sampler or ScreenSampler()

    def evaluate(
        self,
        signature: PixelSignature,
        rect: ClientRect,
        *,
        threshold: float | None = None,
    ) -> PixelSignatureMatch:
        required = signature.minimum_ratio if threshold is None else threshold
        if not 0.0 <= required <= 1.0:
            raise ValueError("Signature threshold must be between 0 and 1.")

        matched = 0
        for sample in signature.samples:
            x, y = sample.point.to_desktop(rect)
            actual = self.sampler.sample(Point(x, y), sample.radius).color
            if color_matches(actual, sample.color, sample.tolerance):
                matched += 1

        total = len(signature.samples)
        raw_ratio = matched / total
        normalized_score = 1.0 if raw_ratio >= required else raw_ratio / max(required, 1e-9)
        return PixelSignatureMatch(
            score=min(1.0, normalized_score),
            matched_samples=matched,
            total_samples=total,
        )

    def close(self) -> None:
        self.sampler.close()


def capture_signature_sample(
    rect: ClientRect,
    desktop_point: tuple[int, int],
    sampler: ScreenSampler,
    *,
    tolerance: int = 30,
    radius: int = 1,
) -> PixelSignatureSample:
    x, y = desktop_point
    client_x = x - rect.left
    client_y = y - rect.top
    point = NormalizedPoint.from_client_pixels(
        client_x,
        client_y,
        width=rect.width,
        height=rect.height,
    )
    color = sampler.sample(Point(x, y), radius).color
    return PixelSignatureSample(point=point, color=color, tolerance=tolerance, radius=radius)


def load_pixel_signature(path: Path) -> PixelSignature:
    if path.stat().st_size > MAX_SIGNATURE_BYTES:
        raise ValueError("Pixel-signature file is larger than the 256 KB limit.")
    return PixelSignature.from_payload(json.loads(path.read_text(encoding="utf-8")))


def save_pixel_signature(path: Path, signature: PixelSignature) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(signature.to_payload(), ensure_ascii=False, indent=2) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(serialized)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink(missing_ok=True)


def _text(value: Any, field_name: str, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")
    result = value.strip()
    if not result:
        raise ValueError(f"{field_name} cannot be empty.")
    if len(result) > maximum:
        raise ValueError(f"{field_name} must be at most {maximum} characters.")
    return result


def _integer(value: Any, minimum: int, maximum: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


def _number(value: Any, minimum: float, maximum: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number.")
    result = float(value)
    if not minimum <= result <= maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}.")
    return result
