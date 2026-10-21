(function () {
  'use strict';

  const config = document.getElementById('cv-notifications-config');
  if (!config) return;

  const badgeKey = 'ien-cv-analysis-ready';
  const statusTemplate = config.dataset.statusUrl;
  const profileUrl = config.dataset.profileUrl;
  let analysisId = Number(config.dataset.analysisId) || null;
  let currentVersionId = Number(config.dataset.currentVersionId) || null;
  let socket = null;
  let pollTimer = null;
  let retryTimer = null;
  let retryCount = 0;
  let lastNotifiedId = null;

  function showBadge() {
    const badge = document.getElementById('cv-analysis-badge');
    if (badge) badge.classList.remove('hidden');
  }

  function clearBadge() {
    try { localStorage.removeItem(badgeKey); } catch (_) { /* storage disabled */ }
    const badge = document.getElementById('cv-analysis-badge');
    if (badge) badge.classList.add('hidden');
  }

  function showToast() {
    const box = document.createElement('div');
    box.className = 'fixed bottom-5 right-5 z-[100] max-w-sm rounded-2xl border border-emerald-200 bg-white p-4 shadow-xl';
    box.setAttribute('role', 'status');
    box.textContent = 'Análisis listo ✓ ';
    const link = document.createElement('a');
    link.href = profileUrl;
    link.className = 'font-semibold text-[#512DA8] underline';
    link.textContent = 'Ver análisis';
    box.appendChild(link);
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 10000);
  }

  function complete(payload) {
    const id = Number(payload.analysis_id);
    if (!id || id === lastNotifiedId) return;
    if ((currentVersionId && Number(payload.version_cv_id) !== currentVersionId) || payload.es_version_actual === false) return;
    // No aceptar un evento de otro análisis si conocemos el que está en curso.
    if (analysisId && id !== analysisId) return;
    lastNotifiedId = id;
    analysisId = null;
    stopPolling();
    document.dispatchEvent(new CustomEvent('cv:analysis-complete', { detail: payload }));
    if (payload.status === 'completado') {
      try { localStorage.setItem(badgeKey, String(id)); } catch (_) { /* storage disabled */ }
      showBadge();
      showToast();
    } else if (window.IenUI) {
      window.IenUI.aviso('error', 'No se pudo analizar tu CV. Podés volver a intentarlo.');
    }
  }

  async function checkStatus() {
    if (!analysisId) return;
    const id = analysisId;
    try {
      const response = await fetch(statusTemplate.replace('/0/', '/' + id + '/'), {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!response.ok) return;
      const data = await response.json();
      if (data.es_version_actual === false) { analysisId = null; stopPolling(); return; }
      if (data.estado === 'completado' || data.estado === 'error') {
        complete({ analysis_id: id, version_cv_id: data.version_cv_id, es_version_actual: data.es_version_actual, status: data.estado, resultado_url: data.resultado_url, mensaje: data.mensaje });
      }
    } catch (_) { /* el siguiente intento puede recuperar la conexión */ }
  }

  function stopPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
  }

  function startPolling() {
    if (!analysisId || pollTimer) return;
    checkStatus();
    pollTimer = setInterval(checkStatus, 10000);
  }

  function connect() {
    if (!window.WebSocket) { startPolling(); return; }
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(scheme + '//' + location.host + '/ws/cv-analysis/?token=' + encodeURIComponent(config.dataset.token));
    socket.onopen = function () {
      retryCount = 0;
      if (retryTimer) clearTimeout(retryTimer);
      stopPolling();
      // Cubre el evento que pudo llegar mientras el socket estaba desconectado.
      checkStatus();
    };
    socket.onmessage = function (event) {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'cv.analyzed') complete(message.payload || {});
      } catch (_) { /* ignorar un mensaje mal formado */ }
    };
    socket.onclose = function (event) {
      startPolling();
      // 4401 implica sesión/token inválido: recargar emitirá uno nuevo.
      if (event.code === 4401) return;
      const delay = Math.min(30000, 1000 * Math.pow(2, retryCount++));
      retryTimer = setTimeout(connect, delay);
    };
    socket.onerror = function () { socket.close(); };
  }

  window.CVNotifications = {
    watch: function (id, versionId) {
      analysisId = Number(id) || null;
      currentVersionId = Number(versionId) || currentVersionId;
      if (analysisId) checkStatus();
      if (!window.WebSocket || !socket || socket.readyState !== WebSocket.OPEN) startPolling();
    },
    connected: function () { return Boolean(window.WebSocket && socket && socket.readyState === WebSocket.OPEN); },
  };

  document.addEventListener('DOMContentLoaded', function () {
    try { if (localStorage.getItem(badgeKey)) showBadge(); } catch (_) { /* storage disabled */ }
    const anchor = document.getElementById('cv-analysis');
    if (anchor) clearBadge();
    document.querySelectorAll('a[href$="#cv-analysis"]').forEach(function (link) {
      link.addEventListener('click', clearBadge);
    });
    connect();
    if (analysisId) startPolling();
  });
})();
