"""Verify deterministic generation and fail-closed drift detection on copies."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from generate_product_locales import LOCALE_ROUTES, ROOT, ROUTES, english_body, german_body


class ProductLocaleGenerationTests(unittest.TestCase):
    def test_extraction_preserves_authored_english_markup_and_entities(self):
        source = '<p><span class="t-it">Italiano <b>originale</b></span><span class="t-en">Exact <b>English</b> &amp; 1%.</span> Shared.</p>'
        self.assertEqual(english_body(source), '<p>Exact <b>English</b> &amp; 1%. Shared.</p>')

    def test_shared_numbers_use_english_separators_without_changing_authored_spans_or_code(self):
        source = '<table><tr><td>USD 275.000 - 366.000</td><td>USD 100.000</td><td>USD 1.000</td><td>USD 1.000.000</td><td>2,89</td><td>-10,7%</td><td>1,3×</td><td><span class="t-en">USD 1,000 and <b>2,89</b> verbatim</span></td><td><span class="t-it">USD 1.000</span></td></tr></table><script>var number="1.000";</script><b>CH1554882477</b><b>2026-09-24</b>'
        expected = '<table><tr><td>USD 275,000 - 366,000</td><td>USD 100,000</td><td>USD 1,000</td><td>USD 1,000,000</td><td>2.89</td><td>-10.7%</td><td>1.3×</td><td>USD 1,000 and <b>2,89</b> verbatim</td><td></td></tr></table><script>var number="1.000";</script><b>CH1554882477</b><b>2026-09-24</b>'
        self.assertEqual(english_body(source), expected)

    def test_shared_signed_percentages_accept_the_typographic_minus(self):
        source = '<table><tr><td>−36,20%</td><td>+79,19%</td></tr></table><b>−63,28%</b>'
        self.assertEqual(english_body(source), '<table><tr><td>−36.20%</td><td>+79.19%</td></tr></table><b>−63.28%</b>')

    def test_shared_language_labels_keep_values(self):
        source = '<small class="pre">fino a</small>50<b>24 set 2026</b><b>24 mar 2027</b><b>24 set 2029</b>'
        self.assertEqual(english_body(source), '<small class="pre">up to</small>50<b>24 Sep 2026</b><b>24 Mar 2027</b><b>24 Sep 2029</b>')

    def test_german_body_uses_reviewed_text_keeps_markup_and_reports_missing_spans(self):
        source = ('<p><span class="t-it">Ciao <b>mondo</b></span><span class="t-en">Hello <b>world</b> &amp; 1%.</span> <small class="pre">fino a</small>100</p>'
                  '<p><span class="t-it">Altro</span><span class="t-en">Untranslated</span></p>')
        missing = []
        output = german_body(source, {'Hello <b>world</b> &amp; 1%.': 'Hallo <b>Welt</b> &amp; 1%.'}, missing)
        self.assertTrue(output.startswith('<p>Hallo <b>Welt</b> &amp; 1%. <small class="pre">bis zu</small>100</p>'))
        self.assertEqual(missing, ['Untranslated'])

    def test_check_rejects_missing_or_edited_output_and_generation_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / 'scripts' / 'generate_product_locales.py'
            script.parent.mkdir()
            shutil.copyfile(ROOT / 'scripts' / script.name, script)
            for route in ROUTES:
                destination = root / 'it' / route / 'index.html'
                destination.parent.mkdir(parents=True)
                shutil.copyfile(ROOT / 'it' / route / 'index.html', destination)
            shutil.copytree(ROOT / 'i18n', root / 'i18n')
            localized = [locale + '/' + route for locale, routes in LOCALE_ROUTES.items() for route in routes]

            def run(*args):
                return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)

            self.assertEqual(run('--check').returncode, 1, 'missing pages must fail')
            first = run()
            self.assertEqual(first.returncode, 0, first.stderr)
            outputs = {route: (root / route / 'index.html').read_bytes() for route in [*ROUTES, *localized]}
            self.assertEqual(run('--check').returncode, 0)
            self.assertEqual(run().returncode, 0)
            self.assertEqual(outputs, {route: (root / route / 'index.html').read_bytes() for route in [*ROUTES, *localized]})
            target = root / ROUTES[0] / 'index.html'
            target.write_bytes(target.read_bytes() + b'<!-- accidental direct edit -->')
            stale = run('--check')
            self.assertEqual(stale.returncode, 1)
            self.assertIn(ROUTES[0] + '/index.html', stale.stderr)
            self.assertEqual(run().returncode, 0)
            self.assertEqual(run('--check').returncode, 0)

            for locale, routes in LOCALE_ROUTES.items():
                for route in routes:
                    dictionary = root / 'i18n' / locale / (route + '.json')
                    original = dictionary.read_text(encoding='utf-8')
                    data = json.loads(original)
                    removed_key = next(iter(data['segments']))
                    del data['segments'][removed_key]
                    dictionary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                    untranslated = run('--check')
                    self.assertEqual(untranslated.returncode, 1, 'a missing translation must fail')
                    self.assertIn('no ' + locale + ' translation', untranslated.stderr)
                    data = json.loads(original)
                    data['segments']['A sentence the page no longer has'] = 'Ein Satz, den die Seite nicht mehr hat'
                    dictionary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                    unused = run('--check')
                    self.assertEqual(unused.returncode, 1, 'a stale translation must fail')
                    self.assertIn('no longer used', unused.stderr)
                    dictionary.write_text(original, encoding='utf-8')
                    self.assertEqual(run('--check').returncode, 0)


if __name__ == '__main__':
    unittest.main()
