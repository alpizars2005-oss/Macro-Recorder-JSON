"""Priority scheduling for visible screen detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DetectionTask:
    """One periodically checked visual condition."""

    name: str
    priority: int = 0
    poll_interval: float = 0.10

    def __post_init__(self) -> None:
        if not self.name.strip() or len(self.name) > 100:
            raise ValueError("Detection task name must contain 1 to 100 characters.")
        if not -1_000 <= self.priority <= 1_000:
            raise ValueError("Detection task priority must be between -1000 and 1000.")
        if not 0.02 <= self.poll_interval <= 60.0:
            raise ValueError("Detection task poll interval must be between 0.02 and 60 seconds.")


class PriorityDetectionScheduler:
    """Return due detectors in stable priority order.

    Higher-priority tasks run first. Tasks with the same priority are ordered by
    the longest time since their previous check, then by name. This prevents a
    fast high-priority detector from permanently starving lower-priority work.
    """

    def __init__(self, tasks: Iterable[DetectionTask]) -> None:
        self.tasks = tuple(tasks)
        names = [task.name.casefold() for task in self.tasks]
        if len(names) != len(set(names)):
            raise ValueError("Detection task names must be unique.")
        self._last_checked = {task.name: float("-inf") for task in self.tasks}

    def due(self, now: float) -> list[DetectionTask]:
        result = [
            task
            for task in self.tasks
            if now - self._last_checked[task.name] >= task.poll_interval
        ]
        result.sort(
            key=lambda task: (
                -task.priority,
                self._last_checked[task.name],
                task.name.casefold(),
            )
        )
        return result

    def mark_checked(self, task_name: str, now: float) -> None:
        if task_name not in self._last_checked:
            raise KeyError(f"Unknown detection task: {task_name}")
        self._last_checked[task_name] = now

    def next_wait(self, now: float, *, maximum: float = 0.25) -> float:
        """Return how long the worker may sleep before any task becomes due."""

        if not self.tasks:
            return maximum
        remaining = min(
            max(0.0, task.poll_interval - (now - self._last_checked[task.name]))
            for task in self.tasks
        )
        return min(maximum, remaining)
