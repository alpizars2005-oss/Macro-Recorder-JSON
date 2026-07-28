"""Roblox client-area coordinate helpers.

Semantic strategies store points relative to the active client area. The
conversion to desktop coordinates happens only immediately before a visible
mouse action.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClientRect:
    """Desktop-space bounds for one application client area."""

    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Client width and height must be positive.")

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.left + self.width // 2,
            self.top + self.height // 2,
        )


@dataclass(frozen=True, slots=True)
class NormalizedPoint:
    """One point inside a client area using values from 0.0 through 1.0."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.x <= 1.0:
            raise ValueError("Normalized x must be between 0.0 and 1.0.")
        if not 0.0 <= self.y <= 1.0:
            raise ValueError("Normalized y must be between 0.0 and 1.0.")

    def to_desktop(self, rect: ClientRect) -> tuple[int, int]:
        """Convert the normalized point into one desktop-space coordinate."""

        x = rect.left + round(self.x * max(0, rect.width - 1))
        y = rect.top + round(self.y * max(0, rect.height - 1))
        return x, y

    @classmethod
    def from_client_pixels(
        cls,
        x: int,
        y: int,
        *,
        width: int,
        height: int,
    ) -> "NormalizedPoint":
        """Create a normalized point from client-local pixel coordinates."""

        if width <= 0 or height <= 0:
            raise ValueError("Client width and height must be positive.")
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError("Client-local point is outside the client area.")
        return cls(
            x=x / max(1, width - 1),
            y=y / max(1, height - 1),
        )
