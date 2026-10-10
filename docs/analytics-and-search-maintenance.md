# Analytics and search maintenance

## Analytics

The homepage and Insights pages share `/assets/analytics.js`. It loads GA4 only
on `access.framontmanagement.com`; local copies keep a diagnostic dataLayer but
do not send analytics. Keep the existing measurement ID and do not add a second
Google tag to those pages.

The homepage uses `data-manual-pageviews="true"` and sends one page view after
its language and route have settled, then one for each view/language change.
Static Insights pages use the automatic initial page view. The web stream's
**Page changes based on browser history events** option must be disabled to
avoid double-counting SPA navigation and modal history entries. Other enhanced
measurement settings can remain enabled.

`generate_lead` denotes acceptance by the form provider: HTTP success and a JSON
body with `success: true`. It does not establish inbox delivery, investor
eligibility or a qualified opportunity. Mark this event as a GA4 key event,
counted once per event. Its explicit parameters contain only known lead type,
language, category and product ID. Never add names, emails, phone numbers or
free-text messages to analytics parameters.

Legacy events such as `registration_complete`, `access_request` and
`call_request_submit` describe client-side actions and may precede delivery.
Their historical counts must not be reinterpreted as confirmed leads, or added
together as distinct people. The new key event does not backfill old data.

New category overviews and product/utility pages without analytics remain
outside collection. Any
future expansion must first reconcile their stated cookie behavior with the
intended consent implementation.

## Search metadata

Funds, AMC, ETI and Deals have static English/Italian overview pages linked from
the homepage fallback, catalogue footer and relevant Insights articles. Keep
their real anchor links and reciprocal hreflang annotations alongside the
interactive catalogue's existing hash navigation.

Noctiluca Capital, Zalphyx Yield Strategies and Value Edge SnowWhite have their
own English URLs without the `/it` prefix. Each URL serves a fixed locale and
has a self canonical plus reciprocal English/Italian alternates. Language
controls are real links; JavaScript preserves attribution parameters and
section anchors, and redirects legacy Italian `?lang=en` and `#en` links.
ERERE remains Italian-only and must not declare an English alternate.

English product pages are generated from the English text already authored in
the corresponding Italian sources. Edit those source files, then regenerate:

```sh
python3 scripts/generate_product_locales.py
python3 scripts/generate_product_locales.py --check
```

Do not edit generated English files directly. The generator preserves product
identifiers, legal/risk text, professional-access gates and form routing. This
publication does not constitute a new financial review of the source content.
Category excerpts retain their original evidence markers and source dates.

Only update sitemap `lastmod` when the corresponding page changes meaningfully.
An analytics-only edit does not justify refreshing all sitemap dates.
Successful sitemap submission or a public HTTP 200 does not prove indexing.
Use Search Console URL Inspection to check Google's subsequent stored state.

## Verification

```sh
node --test scripts/test_analytics.cjs
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/validate_aeo_content.py
python3 scripts/generate_product_locales.py --check
# Requires Playwright and Chrome; PLAYWRIGHT_MODULE_PATH may point to an existing installation.
node --test scripts/test_homepage_fallback.cjs scripts/test_product_leads.cjs scripts/test_product_locales.cjs
```

Browser checks should block Analytics collection and form endpoints, and cover
initial category links, section highlights, language changes, modal open/close,
desktop and mobile. Product-form checks cover provider rejection and malformed
responses as well as a confirmed success; HTTP 200 alone is not acceptance.
Do not submit real enquiries solely to test tracking.
