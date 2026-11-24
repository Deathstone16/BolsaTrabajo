(() => {
  const nodes = [...document.querySelectorAll('.cv-live-status')];
  const button = document.getElementById('cv-refresh');
  let busy = false;
  async function refresh() {
    if (busy || document.hidden) return;
    busy = true;
    button.disabled = true;
    const pending = [...nodes];
    async function worker() {
      while (pending.length) {
        const node = pending.shift();
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 8000);
        try {
          const response = await fetch(node.dataset.url, {signal: controller.signal, credentials: 'same-origin'});
          if (!response.ok || response.redirected) throw new Error('Consulta no disponible');
          const data = await response.json();
          let text = data.message;
          if (Number.isInteger(data.completed_packets) && Number.isInteger(data.total_packets)) {
            text += ` · ${data.completed_packets}/${data.total_packets} partes`;
          }
          if (data.retry_after_seconds > 0) text += ` · reintento en ~${data.retry_after_seconds} s`;
          node.textContent = text;
          node.style.color = ({failed: 'var(--error-fg)', unavailable: 'var(--error-fg)', completed: 'var(--body-fg)'})[data.status] || 'var(--body-fg)';
        } catch (_) {
          node.textContent = 'Sin respuesta al consultar; estado sin confirmar';
        } finally { clearTimeout(timer); }
      }
    }
    try {
      await Promise.all(Array.from({length: Math.min(3, nodes.length)}, worker));
      document.getElementById('cv-checked').textContent = `Última consulta: ${new Date().toLocaleTimeString()}`;
    } finally { busy = false; button.disabled = false; }
  }
  button.addEventListener('click', refresh);
  refresh();
  setInterval(refresh, 15000);
})();
// Refresh the persisted totals and discover newly submitted CVs as well.
setTimeout(() => { if (!document.hidden) window.location.reload(); }, 60000);
