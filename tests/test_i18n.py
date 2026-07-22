"""Tests for natural English and Spanish interface text."""

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

    def test_spanish_uses_simple_natural_wording(self) -> None:
        spanish = TRANSLATIONS["es"]
        self.assertEqual(spanish["windows_ready"], "Windows detectado.")
        self.assertEqual(spanish["record_text"], "Grabar lo que escribo")
        self.assertEqual(spanish["play_macro"], "Ejecutar macro")

        combined = " ".join(spanish.values()).lower()
        for awkward_term in ("teclas imprimibles", "listener", "estado de la plataforma"):
            self.assertNotIn(awkward_term, combined)

    def test_english_uses_short_clear_labels(self) -> None:
        english = TRANSLATIONS["en"]
        self.assertEqual(english["windows_ready"], "Windows detected.")
        self.assertEqual(english["record_text"], "Record what I type")
        self.assertEqual(english["play_macro"], "Run macro")

    def test_every_translation_has_visible_text(self) -> None:
        for language, messages in TRANSLATIONS.items():
            for key, value in messages.items():
                with self.subTest(language=language, key=key):
                    self.assertTrue(value.strip())
                    self.assertNotIn("  ", value)


if __name__ == "__main__":
    unittest.main()
