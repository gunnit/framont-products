# Framont Access

Static site for Framont Access (`https://access.framontmanagement.com/`), deployed
from this repository by GitHub Pages. There is no build step: what is committed is
what is served.

## Layout

| Path | What it holds |
|---|---|
| `index.html` | The single-page product platform |
| `articles/`, `articles/it/` | Bilingual Insights articles |
| `compare/`, `structure/`, `glossary/` | Utility routes (English) |
| `it/confronto/`, `it/struttura/`, `it/glossario/` | Utility routes (Italian) |
| `data/aeo-sources.json` | Evidence registry backing every sourced claim |
| `docs/editorial-and-review-policy.md` | Byline, review, sourcing and correction policy |
| `scripts/validate_aeo_content.py` | Citation-readiness validator |

## Editorial workflow

Every material legal, numeric, licence, listing, eligibility or product-structure
claim must point at a record in `data/aeo-sources.json` using a claim marker:

```html
<span class="claim" data-source-id="imf-gfsr-2024-private-credit" data-as-of="2024-04-16">USD 2.1 trillion</span>
```

Claims that are true in general, true only in one jurisdiction, or true only of a
Framont product are labelled separately with `data-scope`:

```html
<span class="scope" data-scope="general">General rule</span>
<span class="scope" data-scope="jurisdiction">Malta</span>
<span class="scope" data-scope="framont">Framont example</span>
```

Two rules that the validator enforces and that are easy to forget:

1. A factual change lands in the English page **and** its Italian counterpart in
   the same pull request. The two pages must rest on an identical set of sources.
2. A named `reviewedBy` ships only while `reviewer.status` in the registry is
   `approved` and the written consent is recorded alongside it.

Full policy: [`docs/editorial-and-review-policy.md`](docs/editorial-and-review-policy.md).

## Validation

```bash
python3 scripts/validate_aeo_content.py
```

Exit code 0 means the article set is citation-ready. To also resolve every source
URL over the network:

```bash
python3 scripts/validate_aeo_content.py --links
```

Some authoritative publishers (EUR-Lex, IMF, SSRN, the MFSA register) answer
robots with a challenge or a refusal while serving browsers normally. Those
records declare `access.automated: "bot-protected"` in the registry, and the link
check reports them without failing the run. Anything that genuinely does not
resolve is an error.

### Adding a page

The validator checks a declared list of pages, not whatever happens to be on
disk, so a new page is only checked once it is listed. It reads `sitemap.xml`
back to those lists and warns about any published page that no list covers —
which is the reminder that the page still needs a home in one of these:

| List | For |
|---|---|
| `ARTICLE_PAIRS` | A bilingual article and its counterpart. Both must rest on the same evidence. |
| `STATIC_ROUTES` | A bilingual utility route that has to read without JavaScript. |
| `SOLO_ROUTES` | A page shipped in one language, so there is no counterpart to hold it to parity. |
| `EXEMPT_PAGES` | A page the static checks do not describe. Say why: the note is the record. |

A page listed in `sitemap.xml` with no file behind it is an error, not a warning.

## Local preview

```bash
python3 -m http.server 8000
```
