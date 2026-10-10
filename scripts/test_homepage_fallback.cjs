// Real-browser fallback regression checks. Install Playwright or set
// PLAYWRIGHT_MODULE_PATH to its module path, then run with node --test.
// Analytics and lead-delivery endpoints are blocked in every browser context.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const origin = 'http://localhost';
let browser;

before(async () => {
  browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' });
});
after(async () => { if (browser) await browser.close(); });

async function context(options = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...options });
  await context.route(/google-analytics\.com|googletagmanager\.com|api\.web3forms\.com/, route => route.abort());
  // Serve the real repository files without opening a listening socket.
  await context.route(origin + '/**', route => {
    const url = new URL(route.request().url());
    let file = path.join(root, decodeURIComponent(url.pathname));
    if (url.pathname.endsWith('/')) file = path.join(file, 'index.html');
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      return route.fulfill({ status: 404, body: 'Not found' });
    }
    const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.mp4': 'video/mp4', '.webm': 'video/webm' };
    return route.fulfill({ status: 200, contentType: types[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  return context;
}

async function assertPublicFallback(page) {
  assert.equal(await page.locator('#homepage-fallback').isVisible(), true, 'public content must remain visible before an actual app mount');
  assert.equal(await page.locator('#homepage-fallback h1').textContent(), 'Framont Access — Institutional Investment Platform');
  assert.equal(await page.locator('#homepage-fallback a[href="/articles/what-is-an-eti.html"]').isVisible(), true);
  assert.equal(await page.locator('x-dc').isVisible(), false, 'uncompiled template must remain hidden');
  const size = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }));
  assert.ok(size.width <= size.viewport + 1, 'fallback must not overflow horizontally');
}

test('category overview links preserve the active section highlight on desktop and mobile', async () => {
  for (const width of [1440, 390]) {
    const ctx = await context({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
    try {
      const page = await ctx.newPage();
      await page.goto(origin + '/#/en/amc', { waitUntil: 'domcontentloaded' });
      await page.locator('#dc-root #main h1').waitFor({ state: 'visible', timeout: 40000 });
      for (const [section, label] of [['sec-products', 'Products'], ['sec-about', 'About']]) {
        await page.evaluate(id => window.scrollTo({ top: document.getElementById(id).getBoundingClientRect().top + scrollY - 140, behavior: 'instant' }), section);
        await page.waitForFunction(expected => {
          const links = [...document.querySelectorAll('[data-screen-label="Category — Subnav"] a')];
          const active = links.filter(link => link.style.borderBottomColor === 'rgb(255, 130, 0)');
          return active.length === 1 && active[0].textContent.trim() === expected;
        }, label, { timeout: 5000 });
      }
      assert.equal(await page.locator('[data-screen-label="Category — Subnav"] a[href="/amc/"]').count(), 1);
    } finally { await ctx.close(); }
  }
});

test('no JavaScript exposes the existing public content once and hides the raw template', async () => {
  const ctx = await context({ javaScriptEnabled: false });
  try {
    const page = await ctx.newPage();
    await page.goto(origin, { waitUntil: 'domcontentloaded' });
    await assertPublicFallback(page);
    assert.equal(await page.locator('h1:visible').count(), 1);
  } finally { await ctx.close(); }
});

for (const [name, blocked] of [
  ['React CDN failure', /unpkg\.com/],
  ['runtime script failure', /\/support\.js$/],
]) {
  test(name + ' keeps usable public links with JavaScript enabled', async () => {
    const ctx = await context({ viewport: { width: 390, height: 844 } });
    try {
      await ctx.route(blocked, route => route.abort());
      const page = await ctx.newPage();
      await page.goto(origin, { waitUntil: 'domcontentloaded' });
      await assertPublicFallback(page);
      assert.ok(await page.locator('#homepage-fallback a:visible').count() > 10);
    } finally { await ctx.close(); }
  });
}

test('fallback survives delayed mounting, hides on real content, and returns after root/content loss', async () => {
  const ctx = await context();
  let release;
  const dependencyGate = new Promise(resolve => { release = resolve; });
  try {
    await ctx.route(/unpkg\.com/, async route => { await dependencyGate; await route.continue(); });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin, { waitUntil: 'domcontentloaded' });
    await assertPublicFallback(page);
    release();
    await page.locator('#dc-root #main h1').waitFor({ state: 'visible', timeout: 40000 });
    await page.locator('#homepage-fallback').waitFor({ state: 'hidden' });
    assert.equal(await page.locator('#homepage-fallback').getAttribute('hidden'), '');
    assert.equal(await page.locator('h1:visible').count(), 1);
    assert.deepEqual(errors, []);

    // A runtime error can leave the root in place with no rendered content.
    await page.evaluate(() => {
      window.testAppRoot = document.getElementById('dc-root');
      window.testAppContent = [...window.testAppRoot.childNodes];
      window.testAppRoot.replaceChildren();
    });
    await page.locator('#homepage-fallback').waitFor({ state: 'visible' });
    await assertPublicFallback(page);
    await page.evaluate(() => window.testAppRoot.append(...window.testAppContent));
    await page.locator('#homepage-fallback').waitFor({ state: 'hidden' });

    await page.evaluate(() => window.testAppRoot.remove());
    await page.locator('#homepage-fallback').waitFor({ state: 'visible' });
    await assertPublicFallback(page);
  } finally { release(); await ctx.close(); }
});
