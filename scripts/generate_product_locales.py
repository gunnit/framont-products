#!/usr/bin/env python3
"""Generate English and German product routes from the authored IT sources.

English pages come from the authored English spans in the IT sources. German
pages (only the routes in LOCALE_ROUTES) come from a reviewed dictionary in
i18n/de/<route>.json that maps each authored English span to its German text.

No translation service or build dependency. Run normally to regenerate, or with
--check to fail if a committed page has drifted from its source, if an English
span has no German entry, or if the German dictionary keeps entries the page no
longer uses. --dump-missing PATH writes the untranslated spans as a JSON stub.
Financial prose and FAQ answers come only from authored source text.
"""
from __future__ import annotations

import argparse
import copy
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://access.framontmanagement.com"
ROUTES = ("amc/noctiluca-capital", "amc/zalphyx-yield-strategies", "eti/value-edge-snowwhite", "eti/heraklit-strategy")
# Routes that also publish a German page at /de/<route>/, from i18n/de/<route>.json.
LOCALE_ROUTES = {"de": ("eti/heraklit-strategy",)}
OG_LOCALE = {"it": "it_IT", "en": "en_GB", "de": "de_DE"}
I18N = ROOT / "i18n"
# Shared Italian/English UI strings with no language spans, in German.
DE_LABELS = {"Lingua / Language": "Sprache"}
DE_PLACEHOLDERS = {"KID, prospetto, ISIN, sottoscrizione / subscription": "Basisinformationsblatt, Prospekt, ISIN, Zeichnung"}
DE_OPTIONS = {
    "Investitore al dettaglio / Retail investor": "Privatanleger",
    "Investitore professionale / Professional investor": "Professioneller Anleger",
    "Investitore istituzionale / Institutional investor": "Institutioneller Anleger",
    "Consulente o distributore / Adviser or distributor": "Berater oder Vertriebspartner",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, start, opening_end):
        self.tag, self.attrs, self.start, self.opening_end = tag, dict(attrs), start, opening_end
        self.closing_start = self.end = opening_end
        self.children = []

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source, self.nodes, self.stack = source, [], []
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer("\n", source))
        self.feed(source)

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.source_offset()
        node = Node(tag, attrs, start, start + len(self.get_starttag_text()))
        self.nodes.append(node)
        if self.stack:
            self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                node = self.stack[index]
                node.closing_start = self.source_offset()
                node.end = self.source.index(">", node.closing_start) + 1
                del self.stack[index:]
                return

    def inner(self, node):
        return self.source[node.opening_end:node.closing_start]

    def text(self, node):
        return html.unescape(re.sub(r"<[^>]*>", "", self.inner(node))).strip()


def apply_edits(source, edits):
    output, cursor = [], 0
    for start, end, replacement in sorted(edits):
        if start < cursor:
            raise ValueError("Overlapping locale edits")
        output.extend((source[cursor:start], replacement))
        cursor = end
    output.append(source[cursor:])
    return "".join(output)


def set_attribute(tag, key, value):
    pattern = r'\s' + re.escape(key) + r'="[^"]*"'
    replacement = "" if value is None else f' {key}="{html.escape(value, quote=True)}"'
    if re.search(pattern, tag):
        return re.sub(pattern, lambda _: replacement, tag)
    return re.sub(r"(?=/?>$)", lambda _: replacement, tag, count=1)


def dictionary_value(source, name, locale):
    block = re.search(r"var " + name + r" = \{(.*?)\n  \};", source, re.S)
    if not block:
        raise ValueError(f"Missing authored {name} dictionary")
    value = re.search(r"\b" + locale + r":'((?:\\.|[^'])*)'", block.group(1))
    if not value:
        raise ValueError(f"Missing authored {name}.{locale}")
    return value.group(1).replace("\\'", "'")


def english_body(source):
    doc = Document(source)
    removed = [(n.start, n.end) for n in doc.nodes if n.tag == "span" and n.has_class("t-it")]
    translated = [(n.start, n.end) for n in doc.nodes if n.has_class("t-it") or n.has_class("t-en")]
    edits = [(start, end, "") for start, end in removed]
    for node in doc.nodes:
        if node.tag == "span" and node.has_class("t-en") and not any(a <= node.start < b for a, b in removed):
            edits.extend(((node.start, node.opening_end, ""), (node.closing_start, node.end, "")))
        # Shared source labels have no language spans. Only touch leaf text,
        # excluding authored translations, attributes, identifiers and code.
        if node.tag not in ("b", "td", "span", "div", "small") or node.children or any(a <= node.start < b for a, b in translated):
            continue
        value = doc.inner(node)
        localized = value
        number = r"(?:USD\s+)?[+\-−]?\d[\d.,]*(?:%|x|×)?"
        if re.fullmatch(number + r"(?:\s+-\s+" + number + r")?", value.strip()):
            def format_number(match):
                token = match.group()
                if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", token):
                    return token.replace(".", ",")
                if re.fullmatch(r"\d+,\d{1,2}", token):
                    return token.replace(",", ".")
                return token
            localized = re.sub(r"\d[\d.,]*", format_number, value)
        elif node.tag == "small" and node.has_class("pre") and value == "fino a":
            localized = "up to"  # Already authored in SnowWhite's English copy.
        elif node.tag == "b" and re.fullmatch(r"24 (?:set|mar) 202[6-9]", value):
            localized = value.replace(" set ", " Sep ").replace(" mar ", " Mar ")  # Existing EN month labels; same dates.
        if localized != value:
            edits.append((node.opening_end, node.closing_start, localized))
    # Nested translated spans inside an Italian node are already removed by it.
    edits = [edit for edit in edits if not any(a < edit[0] and edit[1] <= b for a, b in removed)]
    return apply_edits(source, edits)


def german_body(source, segments, missing):
    """Replace each authored English span with its reviewed German text."""
    doc = Document(source)
    removed = [(n.start, n.end) for n in doc.nodes if n.tag == "span" and n.has_class("t-it")]
    english = [n for n in doc.nodes if n.tag == "span" and n.has_class("t-en") and not any(a <= n.start < b for a, b in removed)]
    english = [n for n in english if not any(o is not n and o.start <= n.start and n.end <= o.end for o in english)]
    replaced = [(n.start, n.end) for n in english]
    edits = [(start, end, "") for start, end in removed]
    for node in english:
        key = doc.inner(node)
        if key in segments:
            edits.append((node.start, node.end, segments[key]))
        elif key not in missing:
            missing.append(key)
    translated = removed + replaced
    for node in doc.nodes:
        if node.tag == "small" and node.has_class("pre") and doc.inner(node) == "fino a" and not any(a <= node.start < b for a, b in translated):
            edits.append((node.opening_end, node.closing_start, "bis zu"))
    # Keep only outermost edits: spans nested in a removed or replaced span go with it.
    edits = [edit for edit in edits if not any(a <= edit[0] and edit[1] <= b and (a, b) != (edit[0], edit[1]) for a, b in translated)]
    return apply_edits(source, edits)


def locale_url(route, locale):
    return SITE + "/" + ("" if locale == "en" else locale + "/") + route + "/"


def locale_schema(rendered, route, title, description, locale="en"):
    doc = Document(rendered)
    old = next(n for n in doc.nodes if n.tag == "script" and n.attrs.get("type") == "application/ld+json")
    graph = json.loads(doc.inner(old))["@graph"]
    by_type = {node["@type"]: node for node in graph}
    url, old_url = locale_url(route, locale), SITE + "/it/" + route + "/"

    def select(kind, keys):
        node = by_type[kind]
        return {key: copy.deepcopy(node[key]) for key in keys if key in node}

    org = select("Organization", ("@type", "@id", "name", "alternateName", "url", "logo", "address", "telephone", "email", "areaServed", "sameAs"))
    org["identifier"] = [copy.deepcopy(value) for value in by_type["Organization"].get("identifier", []) if value.get("name") == "VAT"]
    product = select("FinancialProduct", ("@type", "@id", "name", "identifier", "provider", "category"))
    product.update(url=url, description=description)
    if route.startswith("eti/"):
        product["name"] = doc.text(next(n for n in doc.nodes if n.tag == "h1"))
    breadcrumb = {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": org["name"], "item": "https://www.framontmanagement.com/"},
        {"@type": "ListItem", "position": 2, "name": "Framont Access", "item": SITE + "/"},
        {"@type": "ListItem", "position": 3, "name": product["name"], "item": url},
    ]}
    faq = {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": []}
    for details in (n for n in doc.nodes if n.tag == "details" and n.attrs.get("id", "").startswith("faq-")):
        question = next(n for n in details.children if n.tag == "summary")
        answer = next(n for n in details.children if n.has_class("ans"))
        faq["mainEntity"].append({"@type": "Question", "name": doc.text(question), "acceptedAnswer": {"@type": "Answer", "text": doc.text(answer)}})
    page = select("WebPage", ("@type", "@id", "url", "publisher", "isPartOf", "datePublished", "dateModified", "breadcrumb", "mainEntity", "about", "speakable"))
    hero = next(n for n in doc.nodes if n.has_class("hero-lede"))
    page.update(name=title, inLanguage=locale, abstract=doc.text(hero))
    result = [org, product, breadcrumb, faq, page]
    if "Person" in by_type:
        result.insert(1, select("Person", ("@type", "@id", "name", "url", "image", "sameAs")))
    serialized = json.dumps({"@context": "https://schema.org", "@graph": result}, ensure_ascii=False, indent=2)
    return serialized.replace(old_url, url)


def generate(source, route, locale="en", segments=None, missing=None):
    title = dictionary_value(source, "TITLE", locale)
    description = dictionary_value(source, "DESC", locale)
    rendered = english_body(source) if locale == "en" else german_body(source, segments or {}, missing if missing is not None else [])
    doc, edits = Document(rendered), []
    url = locale_url(route, locale)
    source_alternates = [n.attrs.get("content", "") for n in Document(source).nodes if n.tag == "meta" and n.attrs.get("property") == "og:locale:alternate"]
    alternates = [OG_LOCALE["it"]] + [code for code in source_alternates if code != OG_LOCALE[locale]]
    alternate_index = 0
    simple_labels = {
        "Lingua / Language": "Language", "Confermo di essere un investitore professionale": "I confirm, I am a professional investor",
        "Confermo di essere un investitore professionale o qualificato": "I confirm, I am a professional or qualified investor",
        "Azioni e opzioni": "Equities and options", "Futures su indici e bond": "Index and bond futures",
        "Valute e materie prime": "Currencies and commodities", "Componenti del portafoglio": "Portfolio components", "Orizzonte tipico": "Typical horizon",
    }
    placeholders = {
        "Term sheet, fact sheet, data room, sottoscrizione / subscription": "Term sheet, fact sheet, data room, subscription",
        "Term sheet, presentazione, disponibilità / availability": "Term sheet, presentation, availability",
        "KID, prospetto, ISIN, sottoscrizione / subscription": "KID, prospectus, ISIN, subscription",
    }
    for node in doc.nodes:
        opening = rendered[node.start:node.opening_end]
        attrs = node.attrs
        changes = {}
        if node.tag == "html": changes.update(lang=locale, **{"data-lang": locale})
        if node.tag == "title": edits.append((node.opening_end, node.closing_start, html.escape(title)))
        if node.tag == "meta":
            key = attrs.get("name", attrs.get("property"))
            values = {"description": description, "og:title": title, "twitter:title": title, "og:description": description, "twitter:description": description, "og:url": url, "og:locale": OG_LOCALE[locale]}
            if key in values: changes["content"] = values[key]
            if key == "og:locale:alternate":
                changes["content"] = alternates[alternate_index]
                alternate_index += 1
            if key == "og:image:alt" and route.startswith("eti/"):
                heading = doc.text(next(n for n in doc.nodes if n.tag == "h1"))
                author = next(n.attrs["content"] for n in doc.nodes if n.tag == "meta" and n.attrs.get("name") == "author")
                changes["content"] = heading + ", " + author
        if node.tag == "link" and attrs.get("rel") == "canonical": changes["href"] = url
        if node.tag == "input":
            values = {"language": locale, "page": url, "redirect": url + "?sent=1#contact"}
            if attrs.get("name") in values: changes["value"] = values[attrs["name"]]
        if node.tag == "a" and "data-language" in attrs: changes["aria-current"] = "page" if attrs["data-language"] == locale else None
        if attrs.get("aria-label") in simple_labels: changes["aria-label"] = simple_labels[attrs["aria-label"]] if locale == "en" else DE_LABELS[attrs["aria-label"]]
        if attrs.get("placeholder") in placeholders: changes["placeholder"] = placeholders[attrs["placeholder"]] if locale == "en" else DE_PLACEHOLDERS[attrs["placeholder"]]
        if node.has_class("bars"):
            # Use the exact already-visible instrument codes and values, never
            # retranslate the financial breakdown in the Italian aria label.
            changes["aria-label"] = ", ".join(" ".join(doc.text(n) for n in bar.children if n.tag in ("b", "span")) for bar in node.children if bar.has_class("bar"))
        if attrs.get("src") == "assets/giovanni-zibordi-ideatore-strategia-snowwhite.jpg":
            changes["src"] = "/it/eti/value-edge-snowwhite/" + attrs["src"]
            changes["alt"] = "Giovanni Zibordi"
        if node.tag == "a" and attrs.get("href") in ("/it/confronto/", "/it/struttura/"):
            changes["href"] = {"/it/confronto/": "/compare/", "/it/struttura/": "/structure/"}[attrs["href"]]
        if node.tag == "option" and " / " in doc.text(node):
            label = doc.text(node).split(" / ")[-1] if locale == "en" else DE_OPTIONS[doc.text(node)]
            edits.append((node.opening_end, node.closing_start, html.escape(label)))
        if node.tag == "script" and attrs.get("type") == "application/ld+json":
            edits.append((node.opening_end, node.closing_start, "\n" + locale_schema(rendered, route, title, description, locale) + "\n"))
        for key, value in changes.items(): opening = set_attribute(opening, key, value)
        if changes: edits.append((node.start, node.opening_end, opening))
    return apply_edits(rendered, edits)


def load_segments(locale, route):
    path = I18N / locale / (route + ".json")
    if not path.exists():
        return path, {}
    return path, json.loads(path.read_text(encoding="utf-8"))["segments"]


def used_segments(source):
    doc = Document(source)
    removed = [(n.start, n.end) for n in doc.nodes if n.tag == "span" and n.has_class("t-it")]
    english = [n for n in doc.nodes if n.tag == "span" and n.has_class("t-en") and not any(a <= n.start < b for a, b in removed)]
    return {doc.inner(n) for n in english if not any(o is not n and o.start <= n.start and n.end <= o.end for o in english)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated routes are absent or stale")
    parser.add_argument("--dump-missing", metavar="PATH", help="write untranslated German spans to PATH as a JSON stub")
    args = parser.parse_args()
    stale, problems, untranslated = [], [], {}
    for locale, routes in LOCALE_ROUTES.items():
        for route in routes:
            source_text = (ROOT / "it" / route / "index.html").read_text(encoding="utf-8")
            path, segments = load_segments(locale, route)
            missing = []
            output = generate(source_text, route, locale, segments, missing)
            unused = sorted(set(segments) - used_segments(source_text))
            label = str(path.relative_to(ROOT))
            if missing:
                problems.append(f"{label}: {len(missing)} English span(s) have no {locale} translation, first: {missing[0][:90]!r}")
                untranslated.update({key: "" for key in missing})
            if unused:
                problems.append(f"{label}: {len(unused)} entr(y/ies) no longer used by the page, first: {unused[0][:90]!r}")
            target = ROOT / locale / route / "index.html"
            if missing:
                continue
            if args.check:
                if not target.exists() or target.read_text(encoding="utf-8") != output: stale.append(str(target.relative_to(ROOT)))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(output, encoding="utf-8")
                print("Generated", target.relative_to(ROOT))
    if args.dump_missing:
        Path(args.dump_missing).write_text(json.dumps(untranslated, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Wrote {len(untranslated)} untranslated span(s) to {args.dump_missing}")
    for route in ROUTES:
        source = ROOT / "it" / route / "index.html"
        target = ROOT / route / "index.html"
        output = generate(source.read_text(encoding="utf-8"), route)
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != output: stale.append(str(target.relative_to(ROOT)))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(output, encoding="utf-8")
            print("Generated", target.relative_to(ROOT))
    if problems:
        parser.exit(1, "\n".join(problems) + "\n")
    if stale:
        parser.exit(1, "Stale generated product routes: " + ", ".join(stale) + "\nRun python3 scripts/generate_product_locales.py\n")
    if args.check:
        print(f"PASS: all {len(ROUTES)} generated English product routes match their authored sources")
        for locale, routes in LOCALE_ROUTES.items():
            print(f"PASS: all {len(routes)} generated {locale} product route(s) match their sources and reviewed translations")


if __name__ == "__main__": main()
