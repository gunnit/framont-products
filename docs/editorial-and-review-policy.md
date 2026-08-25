# Editorial and review policy — Framont Access Insights

This policy governs the bilingual Insights articles published at
`https://access.framontmanagement.com/articles/`. It exists so that a reader —
or a search engine, or an AI answer engine — can tell who wrote a page, who
checked it, what it rests on, and how to get it corrected.

Last updated: 25 August 2026.

## 1. Who writes and who reviews

**Author.** Articles are written by the **Framont Access editorial team**. No
individual byline is published, and the `author` node in the structured data is
an `Organization` rather than a `Person`. This is deliberate: publishing a named
author requires that named person's verified identity and written consent, and
that has not been established. It is an open item, not an oversight.

**Reviewer.** Regulatory, structural and product-descriptive content is reviewed
by:

> Reviewed by **Gianluigi Montagner**, CEO and Founder – Chief Executive
> Officer, Framont & Partners Management

Italian pages carry the same attribution in the reviewer's own wording:

> Revisionato da **Gianluigi Montagner**, CEO e Founder – Chief Executive
> Officer, Framont & Partners Management

The reviewer validates content on ETIs, AMCs, AIF/FIA, PRIIPs KIDs, private
credit and systematic strategies. **The reviewer is not the author.** Review
means the material has been checked for factual and regulatory accuracy, not
that the reviewer drafted it.

Consent for this attribution — both the fact of it and the exact wording — was
given in writing on 23 August 2026 and is recorded in
`data/aeo-sources.json` under `reviewer.consent_evidence`. The reviewer also
authorised the optional addition of a portfolio manager role; it is not used in
the visible byline, because a portfolio-management title standing next to
product examples would blur the scope of what was actually reviewed. The
permission is recorded so it is not lost.

**Attribution is gated in code.** `scripts/validate_aeo_content.py` fails the
build if a page publishes a named `reviewedBy` while `reviewer.status` in the
registry is anything other than `approved`. Withdrawing consent is therefore a
one-line change that automatically blocks deployment of the attribution.

## 2. Source hierarchy

Sources are preferred in this order, and a lower tier never carries a claim on
its own when a higher tier exists:

1. **Primary law** — EUR-Lex (regulations, directives, delegated acts,
   consolidated texts), national primary legislation and implementing decrees.
2. **Regulator material** — MFSA, FMA Liechtenstein, ESMA, national competent
   authorities: rulebooks, circulars, public registers.
3. **Issuer and fund documents** — base prospectuses, final terms, KIDs,
   offering memoranda, term sheets, exchange listing records.
4. **Institutional research** — IMF, ECB, EBA and equivalent, for market-level
   statistics.
5. **Peer-reviewed academic work**, for methodological claims.

**Marketing microsites are never the sole evidence** for a legal, licence,
listing or product-structure claim — including Framont's own. Where a Framont
page is the only available source for a product fact, the fact is labelled as a
Framont example and the reader is pointed at the governing document.

Every source used is recorded in [`../data/aeo-sources.json`](../data/aeo-sources.json)
with its publisher, type, jurisdiction, `as_of` date and last-checked date.

## 3. Scope labelling

A statement that is true across the EU, true only in one member state, and true
only of one Framont product are three different kinds of claim, and conflating
them is the most common way an otherwise accurate article misleads. Each is
labelled visibly and in the markup:

| Label | `data-scope` | Meaning |
|---|---|---|
| General rule | `general` | Applies EU-wide, or to the instrument class generally |
| Jurisdiction (Malta, Italy, Liechtenstein, …) | `jurisdiction` | Depends on national law or a national regulator |
| Framont example | `framont` | A fact about a specific Framont or partner-issued product |

An answer engine that lifts a sentence out of context should still carry the
qualification with it. That is why the label is inline text, not a footnote.

## 4. Dates and time-sensitive figures

Any market size, share, yield, cost, threshold or other figure that can go stale
carries an explicit `as of` date next to it, and the underlying source record
carries the same date. The validator refuses to pass a claim marker containing a
magnitude, percentage or money amount unless it declares `data-as-of`.

Figures that cannot be attached to a dated, methodologically transparent source
are removed rather than softened. Where a figure is a practitioner estimate
rather than a measurement, it is labelled as one, dated, and its basis stated.

## 5. Update frequency

- **Full review of the article set:** every six months.
- **Triggered review:** within 20 working days of a change in the underlying law
  or regulator rules, or of any change to a referenced product's terms, listing
  or documentation.
- **Link check:** at every deployment, via `python3 scripts/validate_aeo_content.py --links`.

The visible `Last reviewed` date and the `dateModified` value in the structured
data must always match the date the content was actually approved. The validator
enforces the match. Neither is bumped for cosmetic edits.

## 6. Corrections

Factual corrections go to **access@framontmanagement.com**, monitored by the
editorial team.

> **Open item:** the monitored correction address must be confirmed by Framont
> before this policy page is published. Until it is confirmed, treat the address
> above as provisional.

When a correction is accepted:

1. the article is corrected in **both** languages in the same change;
2. the source registry is updated with the new evidence and check date;
3. the `Last reviewed` date and `dateModified` are advanced;
4. where the original statement was materially wrong — not merely imprecise — a
   dated correction note is added at the foot of the article and left in place.

Corrections are not made silently.

## 7. Conflicts of interest

Framont Access is operated by Framont & Partners Management, which acts as
portfolio manager to several of the instruments the articles use as examples,
and which earns fees from them. That is a real conflict and it is disclosed:

- product examples are always labelled `Framont example`;
- no article recommends a product, ranks Framont products against competitors,
  or asserts suitability for any reader;
- educational claims are sourced to law, regulators or independent research, not
  to Framont material;
- the reviewer is an officer of Framont & Partners Management, and his role and
  entity are stated in full next to his name so a reader can weigh the review
  accordingly.

## 8. What these articles are not

They are information, not investment advice, and not an offer or solicitation.
They do not replace a product's Key Information Document, prospectus, final
terms, offering memorandum or term sheet. Where an article and a governing
document disagree, the governing document controls.
