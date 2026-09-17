/*
 * ien-ui.js - comportamiento compartido de la interfaz nueva (nueva_ui).
 * Extraido de index-ui.html del rediseno, sin el router por hash ni los
 * formularios simulados: en Django la navegacion la resuelven las urls.
 */
(function () {
  "use strict";

  var ICONS = {
    "search": '<circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>',
    "arrow-right": '<path d="M5 12h14"></path><path d="M13 6l6 6-6 6"></path>',
    "arrow-up-right": '<path d="M7 17L17 7"></path><path d="M8 7h9v9"></path>',
    "arrow-left": '<path d="M19 12H5"></path><path d="M11 18l-6-6 6-6"></path>',
    "map-pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0Z"></path><circle cx="12" cy="10" r="3"></circle>',
    "clock": '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path>',
    "bookmark": '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z"></path>',
    "bookmark-check": '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z"></path><path d="M9 11l2 2 4-4"></path>',
    "check-circle": '<circle cx="12" cy="12" r="9"></circle><path d="M8.5 12.5l2.5 2.5 5-5"></path>',
    "x-circle": '<circle cx="12" cy="12" r="9"></circle><path d="M9 9l6 6"></path><path d="M15 9l-6 6"></path>',
    "alert": '<circle cx="12" cy="12" r="9"></circle><path d="M12 8v4"></path><path d="M12 16h.01"></path>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="m3 7 9 6 9-6"></path>',
    "phone": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"></path>',
    "graduation-cap": '<path d="m2 9 10-5 10 5-10 5L2 9Z"></path><path d="M7 11.5V17c0 1.5 2.2 2.5 5 2.5s5-1 5-2.5v-5.5"></path><path d="M22 9v5"></path>',
    "building": '<rect x="4" y="3" width="16" height="18" rx="1"></rect><path d="M9 7h.01M15 7h.01M9 11h.01M15 11h.01M9 15h.01M15 15h.01M9 19h6"></path>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"></rect><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><path d="M3 13h18"></path>',
    "share": '<path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"></path><path d="M16 6l-4-4-4 4"></path><path d="M12 2v13"></path>',
    "check": '<path d="M5 12l5 5L20 6"></path>',
    "sliders": '<path d="M4 21v-7"></path><path d="M4 10V3"></path><path d="M12 21v-9"></path><path d="M12 8V3"></path><path d="M20 21v-5"></path><path d="M20 12V3"></path><path d="M1 14h6"></path><path d="M9 8h6"></path><path d="M17 16h6"></path>',
    "plus": '<path d="M12 5v14"></path><path d="M5 12h14"></path>',
    "x": '<path d="M6 6l12 12"></path><path d="M18 6L6 18"></path>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>',
    "quote": '<path d="M3 21c3 0 7-1 7-8V5c0-1.25-.76-2-2-2H4c-1.25 0-2 .75-2 2v6c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1Z"></path><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.76-2-2-2h-4c-1.25 0-2 .75-2 2v6c0 1.25.75 2 2 2h1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1Z"></path>',
    "sparkles": '<path d="M12 3l1.9 5.7L19.6 10l-5.7 1.9L12 17.6l-1.9-5.7L4.4 10l5.7-1.9L12 3Z"></path><path d="M19 15l.9 2.6L22.5 18.5l-2.6.9L19 22l-.9-2.6L15.5 18.5l2.6-.9L19 15Z"></path>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"></path><path d="M9 12l2 2 4-4"></path>',
    "trending-up": '<path d="M3 17l6-6 4 4 8-8"></path><path d="M14 7h7v7"></path>',
    "file-text": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z"></path><path d="M14 3v6h6"></path><path d="M9 13h6"></path><path d="M9 17h6"></path>',
    "upload": '<path d="M12 16V4"></path><path d="M6 10l6-6 6 6"></path><path d="M4 20h16"></path>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"></rect><path d="M16 3v4"></path><path d="M8 3v4"></path><path d="M3 11h18"></path>',
    "tag": '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"></path><circle cx="7.5" cy="7.5" r="1.5"></circle>',
    "log-out": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><path d="M16 17l5-5-5-5"></path><path d="M21 12H9"></path>',
    "compass": '<circle cx="12" cy="12" r="9"></circle><path d="m15 9-2 4-4 2 2-4 4-2Z"></path>',
    "book-open": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2V3Z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7V3Z"></path>',
    "external-link": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><path d="M15 3h6v6"></path><path d="M10 14L21 3"></path>',
    "user": '<circle cx="12" cy="8" r="4"></circle><path d="M4 21c0-4 4-6 8-6s8 2 8 6"></path>',
    "wallet": '<path d="M20 7V5a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7Z"></path><path d="M16 12.5h.01"></path>',
    "menu": '<path d="M4 6h16"></path><path d="M4 12h16"></path><path d="M4 18h16"></path>'
  };

  function injectIcons(root) {
    Array.from((root || document).querySelectorAll("[data-icon]")).forEach(function (el) {
      var inner = ICONS[el.getAttribute("data-icon")] || "";
      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("aria-hidden", "true");
      svg.className.baseVal = "ic " + (el.getAttribute("class") || "");
      svg.innerHTML = inner;
      el.replaceWith(svg);
    });
  }

  function initReveal(scope) {
    (scope || document).querySelectorAll(".reveal:not(.revealed)").forEach(function (el) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add("revealed"); io.disconnect(); }
        });
      }, { threshold: 0.15 });
      io.observe(el);
    });
  }

  function startCounters(scope) {
    (scope || document).querySelectorAll("[data-count]").forEach(function (el) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          io.disconnect();
          var to = parseInt(el.getAttribute("data-count"), 10) || 0;
          var dur = 1400, t0 = performance.now();
          function tick(t) {
            var p = Math.min((t - t0) / dur, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(to * eased);
            if (p < 1) requestAnimationFrame(tick);
          }
          requestAnimationFrame(tick);
        });
      }, { threshold: 0.4 });
      io.observe(el);
    });
  }

  function initBurger() {
    var burger = document.querySelector(".nav-burger");
    var mobile = document.querySelector(".nav-mobile");
    if (!burger || !mobile) return;
    burger.addEventListener("click", function () { mobile.classList.toggle("hidden"); });
    mobile.addEventListener("click", function (e) {
      if (e.target.closest("a")) mobile.classList.add("hidden");
    });
  }

  /*
   * Guardados: por ahora se persisten en localStorage, igual que en el mockup.
   * Cuando exista el modelo de ofertas guardadas hay que reemplazar esto por
   * un POST al backend.
   */
  function initSaved() {
    var saved;
    try { saved = JSON.parse(localStorage.getItem("ien-saved") || "[]"); } catch (e) { saved = []; }

    function isSaved(id) { return saved.indexOf(id) !== -1; }

    function renderSavedButtons() {
      document.querySelectorAll("[data-save]").forEach(function (btn) {
        var id = parseInt(btn.getAttribute("data-save"), 10);
        var on = isSaved(id);
        btn.classList.toggle("bg-[#512DA8]", on);
        btn.classList.toggle("text-white", on);
        btn.classList.toggle("border-[#512DA8]", on);
        btn.title = on ? "Quitar de guardados" : "Guardar oferta";
        var ic = btn.querySelector("[data-icon]");
        if (ic) { ic.setAttribute("data-icon", on ? "bookmark-check" : "bookmark"); injectIcons(btn); }
      });
    }

    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-save]");
      if (!btn) return;
      var id = parseInt(btn.getAttribute("data-save"), 10);
      if (isSaved(id)) saved = saved.filter(function (x) { return x !== id; });
      else saved.push(id);
      try { localStorage.setItem("ien-saved", JSON.stringify(saved)); } catch (err) {}
      renderSavedButtons();
    });

    renderSavedButtons();
  }

  function init() {
    injectIcons(document);
    initReveal(document);
    startCounters(document);
    initBurger();
    initSaved();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.IenUI = { injectIcons: injectIcons, initReveal: initReveal, startCounters: startCounters };
})();
