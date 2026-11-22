const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('el punto rojo se actualiza y desaparece al resolver; una sesión vencida detiene consultas', async () => {
  const element = () => ({
    children: [], attributes: {},
    append(...items) { this.children.push(...items); },
    replaceChildren() { this.children = []; },
    setAttribute(key, value) { this.attributes[key] = value; },
  });
  const dot = {hidden: true};
  const summary = element();
  const count = element();
  const list = element();
  const menu = {
    dataset: {adminNotificationsUrl: '/moderacion/notificaciones-empresas/'},
    addEventListener() {},
    querySelector(selector) {
      return {'[data-admin-notification-dot]': dot, summary,
        '[data-admin-notification-count]': count, '[data-admin-notification-items]': list}[selector];
    },
  };
  let poll;
  let calls = 0;
  let payload = {pendientes: 1, recientes: [{empresa: '<Empresa>', estado: 'Pendiente', fecha: '2026-11-16T12:00:00Z', url: '/moderacion/empresas/1/'}]};
  let status = 200;
  const context = {
    document: {hidden: false, querySelectorAll: () => [menu], createElement: element, addEventListener() {}},
    setInterval(callback, milliseconds) { assert.equal(milliseconds, 60000); poll = callback; },
    Intl, Date,
    fetch: async (url, options) => {
      assert.equal(url, '/moderacion/notificaciones-empresas/');
      assert.equal(options.credentials, 'same-origin');
      assert.equal(options.cache, 'no-store');
      calls++;
      return {status, ok: status === 200, json: async () => payload};
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../admin-notifications.js'), 'utf8'), context);
  await poll();
  assert.equal(dot.hidden, false);
  assert.equal(count.textContent, '1 pendiente de revisión');
  assert.equal(list.children[0].children[0].children[0].textContent, '<Empresa>');
  payload = {pendientes: 0, recientes: []};
  await poll();
  assert.equal(dot.hidden, true);
  assert.equal(list.children[0].textContent, 'Todavía no hay solicitudes.');
  status = 403;
  await poll();
  await poll();
  assert.equal(calls, 3);
});
