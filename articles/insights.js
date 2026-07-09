/* Framont Access — Insights scroll-reveal motion.
   Mirrors the entrance choreography of the main site's category pages: a gentle
   rise + fade as blocks enter the viewport, with a light stagger across grids.
   Progressive enhancement — see insights.css. The `html.motion` gate is set
   synchronously by the inline snippet in each page's <head>, so hidden elements
   never flash; this file only reveals them as they scroll into view. */
(function () {
  "use strict";
  window.__insightsMotion = true;

  var root = document.documentElement;
  if (!("IntersectionObserver" in window) ||
      (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches)) {
    root.classList.remove("motion"); // ensure nothing stays hidden
    return;
  }
  root.classList.add("motion");

  // Elements the CSS hides — must stay in sync with the selector list in insights.css.
  var HIDDEN = [
    ".hero-in",
    ".article > *",
    ".products-in > .p-label",
    ".products-in > h2",
    ".p-grid > .p-card",
    ".nextread > *",
    ".hub-card"
  ].join(",");

  function start() {
    var targets = Array.prototype.slice.call(document.querySelectorAll(HIDDEN));
    if (!targets.length) return;

    // Light stagger for cards that share a grid row.
    function stagger(sel) {
      document.querySelectorAll(sel).forEach(function (el, i) {
        el.style.transitionDelay = (Math.min(i, 6) * 0.07) + "s";
      });
    }
    stagger(".p-grid > .p-card");
    stagger(".hub-card");

    function reveal(el) { el.classList.add("mo-in"); }
    function revealAll() { targets.forEach(reveal); }
    // Reveal whatever currently sits within the viewport (covers above-the-fold
    // content on load and when a hidden tab is later focused).
    function sweep() {
      var vh = window.innerHeight || root.clientHeight || 0;
      targets.forEach(function (el) {
        if (el.classList.contains("mo-in")) return;
        if (el.getBoundingClientRect().top < vh) reveal(el);
      });
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { reveal(en.target); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
    targets.forEach(function (el) { io.observe(el); });

    // Backstop: if the environment can't drive IntersectionObserver — a hidden or
    // zero-size viewport (background tab, some headless renderers) — reveal
    // everything so content is never left invisible. Otherwise just make sure the
    // above-the-fold blocks show even if the first IO callback was throttled.
    function backstop() {
      if (document.visibilityState === "hidden" || !(window.innerHeight > 0)) revealAll();
      else sweep();
    }
    if (document.readyState === "complete") setTimeout(backstop, 400);
    else window.addEventListener("load", function () { setTimeout(backstop, 400); });

    // A tab that starts hidden and is later focused: reveal in-view content.
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") sweep();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
