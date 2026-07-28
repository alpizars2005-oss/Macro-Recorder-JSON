"""Tests for bounded semantic-action retry policies."""

from __future__ import annotations

import unittest

from macro_app.client_geometry import NormalizedPoint
from macro_app.retry_policy import RetryPolicy


class RetryPolicyTests(unittest.TestCase):
    def test_backoff_is_bounded(self) -> None:
        policy = RetryPolicy(
            attempts=5,
            initial_delay=0.25,
            backoff_multiplier=2.0,
            max_delay=0.75,
        )

        self.assertEqual(list(policy.delays()), [0.25, 0.5, 0.75, 0.75])

    def test_first_candidate_is_requested_point(self) -> None:
        policy = RetryPolicy(attempts=4, jitter_radius=0.02)
        base = NormalizedPoint(0.5, 0.5)

        points = list(policy.candidate_points(base))

        self.assertEqual(points[0], base)
        self.assertEqual(len(points), 4)
        self.assertNotEqual(points[1], base)

    def test_candidate_points_are_clamped_to_client(self) -> None:
        policy = RetryPolicy(attempts=10, jitter_radius=0.10)

        points = list(policy.candidate_points(NormalizedPoint(0.0, 1.0)))

        self.assertTrue(all(0.0 <= point.x <= 1.0 for point in points))
        self.assertTrue(all(0.0 <= point.y <= 1.0 for point in points))

    def test_payload_round_trip(self) -> None:
        original = RetryPolicy(
            attempts=9,
            initial_delay=0.3,
            backoff_multiplier=1.25,
            max_delay=1.5,
            timeout_seconds=45.0,
            jitter_radius=0.015,
        )

        restored = RetryPolicy.from_value(
            original.to_payload(),
            "retry",
            default_attempts=5,
            default_delay=0.2,
        )

        self.assertEqual(restored, original)


if __name__ == "__main__":
    unittest.main()
