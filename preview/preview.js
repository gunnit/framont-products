/* ============================================================================
   Framont Access — preview documents
   Shared chrome: bilingual switching, document navigation, scroll reveal.
   Each page supplies its own copy dictionary and render function; this file
   owns everything the four documents have in common.
   ========================================================================= */

(function () {
  "use strict";

  var KEY = "framont_preview_lang";
  var PAGES = [
    { file: "index.html", en: "Overview", it: "Riepilogo" },
    { file: "comparison.html", en: "Comparison", it: "Confronto" },
    { file: "structure.html", en: "Structure", it: "Struttura" },
    { file: "glossary.html", en: "Glossary", it: "Glossario" }
  ];

  var CHROME = {
    en: { stamp: "Draft for approval", lang: "Italiano", skip: "Skip to content" },
    it: { stamp: "Bozza per approvazione", lang: "English", skip: "Vai al contenuto" }
  };

  var lang = "en";
  try {
    var saved = window.localStorage.getItem(KEY);
    if (saved === "en" || saved === "it") lang = saved;
  } catch (e) {}

  var renderers = [];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Values in the page dictionaries may be a plain string or an {en,it} pair.
  function L(v) {
    return (v && typeof v === "object" && !Array.isArray(v)) ? (v[lang] != null ? v[lang] : v.en) : v;
  }

  function currentFile() {
    var p = window.location.pathname;
    var f = p.substring(p.lastIndexOf("/") + 1);
    return f === "" ? "index.html" : f;
  }

  function buildChrome() {
    var host = document.querySelector("[data-chrome]");
    if (!host) return;
    var here = currentFile();
    host.className = "chrome";
    host.innerHTML =
      '<div class="chrome-in">' +
        '<a class="mark" href="index.html">Framont <span>Access</span></a>' +
        '<span class="stamp" data-chrome-stamp></span>' +
        "<nav aria-label=\"Draft documents\">" +
          PAGES.map(function (p) {
            var cur = p.file === here ? ' aria-current="page"' : "";
            return '<a href="' + p.file + '"' + cur + ' data-page="' + p.file + '"></a>';
          }).join("") +
        "</nav>" +
        '<button class="lang" data-chrome-lang aria-live="polite"></button>' +
      "</div>";
    host.querySelector("[data-chrome-lang]").addEventListener("click", function () {
      setLang(lang === "en" ? "it" : "en");
    });
  }

  function paintChrome() {
    var t = CHROME[lang];
    var stamp = document.querySelector("[data-chrome-stamp]");
    var btn = document.querySelector("[data-chrome-lang]");
    if (stamp) stamp.textContent = t.stamp;
    if (btn) btn.textContent = t.lang;
    PAGES.forEach(function (p) {
      var a = document.querySelector('[data-page="' + p.file + '"]');
      if (a) a.textContent = p[lang];
    });
  }

  // Static markup carries data-i18n keys; page dictionaries fill them in.
  function paintStatic(dict) {
    if (!dict) return;
    var t = dict[lang] || dict.en;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var k = el.getAttribute("data-i18n");
      if (t[k] != null) el.textContent = t[k];
    });
  }

  function setLang(next) {
    lang = next;
    try { window.localStorage.setItem(KEY, lang); } catch (e) {}
    document.documentElement.lang = lang;
    paintChrome();
    renderers.forEach(function (fn) { fn(lang); });
    observe();
  }

  var io = null, settleTimer = null;

  function settleAll() {
    document.querySelectorAll(".rise:not(.in)").forEach(function (el) { el.classList.add("in"); });
  }

  function observe() {
    if (!("IntersectionObserver" in window)) { settleAll(); return; }
    // Opting in here, not in the stylesheet, is what keeps the page readable
    // when this script never runs.
    document.documentElement.classList.add("reveal-ready");
    if (!io) {
      io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
        });
      }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    }
    document.querySelectorAll(".rise:not(.in)").forEach(function (el) { io.observe(el); });
    // Backstop: a throttled background tab can starve the observer callback, and
    // a section that never settles is a section the reviewer never reads.
    clearTimeout(settleTimer);
    settleTimer = setTimeout(settleAll, 1600);
  }

  window.PV = {
    get lang() { return lang; },
    esc: esc,
    L: L,
    /* dict: {en:{...},it:{...}} for data-i18n nodes. render: called on every
       language change with the active language. */
    init: function (opts) {
      var o = opts || {};
      buildChrome();
      if (o.render) renderers.push(function (l) { o.render(l); });
      if (o.dict) renderers.unshift(function () { paintStatic(o.dict); });
      document.documentElement.lang = lang;
      paintChrome();
      renderers.forEach(function (fn) { fn(lang); });
      // Synchronous, not in rAF: rAF is paused in background tabs, and the
      // reveal must never be the reason content stays hidden.
      observe();
    }
  };
})();
