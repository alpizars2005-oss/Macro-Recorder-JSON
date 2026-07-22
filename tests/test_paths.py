"""Tests for project path helpers."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macro_app.paths import ensure_macro_directory


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


if __name__ == "__main__":
    unittest.main()
