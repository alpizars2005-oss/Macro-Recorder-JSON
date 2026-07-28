"""Reusable bounded retry policies for semantic automation actions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterator

from .client_geometry import NormalizedPoint


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """One deterministic retry schedule with optional placement jitter.

    ``attempts`` includes the first attempt. Delays are applied only after a
    failed attempt. Positional jitter follows a deterministic expanding ring so
    two identical strategy runs try the same candidate points.
    """

    attempts: int = 5
    initial_delay: float = 0.20
    backoff_multiplier: float = 1.50
    max_delay: float = 2.0
    timeout_seconds: float = 30.0
    jitter_radius: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= self.attempts <= 100:
            raise ValueError("Retry attempts must be between 1 and 100.")
        if not 0.0 <= self.initial_delay <= 30.0:
            raise ValueError("Retry initial delay must be between 0 and 30 seconds.")
        if not 1.0 <= self.backoff_multiplier <= 10.0:
            raise ValueError("Retry backoff multiplier must be between 1 and 10.")
        if not 0.0 <= self.max_delay <= 60.0:
            raise ValueError("Retry maximum delay must be between 0 and 60 seconds.")
        if self.max_delay < self.initial_delay:
            raise ValueError("Retry maximum delay cannot be lower than the initial delay.")
        if not 0.0 <= self.timeout_seconds <= 24 * 60 * 60:
            raise ValueError("Retry timeout must be between 0 and 24 hours.")
        if not 0.0 <= self.jitter_radius <= 0.10:
            raise ValueError("Retry jitter radius must be between 0.0 and 0.10.")

    @classmethod
    def from_value(
        cls,
        value: Any,
        field_name: str,
        *,
        default_attempts: int,
        default_delay: float,
    ) -> "RetryPolicy":
        if value is None:
            return cls(attempts=default_attempts, initial_delay=default_delay)
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object.")
        return cls(
            attempts=_integer(value.get("attempts", default_attempts), 1, 100, f"{field_name}.attempts"),
            initial_delay=_number(
                value.get("initial_delay", default_delay),
                0.0,
                30.0,
                f"{field_name}.initial_delay",
            ),
            backoff_multiplier=_number(
                value.get("backoff_multiplier", 1.50),
                1.0,
                10.0,
                f"{field_name}.backoff_multiplier",
            ),
            max_delay=_number(
                value.get("max_delay", 2.0),
                0.0,
                60.0,
                f"{field_name}.max_delay",
            ),
            timeout_seconds=_number(
                value.get("timeout_seconds", 30.0),
                0.0,
                24 * 60 * 60,
                f"{field_name}.timeout_seconds",
            ),
            jitter_radius=_number(
                value.get("jitter_radius", 0.0),
                0.0,
                0.10,
                f"{field_name}.jitter_radius",
            ),
        )

    def to_payload(self) -> dict[str, float | int]:
        return {
            "attempts": self.attempts,
            "initial_delay": self.initial_delay,
            "backoff_multiplier": self.backoff_multiplier,
            "max_delay": self.max_delay,
            "timeout_seconds": self.timeout_seconds,
            "jitter_radius": self.jitter_radius,
        }

    def delay_after_failure(self, failed_attempt: int) -> float:
        """Return the delay after one 1-based failed attempt number."""

        if failed_attempt < 1:
            raise ValueError("failed_attempt must be at least 1.")
        return min(
            self.max_delay,
            self.initial_delay * (self.backoff_multiplier ** (failed_attempt - 1)),
        )

    def delays(self) -> Iterator[float]:
        """Yield delays after failures; there is no delay after the last try."""

        for failed_attempt in range(1, self.attempts):
            yield self.delay_after_failure(failed_attempt)

    def candidate_points(self, base: NormalizedPoint) -> Iterator[NormalizedPoint]:
        """Yield deterministic normalized placement candidates.

        The first point is always the requested point. Remaining attempts use
        an expanding eight-direction ring, clamped to the Roblox client area.
        """

        yield base
        if self.attempts == 1:
            return

        directions = (
            (1.0, 0.0),
            (-1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0),
            (math.sqrt(0.5), math.sqrt(0.5)),
            (-math.sqrt(0.5), math.sqrt(0.5)),
            (math.sqrt(0.5), -math.sqrt(0.5)),
            (-math.sqrt(0.5), -math.sqrt(0.5)),
        )
        remaining = self.attempts - 1
        ring_count = max(1, math.ceil(remaining / len(directions)))
        for index in range(remaining):
            ring = index // len(directions) + 1
            direction = directions[index % len(directions)]
            radius = self.jitter_radius * (ring / ring_count)
            yield NormalizedPoint(
                x=min(1.0, max(0.0, base.x + direction[0] * radius)),
                y=min(1.0, max(0.0, base.y + direction[1] * radius)),
            )


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
