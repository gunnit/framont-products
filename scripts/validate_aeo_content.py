#!/usr/bin/env python3
"""Validate the citation readiness of the Framont Access article set.

Standard library only, so it runs anywhere Python 3 runs and adds no build step
to a static site that deploys straight from the repository.

What it enforces:

  * every ``data-source-id`` used in a page exists in ``data/aeo-sources.json``;
  * every registry record carries a well-formed absolute URL;
  * an English page and its Italian counterpart rest on the same evidence
    (identical set of ``data-source-id`` values), so a factual change cannot
    land in one language only;
  * every page declares a canonical URL, reciprocal ``hreflang``, ``Article``
    and ``FAQPage`` structured data, a visible review date and a matching
    ``dateModified``;
  * every claim marker holding a time-sensitive number carries ``data-as-of``;
  * every article canonical URL appears in both ``sitemap.xml`` and ``llms.txt``;
  * every page ``sitemap.xml`` ships exists on disk and is covered by a check
    list, so a new page cannot go live unexamined;
  * a named ``reviewedBy`` only ever ships when the registry records the
    reviewer's consent as ``approved``.

Usage::

    python3 scripts/validate_aeo_content.py            # content checks
    python3 scripts/validate_aeo_content.py --links    # also resolve every URL

Exit code is 0 when there are no errors, 1 otherwise. Warnings never fail the
run; they are the things a human should look at, not the things that block a
deployment.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "aeo-sources.json"
SITEMAP_PATH = ROOT / "sitemap.xml"
LLMS_PATH = ROOT / "llms.txt"
SITE = "https://access.framontmanagement.com"

# English page -> Italian counterpart. Both members of a pair must rest on the
# same evidence; the parity check below is the only thing standing between a
# bilingual site and two languages that quietly disagree about the facts.
ARTICLE_PAIRS = [
    ("articles/what-is-an-eti.html", "articles/it/cos-e-un-eti.html"),
    ("articles/amc-actively-managed-certificates.html", "articles/it/amc-certificati-gestione-attiva.html"),
    ("articles/how-to-evaluate-systematic-strategies.html", "articles/it/valutare-strategie-sistematiche.html"),
    ("articles/how-to-read-a-priips-kid.html", "articles/it/come-leggere-un-kid-priips.html"),
    ("articles/what-is-an-alternative-investment-fund.html", "articles/it/cos-e-un-fia.html"),
    ("articles/private-credit-explained.html", "articles/it/credito-privato-spiegato.html"),
    ("articles/choose-aif-amc-or-eti.html", "articles/it/scegliere-aif-amc-o-eti.html"),
    ("articles/launch-investment-vehicle-under-20m.html", "articles/it/lanciare-veicolo-investimento-sotto-20m.html"),
    ("articles/malta-aifm-setup-notification-distribution.html", "articles/it/aifm-malta-setup-notifica-distribuzione.html"),
]

# Utility routes that must be readable without running JavaScript.
STATIC_ROUTES = [
    ("compare/index.html", "it/confronto/index.html"),
    ("structure/index.html", "it/struttura/index.html"),
    ("glossary/index.html", "it/glossario/index.html"),
    ("editorial-policy/index.html", "it/politica-editoriale/index.html"),
    ("articles/index.html", "articles/it/index.html"),
]

# Pages that ship in a single language, so there is no counterpart to hold them
# to evidence parity. They still have to stand up without JavaScript, carry a
# correct canonical and point their own hreflang at themselves.
SOLO_ROUTES = [
    ("it/eti/erere-quant-income/index.html", "it"),
]

# Pages the sitemap ships that the static checks deliberately do not describe.
# The reason lives here so that an unchecked page stays a decision somebody made
# once, rather than an omission nobody noticed.
EXEMPT_PAGES = {
    "index.html": "the product platform is a single-page app: it carries an H1 per "
    "view and builds its markup from client-side templates, so the static-route "
    "checks do not apply",
}

# A number is treated as time-sensitive when it states a magnitude, a share or a
# money amount -- the kinds of figure that go stale silently and that an answer
# engine will happily quote years later without the date.
TIME_SENSITIVE = re.compile(
    r"""(?xi)
    \b(?:USD|EUR|CHF|GBP|€|\$|£)\s?[\d.,]+          # money amounts
    | \b[\d.,]+\s?(?:trillion|billion|million|miliardi|milioni|mila\s+miliardi)\b
    | \b[\d.,]+\s?(?:%|per\s+cent|percento|per\s+cento)\b
    """
)


class PageParser(HTMLParser):
    """Pull out only what the checks need: link rels, marker attributes, JSON-LD."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.hreflang: dict[str, str] = {}
        self.ld_blocks: list[str] = []
        self.claims: list[dict[str, str]] = []
        self.scopes: list[str] = []
        self.h1_count = 0
        self.review_dates: list[str] = []
        self.text_len = 0
        self._in_ld = False
        self._claim_stack: list[dict] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "link":
            rel = a.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = a.get("href", "")
            elif rel == "alternate" and a.get("hreflang"):
                self.hreflang[a["hreflang"].lower()] = a.get("href", "")
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_ld = True
            self._buf = []
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "time" and "data-review-date" in a:
            self.review_dates.append(a.get("datetime", ""))

        if "data-source-id" in a:
            claim = {
                "source_id": a["data-source-id"],
                "as_of": a.get("data-as-of", ""),
                "text": "",
            }
            self.claims.append(claim)
            self._claim_stack.append({"tag": tag, "claim": claim, "depth": 0})
        elif self._claim_stack and tag == self._claim_stack[-1]["tag"]:
            self._claim_stack[-1]["depth"] += 1

        if "data-scope" in a:
            self.scopes.append(a["data-scope"])

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld_blocks.append("".join(self._buf))
            self._in_ld = False
            self._buf = []
        if self._claim_stack and tag == self._claim_stack[-1]["tag"]:
            if self._claim_stack[-1]["depth"] == 0:
                self._claim_stack.pop()
            else:
                self._claim_stack[-1]["depth"] -= 1

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)
            return
        self.text_len += len(data.strip())
        for frame in self._claim_stack:
            frame["claim"]["text"] += data


def covered_pages() -> set[str]:
    """Every page some check list looks at."""
    covered = {rel for pair in ARTICLE_PAIRS for rel in pair}
    covered |= {rel for pair in STATIC_ROUTES for rel in pair}
    covered |= {rel for rel, _lang in SOLO_ROUTES}
    return covered


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        sys.exit(f"FATAL: missing source registry at {REGISTRY_PATH}")
    with REGISTRY_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def ld_types(parser: PageParser) -> set[str]:
    """Collect every @type present across the page's JSON-LD blocks."""
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                found.add(t)
            elif isinstance(t, list):
                found.update(x for x in t if isinstance(x, str))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in parser.ld_blocks:
        try:
            walk(json.loads(block))
        except json.JSONDecodeError:
            found.add("__INVALID_JSON__")
    return found


def ld_objects(parser: PageParser) -> list[dict]:
    out: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            out.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in parser.ld_blocks:
        try:
            walk(json.loads(block))
        except json.JSONDecodeError:
            pass
    return out


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checked = 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def check_registry(registry: dict, report: Report) -> dict[str, str]:
    """Validate the registry and return a mapping of source id -> url."""
    ids: dict[str, str] = {}
    for record in registry.get("sources", []):
        sid = record.get("id", "")
        if not sid:
            report.error("registry: a source record has no id")
            continue
        if sid in ids:
            report.error(f"registry: duplicate source id '{sid}'")
        url = record.get("url", "")
        ids[sid] = url
        parsed = urlparse(url)
        if not url or parsed.scheme not in ("http", "https") or not parsed.netloc:
            report.error(f"registry: source '{sid}' has an empty or malformed url: {url!r}")
        for field in ("title", "publisher", "source_type", "as_of", "last_checked"):
            if not record.get(field):
                report.error(f"registry: source '{sid}' is missing required field '{field}'")
    if not ids:
        report.error("registry: no sources defined")
    return ids


def check_page(rel: str, lang: str, registry_ids: dict[str, str], reviewer_approved: bool, report: Report) -> PageParser | None:
    path = ROOT / rel
    if not path.exists():
        report.error(f"{rel}: file does not exist")
        return None

    report.checked += 1
    parser = parse_page(path)
    expected_canonical = f"{SITE}/{rel}".replace("/index.html", "/")

    if not parser.canonical:
        report.error(f"{rel}: no canonical URL")
    elif parser.canonical != expected_canonical:
        report.error(f"{rel}: canonical is {parser.canonical}, expected {expected_canonical}")

    for code in ("en", "it", "x-default"):
        if code not in parser.hreflang:
            report.error(f"{rel}: missing hreflang '{code}'")

    if parser.h1_count != 1:
        report.error(f"{rel}: expected exactly one H1, found {parser.h1_count}")

    types = ld_types(parser)
    if "__INVALID_JSON__" in types:
        report.error(f"{rel}: a JSON-LD block does not parse")
    for required in ("Article", "FAQPage", "BreadcrumbList"):
        if required not in types:
            report.error(f"{rel}: JSON-LD is missing a {required} node")

    if not parser.review_dates:
        report.error(f"{rel}: no visible review date (expected <time data-review-date>)")
    visible_review = parser.review_dates[0] if parser.review_dates else ""

    date_modified = ""
    reviewed_by = None
    for obj in ld_objects(parser):
        if obj.get("@type") == "Article":
            date_modified = obj.get("dateModified", "") or date_modified
            reviewed_by = obj.get("reviewedBy", reviewed_by)
    if not date_modified:
        report.error(f"{rel}: Article schema has no dateModified")
    elif visible_review and date_modified != visible_review:
        report.error(
            f"{rel}: visible review date {visible_review} does not match dateModified {date_modified}"
        )

    if reviewed_by and not reviewer_approved:
        report.error(f"{rel}: reviewedBy is published but the registry reviewer status is not 'approved'")
    if reviewer_approved and not reviewed_by:
        report.warn(f"{rel}: reviewer consent is on file but the page publishes no reviewedBy")

    for claim in parser.claims:
        if claim["source_id"] not in registry_ids:
            report.error(f"{rel}: data-source-id '{claim['source_id']}' is not in the registry")
        if TIME_SENSITIVE.search(claim["text"]) and not claim["as_of"]:
            snippet = " ".join(claim["text"].split())[:70]
            report.error(f"{rel}: time-sensitive figure without data-as-of near: '{snippet}'")

    if not parser.claims:
        report.error(f"{rel}: no evidence markers (data-source-id) anywhere on the page")

    domains = {
        urlparse(registry_ids[c["source_id"]]).netloc
        for c in parser.claims
        if c["source_id"] in registry_ids
    }
    domains.discard("")
    if len(domains) < 2:
        report.error(
            f"{rel}: cites {len(domains)} independent source domain(s); at least 2 are required"
        )

    if lang == "en" and parser.hreflang.get("en") != parser.canonical:
        report.error(f"{rel}: hreflang 'en' does not point at its own canonical")
    if lang == "it" and parser.hreflang.get("it") != parser.canonical:
        report.error(f"{rel}: hreflang 'it' does not point at its own canonical")

    return parser


def check_parity(en_rel: str, it_rel: str, en: PageParser, it: PageParser, report: Report) -> None:
    en_ids = sorted({c["source_id"] for c in en.claims})
    it_ids = sorted({c["source_id"] for c in it.claims})
    missing_in_it = [i for i in en_ids if i not in it_ids]
    missing_in_en = [i for i in it_ids if i not in en_ids]
    if missing_in_it:
        report.error(f"{it_rel}: missing evidence present in English: {', '.join(missing_in_it)}")
    if missing_in_en:
        report.error(f"{en_rel}: missing evidence present in Italian: {', '.join(missing_in_en)}")

    en_scopes = sorted(set(en.scopes))
    it_scopes = sorted(set(it.scopes))
    if en_scopes != it_scopes:
        report.error(
            f"{en_rel} / {it_rel}: scope labels differ ({en_scopes} vs {it_scopes})"
        )

    if en.hreflang.get("it") != it.canonical:
        report.error(f"{en_rel}: hreflang 'it' does not point at {it.canonical}")
    if it.hreflang.get("en") != en.canonical:
        report.error(f"{it_rel}: hreflang 'en' does not point at {en.canonical}")


def check_static_page(rel: str, report: Report, lang: str | None = None) -> str:
    """Check a route that has to stand up without JavaScript; return its canonical."""
    path = ROOT / rel
    if not path.exists():
        report.error(f"{rel}: file does not exist")
        return ""

    raw = path.read_text(encoding="utf-8")
    parser = parse_page(path)
    report.checked += 1

    if parser.h1_count != 1:
        report.error(f"{rel}: expected exactly one H1, found {parser.h1_count}")
    if parser.text_len < 1200:
        report.error(
            f"{rel}: only {parser.text_len} characters of static text; "
            "the route must be readable without JavaScript"
        )
    if "{{" in raw:
        report.error(f"{rel}: contains an unrendered template placeholder")
    if "__INVALID_JSON__" in ld_types(parser):
        report.error(f"{rel}: a JSON-LD block does not parse")

    if not parser.canonical:
        report.error(f"{rel}: no canonical URL")
        return ""

    expected = f"{SITE}/{rel}".replace("/index.html", "/")
    if parser.canonical != expected:
        report.error(f"{rel}: canonical is {parser.canonical}, expected {expected}")
    if lang and parser.hreflang.get(lang) != parser.canonical:
        report.error(f"{rel}: hreflang '{lang}' does not point at its own canonical")

    return parser.canonical


def check_coverage(covered: set[str], report: Report) -> None:
    """Hold the check lists to what the site actually ships.

    ``check_discovery`` walks from the check lists to the sitemap and catches a
    page that is checked but unreachable. This walks the other way -- from the
    sitemap to the check lists -- and catches the more likely accident: a page
    that goes live, gets indexed and quoted by an answer engine while no check
    in this file has ever looked at it.
    """
    if not SITEMAP_PATH.exists():
        return
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")
    for url in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap):
        if not url.startswith(f"{SITE}/"):
            continue
        rel = url[len(SITE) + 1 :]
        rel = f"{rel}index.html" if rel.endswith("/") or not rel else rel
        if not (ROOT / rel).exists():
            report.error(f"sitemap.xml lists {url}, but {rel} does not exist")
        elif rel in EXEMPT_PAGES:
            continue
        elif rel not in covered:
            report.warn(
                f"{rel} is published in sitemap.xml but no check list covers it; "
                "add it to ARTICLE_PAIRS, STATIC_ROUTES, SOLO_ROUTES or EXEMPT_PAGES"
            )


def check_discovery(canonicals: list[str], report: Report) -> None:
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8") if SITEMAP_PATH.exists() else ""
    llms = LLMS_PATH.read_text(encoding="utf-8") if LLMS_PATH.exists() else ""
    if not sitemap:
        report.error("sitemap.xml is missing")
    if not llms:
        report.error("llms.txt is missing")
    for url in canonicals:
        if url and url not in sitemap:
            report.error(f"sitemap.xml does not list {url}")
        if url and url not in llms:
            report.error(f"llms.txt does not list {url}")


def check_links(registry: dict, report: Report) -> None:
    """Resolve every registry URL. Bot challenges are reported, not failed."""
    import ssl
    import urllib.error
    import urllib.request

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "*/*",
    }
    for record in registry.get("sources", []):
        url = record.get("url", "")
        sid = record.get("id", "?")
        declared = record.get("access", {}).get("automated", "unknown")
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
            print(f"  ok    {status}  {sid}")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 429) and declared == "bot-protected":
                print(f"  bot   {exc.code}  {sid}  (declared bot-protected)")
            elif exc.code in (401, 403, 429):
                report.warn(f"link: {sid} returned {exc.code}; mark access.automated as 'bot-protected' if this is expected")
            else:
                report.error(f"link: {sid} returned HTTP {exc.code} for {url}")
        except urllib.error.URLError as exc:
            # A certificate that this machine cannot verify is usually a gap in the
            # local trust store rather than a dead source: browsers and curl accept
            # several publisher roots that Python's bundled store does not carry.
            # Retry unverified purely to establish reachability, and downgrade to a
            # warning that names the cause instead of failing a healthy source.
            if isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError):
                try:
                    unverified = ssl._create_unverified_context()
                    request = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(request, timeout=30, context=unverified) as response:
                        status = response.status
                    print(f"  tls   {status}  {sid}  (reachable; certificate not verifiable by this trust store)")
                    report.warn(
                        f"link: {sid} served a certificate this machine cannot verify, but the document is "
                        f"reachable ({status}). Check the CA bundle before treating this as a source problem."
                    )
                    continue
                except Exception:  # noqa: BLE001 - still unreachable, so it is a real finding
                    pass
            report.error(f"link: {sid} did not resolve ({exc.__class__.__name__}: {exc}) for {url}")
        except Exception as exc:  # noqa: BLE001 - any transport failure is a finding
            report.error(f"link: {sid} did not resolve ({exc.__class__.__name__}: {exc}) for {url}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--links", action="store_true", help="also resolve every registry URL over the network")
    args = ap.parse_args()

    registry = load_registry()
    report = Report()
    registry_ids = check_registry(registry, report)

    reviewer = registry.get("reviewer", {})
    reviewer_approved = reviewer.get("status") == "approved"
    if reviewer_approved and not (reviewer.get("consent_evidence") and reviewer.get("consent_date")):
        report.error("registry: reviewer status is 'approved' but consent evidence or date is missing")

    canonicals: list[str] = []
    for en_rel, it_rel in ARTICLE_PAIRS:
        en = check_page(en_rel, "en", registry_ids, reviewer_approved, report)
        it = check_page(it_rel, "it", registry_ids, reviewer_approved, report)
        if en and it:
            check_parity(en_rel, it_rel, en, it, report)
            canonicals.extend([en.canonical, it.canonical])

    for en_rel, it_rel in STATIC_ROUTES:
        for rel, lang in ((en_rel, "en"), (it_rel, "it")):
            canonical = check_static_page(rel, report, lang)
            if canonical:
                canonicals.append(canonical)

    for rel, lang in SOLO_ROUTES:
        canonical = check_static_page(rel, report, lang)
        if canonical:
            canonicals.append(canonical)

    check_discovery(canonicals, report)
    check_coverage(covered_pages(), report)

    if args.links:
        print("\nResolving registry URLs:")
        check_links(registry, report)

    print(f"\nChecked {report.checked} page(s) against {len(registry_ids)} source record(s).")
    for warning in report.warnings:
        print(f"WARN  {warning}")
    for error in report.errors:
        print(f"ERROR {error}")

    if report.errors:
        print(f"\nFAIL — {len(report.errors)} error(s), {len(report.warnings)} warning(s).")
        return 1
    print(f"\nPASS — 0 errors, {len(report.warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
