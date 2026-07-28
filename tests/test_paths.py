"""Tests for project and packaged-application path helpers."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from macro_app.paths import (
    DATA_DIRECTORY_OVERRIDE,
    APP_DATA_DIRECTORY_NAME,
    default_data_root,
    ensure_automation_directory,
    ensure_macro_directory,
    ensure_strategy_directory,
    ensure_visual_directory,
)


class PathTests(unittest.TestCase):
    def test_macro_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "macros"
            result = ensure_macro_directory(target)

            self.assertTrue(result.is_dir())
            self.assertEqual(result, target.resolve())

    def test_existing_macro_directory_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "macros"
            target.mkdir()

            first = ensure_macro_directory(target)
            second = ensure_macro_directory(target)

            self.assertEqual(first, second)

    def test_automation_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "automations"
            result = ensure_automation_directory(target)

            self.assertTrue(result.is_dir())
            self.assertEqual(result, target.resolve())

    def test_strategy_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "strategies"
            result = ensure_strategy_directory(target)

            self.assertTrue(result.is_dir())
            self.assertEqual(result, target.resolve())

    def test_visual_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "strategies" / "visuals"
            result = ensure_visual_directory(target)

            self.assertTrue(result.is_dir())
            self.assertEqual(result, target.resolve())

    def test_data_directory_override_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "portable-data"
            with mock.patch.dict(os.environ, {DATA_DIRECTORY_OVERRIDE: str(target)}):
                self.assertEqual(default_data_root(), target)

    def test_frozen_windows_build_uses_local_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment = {
                "LOCALAPPDATA": temporary_directory,
                DATA_DIRECTORY_OVERRIDE: "",
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                with mock.patch.object(sys, "frozen", True, create=True):
                    self.assertEqual(
                        default_data_root(),
                        Path(temporary_directory) / APP_DATA_DIRECTORY_NAME,
                    )


if __name__ == "__main__":
    unittest.main()
