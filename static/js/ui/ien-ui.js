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
    "menu": '<path d="M4 6h16"></path><path d="M4 12h16"></path><path d="M4 18h16"></path>',
    // Agregados al portar el panel del oferente: no estaban en el mockup.
    "pencil": '<path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path>',
    "trash": '<path d="M3 6h18"></path><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"></path><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"></rect><circle cx="9" cy="9" r="2"></circle><path d="m21 15-5-5L5 21"></path>',
    // estado_oferente.py devuelve "alert-circle"; el mockup solo traia "alert".
    "alert-circle": '<circle cx="12" cy="12" r="9"></circle><path d="M12 8v4"></path><path d="M12 16h.01"></path>',
    // Agregados al portar moderacion y recuperacion de contrasena.
    "chevron-right": '<path d="m9 6 6 6-6 6"></path>',
    "eye-off": '<path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-2.6 3.8"></path><path d="M6.6 6.6A18 18 0 0 0 2 12s3.5 8 10 8a9.1 9.1 0 0 0 4.4-1.1"></path><path d="M3 3l18 18"></path>',
    "filter": '<path d="M3 5h18l-7 8v5l-4 2v-7L3 5Z"></path>',
    "triangle-alert": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path>',
    "info": '<circle cx="12" cy="12" r="9"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path>',
    "globe": '<circle cx="12" cy="12" r="9"></circle><path d="M3 12h18"></path><path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18Z"></path>',
    "archive": '<rect x="3" y="4" width="18" height="4" rx="1"></rect><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"></path><path d="M10 12h4"></path>',
    "mail-check": '<path d="M21 10V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8"></path><path d="m3 7 9 6 9-6"></path><path d="m16 19 2 2 4-4"></path>',
    "lock-keyhole": '<rect x="4" y="11" width="16" height="10" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path><circle cx="12" cy="16" r="1"></circle>',
    "lock-keyhole-open": '<rect x="4" y="11" width="16" height="10" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 7.5-2"></path><circle cx="12" cy="16" r="1"></circle>'
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

  /* ------------------------------------------------------------------------
   * Popups del sitio. Reemplazan a confirm() / alert() del navegador.
   *
   *   IenUI.confirmar({ titulo, mensaje, confirmar, cancelar, peligro })
   *     -> Promise<boolean>. peligro:true pinta el boton en rojo.
   *   IenUI.aviso(tipo, mensaje)
   *     -> notificacion flotante que se cierra sola. tipo: exito | error | info
   *
   * Los textos se insertan con textContent: no hace falta escapar HTML.
   * --------------------------------------------------------------------- */
  function crearIcono(nombre, clases) {
    var span = document.createElement("span");
    span.setAttribute("data-icon", nombre);
    span.className = clases;
    return span;
  }

  function confirmar(opciones) {
    opciones = opciones || {};
    return new Promise(function (resolver) {
      var peligro = !!opciones.peligro;
      var previo = document.activeElement;

      var overlay = document.createElement("div");
      overlay.className = "ien-overlay";

      var modal = document.createElement("div");
      modal.className = "ien-modal panel";
      modal.setAttribute("role", "alertdialog");
      modal.setAttribute("aria-modal", "true");

      var burbuja = document.createElement("div");
      burbuja.className = "ien-modal-icono " + (peligro ? "es-peligro" : "es-info");
      burbuja.appendChild(crearIcono(opciones.icono || (peligro ? "triangle-alert" : "info"), "h-6 w-6"));

      var titulo = document.createElement("h3");
      titulo.className = "ien-modal-titulo";
      titulo.id = "ien-modal-titulo-" + Date.now();
      titulo.textContent = opciones.titulo || "¿Confirmás esta acción?";
      modal.setAttribute("aria-labelledby", titulo.id);

      modal.appendChild(burbuja);
      modal.appendChild(titulo);
      if (opciones.mensaje) {
        var texto = document.createElement("p");
        texto.className = "ien-modal-texto";
        texto.textContent = opciones.mensaje;
        modal.appendChild(texto);
      }

      var botones = document.createElement("div");
      botones.className = "ien-modal-botones";
      var cancelar = document.createElement("button");
      cancelar.type = "button";
      cancelar.className = "btn-ghost";
      cancelar.textContent = opciones.cancelar || "Cancelar";
      var aceptar = document.createElement("button");
      aceptar.type = "button";
      aceptar.className = peligro ? "btn-ien btn-peligro" : "btn-ien";
      aceptar.textContent = opciones.confirmar || "Confirmar";
      botones.appendChild(cancelar);
      botones.appendChild(aceptar);
      modal.appendChild(botones);

      overlay.appendChild(modal);
      document.body.appendChild(overlay);
      injectIcons(modal);
      requestAnimationFrame(function () { overlay.classList.add("abierto"); });

      function cerrar(valor) {
        document.removeEventListener("keydown", onTecla);
        overlay.classList.remove("abierto");
        setTimeout(function () { overlay.remove(); }, 180);
        if (previo && previo.focus) previo.focus();
        resolver(valor);
      }
      function onTecla(e) {
        if (e.key === "Escape") cerrar(false);
        if (e.key === "Tab") {  // el foco no se escapa del modal
          if (document.activeElement === aceptar && !e.shiftKey) { e.preventDefault(); cancelar.focus(); }
          else if (document.activeElement === cancelar && e.shiftKey) { e.preventDefault(); aceptar.focus(); }
        }
      }
      overlay.addEventListener("click", function (e) { if (e.target === overlay) cerrar(false); });
      cancelar.addEventListener("click", function () { cerrar(false); });
      aceptar.addEventListener("click", function () { cerrar(true); });
      document.addEventListener("keydown", onTecla);
      // en acciones peligrosas el foco arranca en Cancelar, para no confirmar con un Enter distraido
      (peligro ? cancelar : aceptar).focus();
    });
  }

  function contenedorAvisos() {
    var c = document.getElementById("ien-avisos");
    if (!c) {
      c = document.createElement("div");
      c.id = "ien-avisos";
      c.setAttribute("aria-live", "polite");
      document.body.appendChild(c);
    }
    return c;
  }

  function aviso(tipo, mensaje, duracion) {
    var iconos = { exito: "check-circle", error: "x-circle", info: "info" };
    if (!iconos[tipo]) tipo = "info";
    var el = document.createElement("div");
    el.className = "ien-aviso es-" + tipo;
    el.setAttribute("role", tipo === "error" ? "alert" : "status");
    el.appendChild(crearIcono(iconos[tipo], "h-5 w-5 shrink-0"));
    var texto = document.createElement("p");
    texto.textContent = mensaje;
    el.appendChild(texto);
    var cerrarBtn = document.createElement("button");
    cerrarBtn.type = "button";
    cerrarBtn.className = "ien-aviso-cerrar";
    cerrarBtn.setAttribute("aria-label", "Cerrar aviso");
    cerrarBtn.appendChild(crearIcono("x", "h-4 w-4"));
    el.appendChild(cerrarBtn);

    contenedorAvisos().appendChild(el);
    injectIcons(el);
    requestAnimationFrame(function () { el.classList.add("abierto"); });

    function quitar() {
      el.classList.remove("abierto");
      setTimeout(function () { el.remove(); }, 250);
    }
    cerrarBtn.addEventListener("click", quitar);
    setTimeout(quitar, duracion || (tipo === "error" ? 7000 : 4500));
  }

  // Para acciones que terminan en location.reload(): el aviso se guarda y se
  // muestra despues de recargar. Si sessionStorage no esta disponible, se pierde.
  var CLAVE_AVISO = "ien-aviso-pendiente";
  function avisoTrasRecarga(tipo, mensaje) {
    try { sessionStorage.setItem(CLAVE_AVISO, JSON.stringify({ tipo: tipo, mensaje: mensaje })); } catch (e) {}
  }
  function initAvisoPendiente() {
    var guardado = null;
    try {
      guardado = JSON.parse(sessionStorage.getItem(CLAVE_AVISO) || "null");
      sessionStorage.removeItem(CLAVE_AVISO);
    } catch (e) {}
    if (guardado && guardado.mensaje) aviso(guardado.tipo, guardado.mensaje);
  }

  // Mensajes de Django (django.contrib.messages): la base los deja en un
  // <script type="application/json" id="ien-mensajes"> y aca se muestran como avisos.
  function initMensajesDjango() {
    var nodo = document.getElementById("ien-mensajes");
    if (!nodo) return;
    var lista;
    try { lista = JSON.parse(nodo.textContent || "[]"); } catch (e) { lista = []; }
    var mapa = { success: "exito", error: "error", warning: "error", info: "info", debug: "info" };
    lista.forEach(function (m, i) {
      setTimeout(function () { aviso(mapa[m.nivel] || "info", m.texto); }, i * 150);
    });
  }

  function init() {
    injectIcons(document);
    initReveal(document);
    startCounters(document);
    initBurger();
    initSaved();
    initMensajesDjango();
    initAvisoPendiente();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.IenUI = { injectIcons: injectIcons, initReveal: initReveal, startCounters: startCounters,
                  confirmar: confirmar, aviso: aviso, avisoTrasRecarga: avisoTrasRecarga };
})();
