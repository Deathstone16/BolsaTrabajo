(() => {
  const menus = [...document.querySelectorAll('[data-admin-notifications-url]')];
  if (!menus.length) return;
  let running = false;
  let stopped = false;
  let previous;
  async function refresh() {
    if (running || stopped || document.hidden) return;
    running = true;
    try {
      const response = await fetch(menus[0].dataset.adminNotificationsUrl, {credentials: 'same-origin', cache: 'no-store'});
      if (response.redirected || [401, 403].includes(response.status)) { stopped = true; return; }
      if (!response.ok) return;
      const data = await response.json();
      const signature = JSON.stringify(data);
      if (signature === previous) return;
      previous = signature;
      document.querySelectorAll('[data-admin-offer-count]').forEach((count) => { count.textContent = `(${data.ofertas_pendientes})`; count.hidden = !data.ofertas_pendientes; });
      menus.forEach((menu) => {
        menu.querySelector('[data-admin-notification-dot]').hidden = !data.pendientes;
        menu.querySelector('summary').setAttribute('aria-label', `Notificaciones de revisión: ${data.pendientes} pendiente${data.pendientes === 1 ? '' : 's'}`);
        menu.querySelector('[data-admin-notification-count]').textContent = `${data.empresas_pendientes} empresa${data.empresas_pendientes === 1 ? '' : 's'} y ${data.ofertas_pendientes} oferta${data.ofertas_pendientes === 1 ? '' : 's'}`;
        const list = menu.querySelector('[data-admin-notification-items]');
        list.replaceChildren();
        data.recientes.forEach((item) => {
          const row = document.createElement('li');
          const link = document.createElement('a');
          const name = document.createElement('strong');
          name.textContent = item.titulo;
          const status = document.createElement('span');
          status.textContent = `${item.tipo}: ${item.estado}`;
          link.href = item.url;
          link.append(name, status);
          row.append(link);
          list.append(row);
        });
        if (!data.recientes.length) {
          const empty = document.createElement('li');
          empty.className = 'ien-admin-notification-empty';
          empty.textContent = 'Todavía no hay solicitudes.';
          list.append(empty);
        }
      });
    } catch (_) {
      // Mantener el último estado mientras se recupera la conexión.
    } finally { running = false; }
  }
  menus.forEach((menu) => menu.addEventListener('toggle', () => { if (menu.open) refresh(); }));
  document.addEventListener('visibilitychange', refresh);
  setInterval(refresh, 60000);
})();
