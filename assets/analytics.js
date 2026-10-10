// Shared only by pages that already collect analytics. Local copies and preview
// hosts retain dataLayer for debugging without loading an analytics provider.
(function (window, document) {
  "use strict";
  window.dataLayer = window.dataLayer || [];
  if (window.framontAnalytics) return;

  var enabled = window.location.hostname === "access.framontmanagement.com";
  var configured = Object.create(null);
  function loadGa4(id, manualPageviews) {
    if (!enabled || !id || configured[id]) return;
    configured[id] = true;
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", id, { send_page_view: !manualPageviews });
    var script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
    document.head.appendChild(script);
  }

  window.framontAnalytics = { enabled: enabled, loadGa4: loadGa4 };
  var manual = document.currentScript && document.currentScript.getAttribute("data-manual-pageviews") === "true";
  loadGa4("G-YRE5XX3RN2", manual);
})(window, document);
