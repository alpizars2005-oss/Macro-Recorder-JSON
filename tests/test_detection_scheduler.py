"""Tests for priority-based visual detector scheduling."""

from __future__ import annotations

import unittest

from macro_app.detection_scheduler import DetectionTask, PriorityDetectionScheduler


class DetectionSchedulerTests(unittest.TestCase):
    def test_higher_priority_due_task_runs_first(self) -> None:
        scheduler = PriorityDetectionScheduler(
            [
                DetectionTask("wave", priority=10, poll_interval=0.1),
                DetectionTask("disconnect", priority=100, poll_interval=0.1),
            ]
        )

        self.assertEqual(
            [task.name for task in scheduler.due(1.0)],
            ["disconnect", "wave"],
        )

    def test_mark_checked_hides_task_until_interval_passes(self) -> None:
        scheduler = PriorityDetectionScheduler(
            [DetectionTask("ready", priority=1, poll_interval=0.5)]
        )
        scheduler.mark_checked("ready", 10.0)

        self.assertEqual(scheduler.due(10.2), [])
        self.assertEqual([task.name for task in scheduler.due(10.5)], ["ready"])

    def test_same_priority_uses_oldest_check_first(self) -> None:
        scheduler = PriorityDetectionScheduler(
            [
                DetectionTask("a", priority=5, poll_interval=0.1),
                DetectionTask("b", priority=5, poll_interval=0.1),
            ]
        )
        scheduler.mark_checked("a", 2.0)
        scheduler.mark_checked("b", 1.0)

        self.assertEqual([task.name for task in scheduler.due(3.0)], ["b", "a"])

    def test_duplicate_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            PriorityDetectionScheduler(
                [
                    DetectionTask("Restart"),
                    DetectionTask("restart"),
                ]
            )


if __name__ == "__main__":
    unittest.main()
