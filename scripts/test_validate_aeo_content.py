"""Regression checks for optional hreflang on genuinely single-language routes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_aeo_content as validator


class StaticRouteHreflangTest(unittest.TestCase):
    def check_route(self, alternates="", *, require_hreflang=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "it" / "example" / "index.html"
            page.parent.mkdir(parents=True)
            canonical = f"{validator.SITE}/it/example/"
            page.write_text(
                f'<html lang="it"><head><link rel="canonical" href="{canonical}">'
                f'{alternates}</head><body><h1>Esempio</h1><p>'
                + "Contenuto leggibile. " * 100 + "</p></body></html>",
                encoding="utf-8",
            )
            report = validator.Report()
            with patch.object(validator, "ROOT", root):
                validator.check_static_page(
                    "it/example/index.html", report, "it",
                    require_hreflang=require_hreflang,
                )
            return report.errors

    def test_solo_route_can_omit_language_alternates(self):
        self.assertEqual(self.check_route(require_hreflang=False), [])

    def test_bilingual_route_still_requires_self_alternate(self):
        self.assertTrue(any("hreflang 'it'" in e for e in self.check_route()))

    def test_declared_alternates_require_correct_self_even_on_solo_route(self):
        alternate = '<link rel="alternate" hreflang="it" href="https://example.com/wrong/">'
        errors = self.check_route(alternate, require_hreflang=False)
        self.assertTrue(any("hreflang 'it'" in e for e in errors))

    def test_optional_valid_self_alternate_is_allowed(self):
        alternate = f'<link rel="alternate" hreflang="it" href="{validator.SITE}/it/example/">'
        self.assertEqual(self.check_route(alternate, require_hreflang=False), [])


if __name__ == "__main__":
    unittest.main()
