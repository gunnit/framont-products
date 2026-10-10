#!/usr/bin/env python3
"""Category routes stay useful without JavaScript and preserve their evidence.

Run with: python3 -m unittest discover -s scripts -p 'test_category_pages.py'
These contracts catch empty routes, wrong locale targets, broken navigation,
uncited/changed excerpts, and accidental collection on previously untracked pages.
"""

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

import validate_aeo_content as validator

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://access.framontmanagement.com"
PAIRS = [
    ("funds/", "it/fondi/", "funds", "what-is-an-alternative-investment-fund.html", "it/cos-e-un-fia.html", "eu-aifmd-2011-61"),
    ("amc/", "it/amc/", "amc", "amc-actively-managed-certificates.html", "it/amc-certificati-gestione-attiva.html", "imaps-eti-programme"),
    ("eti/", "it/eti/", "eti", "what-is-an-eti.html", "it/cos-e-un-eti.html", "eu-prospectus-2017-1129"),
    ("deals/", "it/deals/", "deals", "private-credit-explained.html", "it/credito-privato-spiegato.html", "imf-gfsr-2024-private-credit"),
]


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.meta, self.links, self.alternates = {}, [], {}
        self.canonical = ""
        self.h1 = self.forms = 0
        self.scripts, self.ld, self.text, self.ids = [], [], [], set()
        self.hidden = 0
        self.ld_text = None
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta":
            self.meta[a.get("property", a.get("name"))] = a.get("content", "")
        if tag in {"a", "link"} and a.get("href"):
            self.links.append(a["href"])
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a["href"]
        if tag == "link" and a.get("hreflang"):
            self.alternates[a["hreflang"]] = a["href"]
        if tag == "h1":
            self.h1 += 1
        if tag == "form":
            self.forms += 1
        if tag == "script":
            self.scripts.append(a)
            self.ld_text = [] if a.get("type") == "application/ld+json" else None
        if tag in {"script", "style", "head"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag == "script" and self.ld_text is not None:
            self.ld.append(json.loads("".join(self.ld_text)))
            self.ld_text = None
        if tag in {"script", "style", "head"}:
            self.hidden -= 1

    def handle_data(self, data):
        if self.ld_text is not None:
            self.ld_text.append(data)
        if self.hidden == 0:
            self.text.append(data)


class CategoryPages(unittest.TestCase):
    def pages(self):
        for en, it, key, en_source, it_source, source_id in PAIRS:
            for lang, route, source in [("en", en, en_source), ("it", it, it_source)]:
                path = ROOT / route / "index.html"
                self.assertTrue(path.is_file(), f"Missing readable category route /{route}")
                raw = path.read_text()
                yield lang, route, source, source_id, key, en, it, raw, Page(raw)

    def test_static_routes_are_readable_and_keep_existing_access_flow(self):
        for lang, route, source, sid, key, en, it, raw, page in self.pages():
            with self.subTest(route=route):
                self.assertEqual(page.h1, 1)
                self.assertGreaterEqual(len(" ".join(page.text).strip()), 1200)
                self.assertIn(f"/#/{lang}/{key}", page.links)
                self.assertIn("/compare/" if lang == "en" else "/it/confronto/", page.links)
                self.assertIn("/structure/" if lang == "en" else "/it/struttura/", page.links)
                guides = {x for x in page.links if x.startswith("/articles/") and x.endswith(".html")}
                self.assertGreaterEqual(len(guides), 3)
                report = validator.Report()
                validator.check_static_page(route + "index.html", report, lang)
                self.assertEqual(report.errors, [])

    def test_metadata_describes_real_language_pairs(self):
        for lang, route, source, sid, key, en, it, raw, page in self.pages():
            with self.subTest(route=route):
                canonical = SITE + "/" + route
                self.assertEqual(page.lang, lang)
                self.assertEqual(page.canonical, canonical)
                self.assertEqual(page.alternates, {"en": SITE + "/" + en, "it": SITE + "/" + it, "x-default": SITE + "/" + en})
                self.assertEqual(page.meta["og:url"], canonical)
                self.assertEqual(page.meta["og:locale"], "en_GB" if lang == "en" else "it_IT")
                self.assertTrue(page.meta.get("description"))
                objects = [obj for block in page.ld for obj in block.get("@graph", [block])]
                collection = next(x for x in objects if x.get("@type") == "CollectionPage")
                self.assertEqual(collection["url"], canonical)
                self.assertEqual(collection["inLanguage"], lang)
                crumb = next(x for x in objects if x.get("@type") == "BreadcrumbList")
                self.assertEqual(crumb["itemListElement"][-1]["item"], canonical)
                self.assertFalse(any("reviewedBy" in obj for obj in objects))

    def test_excerpts_keep_original_source_markup_and_full_guide_link(self):
        for lang, route, source, sid, key, en, it, raw, page in self.pages():
            with self.subTest(route=route):
                original = (ROOT / "articles" / source).read_text()
                claims = re.findall(r'<span class="claim" data-source-id="[^"]+"[^>]*>.*?</span>', raw, re.S)
                self.assertTrue(claims, "The excerpt must carry its original evidence")
                for claim in claims:
                    self.assertIn(claim, original, "Do not alter a reviewed excerpt or its citation")
                parsed = validator.parse_page(ROOT / route / "index.html")
                self.assertEqual({x["source_id"] for x in parsed.claims}, {sid})
                self.assertIn("/articles/" + source, page.links)

    def test_local_links_resolve_without_new_tracking_or_forms(self):
        for lang, route, source, sid, key, en, it, raw, page in self.pages():
            with self.subTest(route=route):
                self.assertEqual(page.forms, 0)
                self.assertTrue(all(s.get("type") == "application/ld+json" and "src" not in s for s in page.scripts))
                for href in page.links:
                    url = urlsplit(href)
                    if url.netloc and url.netloc != "access.framontmanagement.com":
                        continue
                    if url.scheme not in {"", "https", "http"}:
                        continue
                    path = unquote(url.path)
                    target = ROOT / path.lstrip("/") if path.startswith("/") else ROOT / route / path
                    if target.is_dir():
                        target = target / "index.html"
                    self.assertTrue(target.is_file(), f"Broken local target {route} -> {href}")


if __name__ == "__main__":
    unittest.main()
