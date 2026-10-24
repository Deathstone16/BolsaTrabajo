const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'cv_notifications.js'), 'utf8');

function setup() {
  const listeners = {};
  const scheduled = [];
  const intervals = [];
  const created = [];
  const storage = new Map();
  const config = { dataset: {
    token: 'signed-token', analysisId: '31',
    statusUrl: '/ia/analisis/0/estado/', profileUrl: '/ia/perfil-profesional/',
  } };
  const badge = { classList: {
    hidden: true,
    remove(name) { if (name === 'hidden') this.hidden = false; },
    add(name) { if (name === 'hidden') this.hidden = true; },
  } };
  const body = { children: [], appendChild(item) { this.children.push(item); } };
  const document = {
    body,
    getElementById(id) { return { 'cv-notifications-config': config, 'cv-analysis-badge': badge }[id] || null; },
    querySelectorAll() { return []; },
    addEventListener(name, fn) { listeners[name] = fn; },
    dispatchEvent(event) { if (listeners[event.type]) listeners[event.type](event); },
    createElement() { return { children: [], appendChild(item) { this.children.push(item); }, setAttribute() {}, remove() {} }; },
  };
  class FakeSocket {
    static OPEN = 1;
    constructor(url) { this.url = url; this.readyState = 0; created.push(this); }
    close() { this.readyState = 3; }
  }
  const context = {
    document, WebSocket: FakeSocket,
    window: { WebSocket: FakeSocket },
    location: { protocol: 'http:', host: 'localhost:8000' },
    localStorage: { setItem: (k, v) => storage.set(k, v), getItem: k => storage.get(k), removeItem: k => storage.delete(k) },
    CustomEvent: function (type, options) { this.type = type; this.detail = options.detail; },
    setTimeout: (fn, ms) => { scheduled.push({ fn, ms }); return scheduled.length; },
    clearTimeout() {},
    setInterval: (fn, ms) => { intervals.push({ fn, ms }); return intervals.length; },
    clearInterval() {},
    fetch: async () => ({ ok: true, json: async () => ({ estado: 'pendiente' }) }),
  };
  vm.runInNewContext(source, context);
  document.dispatchEvent({ type: 'DOMContentLoaded' });
  return { created, scheduled, intervals, badge, body, storage, context };
}

test('WebSocket muestra toast con enlace y badge al finalizar', () => {
  const state = setup();
  const socket = state.created[0];
  socket.readyState = 1;
  socket.onopen();
  socket.onmessage({ data: JSON.stringify({ type: 'cv.analyzed', payload: { analysis_id: 31, version_cv_id: 1, es_version_actual: true, status: 'completado' } }) });
  assert.equal(state.body.children.length, 1);
  assert.equal(state.body.children[0].children[0].href, '/ia/perfil-profesional/');
  assert.equal(state.body.children[0].children[0].textContent, 'Ver mi perfil profesional');
  assert.match(state.body.children[0].textContent, /Análisis listo/);
  assert.equal(state.badge.classList.hidden, false);
  assert.equal(state.storage.get('ien-cv-analysis-ready'), '31');
});

test('polling conserva la identidad de versión al completar el análisis', async () => {
  const state = setup();
  state.context.fetch = async () => ({ ok: true, json: async () => ({
    estado: 'completado', version_cv_id: 1, es_version_actual: true,
    resultado_url: '/ia/analisis/31/', mensaje: 'CV listo',
  }) });
  state.created[0].onclose({ code: 1006 });
  const poll = state.intervals.find(timer => timer.ms === 10000);
  await poll.fn();
  assert.equal(state.body.children.length, 1);
  assert.equal(state.storage.get('ien-cv-analysis-ready'), '31');
});

test('desconexión activa polling de 10 s y reconexión exponencial', () => {
  const state = setup();
  state.created[0].onclose({ code: 1006 });
  assert.ok(state.intervals.some(timer => timer.ms === 10000));
  const firstRetry = state.scheduled.find(timer => timer.ms === 1000);
  assert.ok(firstRetry);
  firstRetry.fn();
  assert.equal(state.created.length, 2);
  state.created[1].onclose({ code: 1006 });
  assert.ok(state.scheduled.some(timer => timer.ms === 2000));
});
