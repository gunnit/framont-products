// Real-browser locale regressions. No network requests leave the test contexts.
// Run with PLAYWRIGHT_MODULE_PATH when Playwright is outside node_modules.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const origin = 'https://access.framontmanagement.com';
const products = [
  { route: '/amc/noctiluca-capital/', heading: 'Noctiluca Capital Systematic Futures Programme', id: 'amc-noctiluca', isin: 'CH1554882477', gated: true },
  { route: '/amc/zalphyx-yield-strategies/', heading: 'Zalphyx Yield Strategies 6% p.a. credit-linked note', id: 'amc-zalphyx', isin: 'CH1518693374', gated: true },
  { route: '/eti/value-edge-snowwhite/', heading: 'Value Edge SnowWhite Strategy', id: 'eti-lcinvest', isin: 'DE000AMC0BZ5', gated: false },
];
let browser;
before(async () => { browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' }); });
after(async () => { if (browser) await browser.close(); });

async function context(options = {}) {
  const ctx = await browser.newContext({ reducedMotion: 'reduce', ...options });
  await ctx.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin) return route.abort();
    let file = path.join(root, decodeURIComponent(url.pathname));
    if (url.pathname.endsWith('/')) file = path.join(file, 'index.html');
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'Not found' });
    const types = { '.html': 'text/html', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.pdf': 'application/pdf' };
    return route.fulfill({ status: 200, contentType: types[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  return ctx;
}

for (const product of products) {
  test(product.route + ' serves authored English content and metadata without JavaScript', async () => {
    const ctx = await context({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    try {
      const page = await ctx.newPage();
      await page.goto(origin + '/it' + product.route);
      const authored = await page.locator('body .t-en').allTextContents();
      assert.ok(authored.length > 300);
      const response = await page.goto(origin + product.route);
      assert.equal(response.status(), 200);
      assert.equal(await page.locator('html').getAttribute('lang'), 'en');
      const source = fs.readFileSync(path.join(root, 'it', product.route, 'index.html'), 'utf8');
      const title = source.match(/var TITLE = \{[\s\S]*?\ben:'([^']+)'/)[1];
      const description = source.match(/var DESC = \{[\s\S]*?\ben:'([^']+)'/)[1];
      assert.equal(await page.title(), title);
      assert.equal(await page.locator('meta[name="description"]').getAttribute('content'), description);
      assert.equal(await page.locator('body .t-it, body .t-en').count(), 0);
      assert.equal(await page.locator('h1').textContent(), product.heading);
      const body = await page.locator('body').textContent();
      for (const text of authored) assert.ok(body.includes(text), 'preserve authored English: ' + text.slice(0, 80));
      if (product.id === 'amc-noctiluca') {
        assert.ok(body.includes('USD 275,000 - 366,000'));
        assert.ok(body.includes('USD 100,000'));
        assert.ok(body.includes('USD 1,000,000'));
        assert.equal(await page.locator('.k b').filter({ hasText: /^2\.89$/ }).count(), 1);
      } else if (product.id === 'amc-zalphyx') {
        assert.ok(body.includes('USD 1,000'));
        assert.equal(await page.locator('td').filter({ hasText: /^USD 1\.000$/ }).count(), 0);
        assert.deepEqual(await page.locator('.cd b').allTextContents(), ['24 Sep 2026', '24 Mar 2027', '24 Sep 2027', '24 Mar 2028', '24 Sep 2028', '24 Mar 2029', '24 Sep 2029']);
      } else {
        assert.equal(await page.locator('.spec-n .pre').textContent(), 'up to');
      }
      assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), origin + product.route);
      assert.equal(await page.locator('link[hreflang="en"]').getAttribute('href'), origin + product.route);
      assert.equal(await page.locator('link[hreflang="it"]').getAttribute('href'), origin + '/it' + product.route);
      assert.equal(await page.locator('link[hreflang="x-default"]').getAttribute('href'), origin + product.route);
      assert.equal(await page.locator('#lead [name="language"]').inputValue(), 'en');
      assert.equal(await page.locator('#lead [name="page"]').inputValue(), origin + product.route);
      assert.equal(await page.locator('#lead [name="redirect"]').inputValue(), origin + product.route + '?sent=1#contact');
      assert.equal(await page.locator('#lead [name="product_id"]').inputValue(), product.id);
      assert.equal(await page.locator('#lead [name="isin"]').inputValue(), product.isin);
      const graph = JSON.parse(await page.locator('script[type="application/ld+json"]').textContent())['@graph'];
      assert.equal(graph.find(node => node['@type'] === 'WebPage').inLanguage, 'en');
      if (!product.gated) {
        assert.equal(graph.find(node => node['@type'] === 'FinancialProduct').name, product.heading);
        assert.equal(graph.find(node => node['@type'] === 'BreadcrumbList').itemListElement.at(-1).name, product.heading);
        assert.equal(await page.locator('meta[property="og:image:alt"]').getAttribute('content'), product.heading + ', FRAMONT & Partners Management Ltd');
      }
      const faqs = graph.find(node => node['@type'] === 'FAQPage').mainEntity;
      const visibleFaqs = await page.locator('#faq details').evaluateAll(nodes => nodes.map(node => ({ question: node.querySelector('summary').textContent, answer: node.querySelector('.ans').textContent })));
      assert.equal(faqs.length, visibleFaqs.length);
      for (let i = 0; i < faqs.length; i++) {
        assert.equal(faqs[i].name, visibleFaqs[i].question.trim());
        assert.equal(faqs[i].acceptedAnswer.text, visibleFaqs[i].answer.trim());
      }
      if (product.gated) {
        assert.equal(await page.locator('#gate').isVisible(), true);
        await page.locator('label[for="pro-ack"]').click();
        assert.equal(await page.locator('#gate').isVisible(), false);
      }
      assert.equal(await page.locator('a[data-language="it"]').getAttribute('href'), '/it' + product.route);
      const size = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }));
      assert.ok(size.width <= size.viewport + 1, 'no mobile overflow');
      if (!product.gated) {
        assert.equal(await page.locator('.dev-photo img').evaluate(img => img.complete && img.naturalWidth > 0), true);
      }
    } finally { await ctx.close(); }
  });

  test(product.route + ' uses actual locale links and keeps attribution and section anchors', async () => {
    const ctx = await context();
    try {
      const page = await ctx.newPage();
      const errors = []; page.on('pageerror', error => errors.push(error.message));
      await page.goto(origin + product.route + '?utm_source=locale-test#contact');
      assert.equal(new URL(page.url()).searchParams.has('lang'), false);
      assert.equal(await page.locator('html').getAttribute('lang'), 'en');
      const toItalian = new URL(await page.locator('a[data-language="it"]').getAttribute('href'), origin);
      assert.equal(toItalian.pathname, '/it' + product.route);
      assert.equal(toItalian.search, '?utm_source=locale-test');
      assert.equal(toItalian.hash, '#contact');
      if (product.gated) await page.locator('label[for="pro-ack"]').click();
      await page.locator('a[data-language="it"]').click();
      await page.waitForURL(origin + '/it' + product.route + '?utm_source=locale-test#contact');
      assert.equal(await page.locator('html').getAttribute('lang'), 'it');
      assert.equal(await page.locator('link[hreflang="en"]').getAttribute('href'), origin + product.route);
      if (product.gated) assert.equal(await page.locator('#gate').isVisible(), false);
      await page.locator('a[href="#risks"]:visible').first().click();
      await page.waitForURL(origin + '/it' + product.route + '?utm_source=locale-test#risks');
      await page.waitForFunction(() => document.querySelector('a[data-language="en"]').hash === '#risks');
      assert.equal(await page.locator('a[data-language="en"]').getAttribute('href'), product.route + '?utm_source=locale-test#risks');
      assert.deepEqual(errors, []);
    } finally { await ctx.close(); }
  });

  test(product.route + ' supports legacy English query/hash links without losing attribution', async () => {
    const ctx = await context();
    try {
      const page = await ctx.newPage();
      await page.goto(origin + '/it' + product.route + '?lang=en&utm_medium=guide#contact');
      await page.waitForURL(origin + product.route + '?utm_medium=guide#contact');
      assert.equal(await page.locator('html').getAttribute('lang'), 'en');
      await page.goto(origin + '/it' + product.route + '?utm_medium=guide#en');
      await page.waitForURL(origin + product.route + '?utm_medium=guide');
      assert.equal(await page.locator('#lead [name="language"]').inputValue(), 'en');
    } finally { await ctx.close(); }
  });
}
