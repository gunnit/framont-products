// Browser regressions for standalone product forms. All requests are intercepted;
// Web3Forms responses are simulated and no enquiries or analytics are sent.
// Run with PLAYWRIGHT_MODULE_PATH (if needed) and node --test.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const origin = 'http://localhost';
const endpoint = 'https://api.web3forms.com/submit';
let browser;

before(async () => {
  browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' });
});
after(async () => { if (browser) await browser.close(); });

const cases = [
  { name: 'accepted JSON', status: 200, body: '{"success":true}', accepted: true },
  { name: 'JSON rejection', status: 200, body: '{"success":false}' },
  { name: 'malformed JSON', status: 200, body: '{broken' },
  { name: 'empty response', status: 200, body: '' },
  { name: 'missing success', status: 200, body: '{}' },
  { name: 'non-boolean success', status: 200, body: '{"success":"true"}' },
  { name: 'HTTP rejection', status: 400, body: '{"success":true}' },
  { name: 'network failure', abort: true },
];
const products = [
  { route: '/amc/noctiluca-capital/', id: 'amc-noctiluca', isin: 'CH1554882477' },
  { route: '/amc/zalphyx-yield-strategies/', id: 'amc-zalphyx', isin: 'CH1518693374' },
  { route: '/eti/value-edge-snowwhite/', id: 'eti-lcinvest', isin: 'DE000AMC0BZ5' },
].flatMap(product => [
  { ...product, language: 'en' },
  { ...product, route: '/it' + product.route, language: 'it' },
]);

for (const product of products) {
  for (const response of cases) {
    test(product.route + ' — ' + response.name, async () => {
      const ctx = await browser.newContext({ reducedMotion: 'reduce' });
      const requests = [];
      await ctx.addInitScript(() => localStorage.setItem('framont-pro-ack', '1'));
      await ctx.route('**/*', async route => {
        const request = route.request();
        const url = new URL(request.url());
        if (url.href === endpoint) {
          // A CORS preflight carries no enquiry payload.
          if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: {
            'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'content-type',
          } });
          requests.push(request.postDataJSON());
          if (response.abort) return route.abort('failed');
          return route.fulfill({ status: response.status, contentType: 'application/json',
            headers: { 'Access-Control-Allow-Origin': origin }, body: response.body });
        }
        if (url.origin !== origin) return route.abort();
        let file = path.join(root, decodeURIComponent(url.pathname));
        if (url.pathname.endsWith('/')) file = path.join(file, 'index.html');
        if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
          return route.fulfill({ status: 404, body: 'Not found' });
        }
        const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.png': 'image/png' };
        return route.fulfill({ status: 200, contentType: types[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
      });
      try {
        const page = await ctx.newPage();
        await page.goto(origin + product.route, { waitUntil: 'domcontentloaded' });
        assert.equal(await page.locator('#lead-ok').isVisible(), false);
        await page.locator('#lead').evaluate(form => {
          form.querySelector('[name="name"]').value = 'Test Person';
          form.querySelector('[name="email"]').value = 'test@example.com';
          const category = form.querySelector('[name="investor_category"]');
          category.value = [...category.options].find(option => option.value).value;
          form.querySelector('[name="gdpr_consent"]').checked = true;
          form.requestSubmit();
        });
        await page.waitForFunction(() => {
          const form = document.getElementById('lead');
          return !form.querySelector('button[type="submit"]').disabled
            && (document.getElementById('lead-ok').classList.contains('on')
              || document.getElementById('lead-err').classList.contains('on'));
        });
        assert.equal(requests.length, 1, 'exactly one mocked enquiry');
        assert.equal(requests[0].email, 'test@example.com');
        assert.equal(requests[0].gdpr_consent, 'yes');
        assert.equal(requests[0].redirect, undefined);
        assert.equal(requests[0].language, product.language);
        assert.equal(requests[0].product_id, product.id);
        assert.equal(requests[0].isin, product.isin);
        assert.equal(requests[0].page, origin + product.route);
        const accepted = !!response.accepted;
        assert.equal(await page.locator('#lead-ok').isVisible(), accepted, 'success UI requires provider acceptance');
        assert.equal(await page.locator('#lead-err').isVisible(), !accepted, 'failed or unreadable responses show the retry message');
        assert.equal(await page.locator('#f-email').isVisible(), !accepted, 'failed attempts preserve editable fields');
        assert.equal(await page.locator('#f-email').inputValue(), 'test@example.com');
        assert.equal(await page.locator('#lead button[type="submit"]').isEnabled(), true, 'pending state always clears');
      } finally { await ctx.close(); }
    });
  }
}
