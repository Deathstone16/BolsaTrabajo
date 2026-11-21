const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../ui/http.js'), 'utf8');
function setup(fetch) {
  const context = {window: {}, fetch, AbortController, setTimeout, clearTimeout};
  vm.runInNewContext(source, context);
  return context.window.IenHTTP;
}
test('a hanging response times out without retrying a POST', async () => {
  let calls = 0;
  const api = setup((url, options) => {
    calls++;
    return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))));
  });
  await assert.rejects(api.json('/submit/', {method: 'POST'}, 5), error => error.code === 'timeout' && api.message(error).includes('Revisá el estado'));
  assert.equal(calls, 1);
});
test('server HTML is handled without trying to decode JSON', async () => {
  const api = setup(async () => ({status: 503}));
  await assert.rejects(api.json('/submit/'), error => error.code === 'unavailable');
});
test('validation JSON remains available to the form', async () => {
  const api = setup(async () => ({status: 400, headers: new Headers({'Content-Type': 'application/json'}), json: async () => ({success: false, mensaje: 'Completá el título'})}));
  const response = await api.json('/submit/');
  assert.equal(response.success, false);
  assert.equal(response.mensaje, 'Completá el título');
});
test('a login redirect does not become a JSON parsing error', async () => {
  const api = setup(async () => ({status: 200, redirected: true, headers: new Headers({'Content-Type': 'text/html'})}));
  await assert.rejects(api.json('/submit/'), error => error.code === 'session');
});
