// Runtime regressions: execute the shipped loader and component; replace only
// browser APIs and Web3Forms/GA network boundaries. No real requests are made.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const componentSource = html.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
const head = html.split('</head>')[0];
const production = 'https://access.framontmanagement.com';

function storage(initial = {}) {
  const entries = new Map(Object.entries(initial));
  return { getItem: key => entries.get(key) ?? null, setItem: (key, value) => entries.set(key, String(value)), removeItem: key => entries.delete(key) };
}

function browser({ url = production + '/', manual = true, storedLanguage, browserLanguage = 'en-GB' } = {}) {
  const location = new URL(url);
  location.replace = next => { location.href = new URL(next, location).href; };
  const scripts = [], dispatched = [], pending = [], listeners = new Map();
  const document = {
    title: 'Framont Access — Institutional Investment Platform',
    referrer: 'https://example.org/guide',
    documentElement: {}, body: { style: {} }, activeElement: null,
    head: { appendChild: script => scripts.push(script) },
    createElement: tag => ({ tagName: tag, setAttribute(key, value) { this[key] = value; } }),
    querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
    addEventListener() {}, removeEventListener() {},
  };
  const window = {
    location, document, innerWidth: 1200,
    localStorage: storage(storedLanguage ? { framont_lang: storedLanguage } : {}),
    sessionStorage: storage(),
    addEventListener: (name, callback) => listeners.set(name, callback), removeEventListener() {},
    dispatchEvent: event => dispatched.push(event), scrollTo() {},
    history: { pushState(_state, _title, next) { if (next) location.href = new URL(next, location).href; } },
  };
  class DCLogic {
    setState(patch, callback) { pending.push({ owner: this, patch, callback }); }
  }
  const context = vm.createContext({
    window, document, navigator: { language: browserLanguage }, DCLogic, URL, URLSearchParams,
    console, CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    IntersectionObserver: class { observe() {} unobserve() {} disconnect() {} },
    setTimeout: () => 1, clearTimeout() {},
    fetch: () => { throw new Error('Unexpected request: tests must provide a Web3Forms response'); },
  });
  // Execute actual analytics markup in the head. For static-page mode the same
  // loader receives no manual-pageviews attribute, as on Insights articles.
  for (const match of head.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
    if (/application\/ld\+json/.test(match[1])) continue;
    const src = match[1].match(/\bsrc="([^"]+)"/);
    if (src && src[1] === '/assets/analytics.js') {
      document.currentScript = { getAttribute: name => name === 'data-manual-pageviews' && manual && /data-manual-pageviews="true"/.test(match[1]) ? 'true' : null };
      vm.runInContext(fs.readFileSync(path.join(root, 'assets/analytics.js'), 'utf8'), context);
      document.currentScript = null;
    } else if (src && /googletagmanager/.test(src[1])) {
      scripts.push({ src: src[1] });
    } else if (!src && /gtag|dataLayer/.test(match[2])) {
      // A real browser aliases globals and window; accommodate the legacy
      // inline tag so these tests reproduce its duplicate-pageview bug.
      vm.runInContext(match[2].replace('dataLayer.push(arguments)', 'window.dataLayer.push(arguments)'), context);
      if (context.gtag) window.gtag = context.gtag;
    }
  }
  vm.runInContext(componentSource + '\nwindow.TestComponent = Component;', context);
  const component = new window.TestComponent();
  component.props = { startState: 'anonymous', language: 'en' };
  function flush() {
    let iterations = 0;
    while (pending.length) {
      assert.ok(++iterations < 100, 'component state updates must settle');
      const { owner, patch, callback } = pending.shift();
      Object.assign(owner.state, typeof patch === 'function' ? patch(owner.state) : patch);
      owner.componentDidUpdate(owner.props);
      if (callback) callback();
    }
  }
  function mount() { component.componentDidMount(); flush(); }
  const commands = () => Array.from(window.dataLayer || []).filter(entry => entry && typeof entry[0] === 'string').map(entry => Array.from(entry));
  const events = name => commands().filter(entry => entry[0] === 'event' && entry[1] === name).map(entry => JSON.parse(JSON.stringify(entry[2])));
  const buffered = name => Array.from(window.dataLayer || []).filter(entry => entry.event === name).map(entry => JSON.parse(JSON.stringify(entry)));
  return { window, document, context, scripts, dispatched, component, flush, mount, commands, events, buffered, listeners };
}

test('homepage config suppresses its automatic view; static pages retain one automatic config', () => {
  const home = browser();
  assert.equal(home.commands().filter(entry => entry[0] === 'config').length, 1);
  assert.equal(home.commands().find(entry => entry[0] === 'config')[2]?.send_page_view, false);
  home.component.initAnalytics();
  assert.equal(home.commands().filter(entry => entry[0] === 'config').length, 1);
  assert.equal(home.scripts.filter(script => /googletagmanager/.test(script.src)).length, 1);
  const article = browser({ manual: false, url: production + '/articles/what-is-an-eti.html' });
  assert.equal(article.commands().filter(entry => entry[0] === 'config').length, 1);
  assert.notEqual(article.commands().find(entry => entry[0] === 'config')[2]?.send_page_view, false);
  assert.equal(article.events('page_view').length, 0);
});

for (const origin of ['http://localhost:8000', 'http://127.0.0.1:8000', 'https://preview.example.com', 'https://access.framontmanagement.com.example.org', 'file://']) {
  test('does not load or dispatch analytics outside production: ' + origin, () => {
    const page = browser({ url: origin + '/' });
    let escapedEvents = 0;
    page.window.gtag = page.window.plausible = () => { escapedEvents++; };
    page.component.ANALYTICS.plausibleDomain = 'access.framontmanagement.com';
    page.mount();
    page.component.trackEvent('registration_start', { language: 'en' });
    assert.equal(page.scripts.filter(script => /googletagmanager|plausible/.test(script.src)).length, 0);
    assert.equal(escapedEvents, 0);
    assert.equal(page.dispatched.length, 0);
    assert.equal(page.buffered('registration_start').length, 1);
  });
}

for (const fixture of [
  { url: production + '/#/it/eti', view: 'eti', lang: 'it', location: production + '/#/it/eti', title: 'ETI — Framont Access' },
  { url: production + '/', storedLanguage: 'it', view: 'home', lang: 'it', location: production + '/', title: 'Framont Access — Piattaforma di Investimento Istituzionale' },
  { url: production + '/#/it/fondi', view: 'funds', lang: 'it', location: production + '/#/it/fondi', title: 'Fondi — Framont Access' },
]) {
  test('initial view waits for resolved language and route: ' + fixture.url + (fixture.storedLanguage || ''), () => {
    const page = browser(fixture);
    page.mount();
    const views = page.events('page_view');
    assert.equal(views.length, 1);
    assert.equal(views[0].view, fixture.view);
    assert.equal(views[0].language, fixture.lang);
    assert.equal(views[0].page_location, fixture.location);
    assert.equal(views[0].page_title, fixture.title);
    assert.equal(views[0].page_referrer, 'https://example.org/guide');
    assert.equal(page.events('language_switch').length, 0);
  });
}

test('each real view/language change has current URL/title and previous referrer; modals add no view', () => {
  const page = browser();
  page.mount();
  page.component.navTo('eti'); page.flush();
  page.component.openModal('register'); page.flush();
  page.component.setState({ modal: null }); page.flush();
  page.component.toggleLang(); page.flush();
  page.component.navTo('eti'); page.flush();
  const views = page.events('page_view');
  assert.equal(views.length, 3);
  assert.equal(views[1].page_location, production + '/#/en/eti');
  assert.equal(views[1].page_title, 'ETI — Framont Access');
  assert.equal(views[1].page_referrer, production + '/');
  assert.equal(views[2].page_location, production + '/#/it/eti');
  assert.equal(views[2].page_referrer, production + '/#/en/eti');
  assert.equal(page.events('language_switch').length, 1);
});

test('a redirect to static Insights does not record a temporary homepage view', () => {
  const page = browser({ url: production + '/#/it/insights' });
  page.mount();
  assert.equal(page.window.location.pathname, '/articles/it/');
  assert.equal(page.events('page_view').length, 0);
});

test('browser hash navigation records the resolved category once', () => {
  const page = browser(); page.mount();
  page.window.location.hash = '#/it/amc';
  page.listeners.get('hashchange')(); page.flush();
  const views = page.events('page_view');
  assert.equal(views.length, 2);
  assert.equal(views[1].view, 'amc');
  assert.equal(views[1].language, 'it');
  assert.equal(views[1].page_location, production + '/#/it/amc');
  assert.equal(views[1].page_referrer, production + '/');
});

const failures = [
  ['non-2xx', () => Promise.resolve({ ok: false, status: 400, json: async () => ({ success: true }) })],
  ['API rejection', () => Promise.resolve({ ok: true, status: 200, json: async () => ({ success: false, message: 'Rejected' }) })],
  ['string success', () => Promise.resolve({ ok: true, status: 200, json: async () => ({ success: 'true' }) })],
  ['missing success', () => Promise.resolve({ ok: true, status: 200, json: async () => ({ message: 'OK' }) })],
  ['invalid JSON', () => Promise.resolve({ ok: true, status: 200, json: async () => { throw new SyntaxError('Invalid JSON'); } })],
  ['network failure', () => Promise.reject(new Error('Offline'))],
  ['synchronous failure', () => { throw new Error('Offline'); }],
];
for (const [label, fetch] of failures) {
  test('no confirmed lead on ' + label, async () => {
    const page = browser(); page.mount(); page.context.fetch = fetch;
    assert.equal(await page.component.submitLead('access_request'), false);
    assert.equal(page.events('generate_lead').length, 0);
    assert.equal(page.buffered('generate_lead').length, 0);
  });
}

test('confirmed lead waits for API acceptance and keeps captured, allowlisted non-PII context', async () => {
  const page = browser({ url: production + '/?email=private@example.com' }); page.mount();
  page.component.state.lang = 'it';
  page.component.state.regCtx = { ck: 'eti', productId: 'eti-heraklit', productName: 'Should not enter analytics' };
  Object.assign(page.component.state.form, { name: 'Private Person', email: 'private@example.com', phone: '123456789', callNote: 'Private message' });
  let accept, request;
  page.context.fetch = (url, options) => {
    request = { url, body: JSON.parse(options.body) };
    return new Promise(resolve => { accept = resolve; });
  };
  const result = page.component.submitLead('call_request', { message: 'Private message', product_id: 'eti-heraklit' });
  assert.equal(page.events('generate_lead').length, 0);
  assert.equal(request.body.email, 'private@example.com');
  page.component.state.lang = 'en'; page.component.state.regCtx = null; page.component.state.view = 'deals';
  accept({ ok: true, status: 200, json: async () => ({ success: true, message: 'Email sent successfully!' }) });
  assert.equal(await result, true);
  assert.deepEqual(page.events('generate_lead'), [{ lead_type: 'call_request', language: 'it', category: 'eti', product_id: 'eti-heraklit' }]);
  assert.deepEqual(page.buffered('generate_lead'), [{ event: 'generate_lead', lead_type: 'call_request', language: 'it', category: 'eti', product_id: 'eti-heraklit' }]);
});

test('unknown category/product text is never copied into confirmed lead analytics', async () => {
  const page = browser(); page.mount();
  page.component.state.regCtx = { ck: 'private@example.com', productId: 'private@example.com' };
  page.context.fetch = async () => ({ ok: true, status: 200, json: async () => ({ success: true }) });
  assert.equal(await page.component.submitLead('access_request', { product_id: 'private@example.com' }), true);
  assert.deepEqual(page.events('generate_lead'), [{ lead_type: 'access_request', language: 'en' }]);
});

for (const fixture of [
  { category: 'funds', product: 'fund-gentile', unlockedDeals: false },
  { category: 'deals', product: 'deal-castello-monticello', unlockedDeals: true },
]) {
  test('actual anonymous enquiry retains its explicit product: ' + fixture.product, async () => {
    const page = browser(); page.mount();
    const component = page.component;
    const requests = [];
    page.context.fetch = async (_url, options) => {
      requests.push(JSON.parse(options.body));
      return { ok: true, status: 200, json: async () => ({ success: true }) };
    };
    component.navTo(fixture.category); page.flush();
    component.state.dealsUnlocked = fixture.unlockedDeals;
    const product = component.DATA[fixture.category].products.find(item => item.id === fixture.product);
    component.viewProduct(product, fixture.category); page.flush();
    component.startSub(); page.flush();
    assert.equal(component.state.modal, 'call');
    Object.assign(component.state.form, { name: 'Test Person', email: 'person@example.com', phone: '123456789', gdpr: true });
    component.callSubmit(); page.flush();
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(page.events('generate_lead'), [{ lead_type: 'call_request', language: 'en', category: fixture.category, product_id: fixture.product }]);
    assert.equal(requests.length, 1);
    // Existing delivery fields and gate behavior are unaffected by analytics context.
    assert.equal(requests[0].interest, fixture.category);
    assert.equal(requests[0].email, 'person@example.com');
    assert.equal(requests[0].product_id, undefined);
    assert.equal(component.state.user, null);
  });
}

test('generic registration after closing a product enquiry cannot reuse its stale active product', async () => {
  const page = browser(); page.mount();
  const component = page.component;
  page.context.fetch = async () => ({ ok: true, status: 200, json: async () => ({ success: true }) });
  component.navTo('funds'); page.flush();
  component.viewProduct(component.DATA.funds.products.find(item => item.id === 'fund-gentile'), 'funds'); page.flush();
  component.startSub(); page.flush();
  component.closeModal(); page.flush();
  component.navTo('eti'); page.flush();
  component.openModal('register'); page.flush();
  Object.assign(component.state.form, { name: 'Test Person', email: 'person@example.com', phone: '123456789', gdpr: true });
  component.regSubmit(); page.flush();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(page.events('generate_lead'), [{ lead_type: 'access_request', language: 'en', category: 'eti' }]);
  assert.equal(component.state.user.email, 'person@example.com');
});
