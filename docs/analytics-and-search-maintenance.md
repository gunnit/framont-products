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

Product and utility pages without analytics remain outside collection. Any
future expansion must first reconcile their stated cookie behavior with the
intended consent implementation.

## Search metadata

Product `?lang=en` switches are presentation variants with an Italian canonical,
not independently published English pages. Do not declare them as English
hreflang alternates. A future English publication needs its own rendered page,
English canonical, reviewed equivalent content and reciprocal annotations.
Real English/Italian article and utility pairs retain their existing hreflang.

Only update sitemap `lastmod` when the corresponding page changes meaningfully.
An analytics-only edit does not justify refreshing all sitemap dates.
Successful sitemap submission or a public HTTP 200 does not prove indexing.
Use Search Console URL Inspection to check Google's subsequent stored state.

## Verification

```sh
node --test scripts/test_analytics.cjs
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/validate_aeo_content.py
```

Browser checks should block Analytics collection and form endpoints, and cover
initial category links, language changes, modal open/close, desktop and mobile.
Do not submit real enquiries solely to test tracking.
