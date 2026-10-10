// Keep the existing public content available until the interactive catalogue
// actually renders, including when its external runtime cannot load.
(function () {
  "use strict";
  var fallback = document.getElementById("homepage-fallback");
  if (!fallback) return;
  var scheduled = false;

  function update() {
    scheduled = false;
    var main = document.querySelector("#dc-root #main");
    var heading = main && main.querySelector("h1, h2");
    fallback.hidden = !!(heading && heading.textContent.trim());
  }

  // Coalesce content changes into one pending check. Style/animation mutations
  // are deliberately excluded; there is no polling or dependency timeout.
  var observer = new MutationObserver(function () {
    if (scheduled) return;
    scheduled = true;
    window.setTimeout(update, 0);
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  update();
})();
