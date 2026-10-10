// Render the actual product page with all external requests blocked.
// Run with PLAYWRIGHT_MODULE_PATH when Playwright is outside node_modules.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const origin = 'http://localhost';
const route = '/it/eti/erere-quant-income/';
let browser;

before(async () => { browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' }); });
after(async () => { if (browser) await browser.close(); });

async function context(options = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'no-preference', ...options });
  await ctx.route('**/*', request => {
    const url = new URL(request.request().url());
    // This also blocks Analytics and enquiry delivery; no live requests leave.
    if (url.origin !== origin) return request.abort();
    let file = path.join(root, decodeURIComponent(url.pathname));
    if (url.pathname.endsWith('/')) file = path.join(file, 'index.html');
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      return request.fulfill({ status: 404, body: 'Not found' });
    }
    return request.fulfill({ status: 200, contentType: 'text/html', body: fs.readFileSync(file) });
  });
  return ctx;
}

async function assertReadable(page) {
  const blocks = await page.locator('.rv').evaluateAll(nodes => nodes.map(node => ({ opacity: getComputedStyle(node).opacity, text: node.textContent.trim().slice(0, 70) })));
  assert.ok(blocks.length > 20, 'inspect the existing page sections');
  assert.deepEqual(blocks.filter(block => block.opacity !== '1'), [], 'static content must remain visible');
  for (const selector of ['#summary', '#risks .warn', '#documents .g3', '#cta .form-card']) {
    assert.equal(await page.locator(selector).first().evaluate(node => getComputedStyle(node).opacity), '1', selector);
  }
}

test('Erere content remains readable without JavaScript on desktop and mobile', async () => {
  for (const width of [1440, 390]) {
    const ctx = await context({ javaScriptEnabled: false, viewport: { width, height: 1000 } });
    try {
      const page = await ctx.newPage();
      await page.goto(origin + route);
      await assertReadable(page);
    } finally { await ctx.close(); }
  }
});

for (const mode of ['missing', 'constructor throws', 'observe throws']) {
  test('Erere content remains readable when IntersectionObserver ' + mode, async () => {
    const ctx = await context();
    try {
      await ctx.addInitScript(mode => {
        if (mode === 'missing') delete window.IntersectionObserver;
        else if (mode === 'constructor throws') window.IntersectionObserver = class { constructor() { throw new Error('Observer unavailable'); } };
        else {
          const RealObserver = window.IntersectionObserver;
          window.IntersectionObserver = class extends RealObserver {
            observe(target) { super.observe(target); throw new Error('Observer setup failed'); }
          };
        }
      }, mode);
      const page = await ctx.newPage();
      const errors = []; page.on('pageerror', error => errors.push(error.message));
      await page.goto(origin + route);
      await assertReadable(page);
      assert.deepEqual(errors, [], 'observer failure must not abort the remaining page script');
    } finally { await ctx.close(); }
  });
}

test('Erere keeps its normal scroll reveal when the observer works', async () => {
  const ctx = await context();
  try {
    const page = await ctx.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + route);
    // The observer can arm after first paint under load: wait for the existing
    // opacity transition to settle before testing the subsequent scroll reveal.
    await page.waitForFunction(() => getComputedStyle(document.querySelector('#risks .sec-head')).opacity === '0');
    await page.locator('#risks .sec-head').scrollIntoViewIfNeeded();
    await page.waitForFunction(() => getComputedStyle(document.querySelector('#risks .sec-head')).opacity === '1');
    assert.deepEqual(errors, []);
  } finally { await ctx.close(); }
});

test('Erere reduced-motion preference keeps every content block visible', async () => {
  const ctx = await context({ reducedMotion: 'reduce' });
  try {
    const page = await ctx.newPage();
    await page.goto(origin + route);
    await assertReadable(page);
  } finally { await ctx.close(); }
});
