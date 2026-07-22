"""Tests for the bilingual smart launcher."""

from __future__ import annotations

import unittest

import bootstrap


class BootstrapLanguageTests(unittest.TestCase):
    def test_explicit_language_option_is_detected(self) -> None:
        self.assertEqual(bootstrap.requested_language(["--language", "es"]), "es")
        self.assertEqual(bootstrap.requested_language(["--language=en"]), "en")
        self.assertEqual(bootstrap.requested_language(["-l", "es"]), "es")

    def test_launcher_messages_are_natural(self) -> None:
        previous = bootstrap.LANGUAGE
        try:
            bootstrap.LANGUAGE = "es"
            self.assertEqual(
                bootstrap.tr("deps_ready"),
                "Todo está listo. No es necesario descargar nada.",
            )
            bootstrap.LANGUAGE = "en"
            self.assertEqual(
                bootstrap.tr("deps_ready"),
                "Everything is ready. No download needed.",
            )
        finally:
            bootstrap.LANGUAGE = previous


if __name__ == "__main__":
    unittest.main()
