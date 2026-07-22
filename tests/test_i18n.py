"""Tests for English and Spanish translations."""

from __future__ import annotations

import unittest

from macro_app.i18n import TRANSLATIONS, Translator, normalize_language


class TranslationTests(unittest.TestCase):
    def test_supported_languages_have_the_same_keys(self) -> None:
        self.assertEqual(set(TRANSLATIONS["en"]), set(TRANSLATIONS["es"]))

    def test_formatting_works_in_both_languages(self) -> None:
        for language in ("en", "es"):
            text = Translator(language).text("events", count=12)
            self.assertIn("12", text)

    def test_language_normalization(self) -> None:
        self.assertEqual(normalize_language("es_MX"), "es")
        self.assertEqual(normalize_language("en-US"), "en")
        self.assertEqual(normalize_language("fr"), "en")


if __name__ == "__main__":
    unittest.main()
