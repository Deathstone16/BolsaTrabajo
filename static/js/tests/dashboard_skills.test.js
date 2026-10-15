const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'dashboard.js'), 'utf8');

test('edición precarga chips blandos y permite quitar/agregar sin perder el valor', () => {
  const hidden = { value: 'Comunicación, Liderazgo' };
  const container = {
    children: [],
    set innerHTML(value) { if (value === '') this.children = []; },
    appendChild(child) { child.parent = this; this.children.push(child); },
  };
  const nodes = { 'tags-container-blandas': container, 'id_habilidades_blandas': hidden };
  const document = {
    getElementById: id => nodes[id] || null,
    addEventListener() {},
    createTextNode: text => ({ textContent: text }),
    createElement: () => ({
      children: [], dataset: {},
      appendChild(child) { this.children.push(child); },
      querySelector(name) { return name === 'button' ? this.children[1] : null; },
      addEventListener(name, fn) { this[name] = fn; },
      remove() { this.parent.children = this.parent.children.filter(item => item !== this); },
    }),
  };
  const context = { document, window: { IenUI: { injectIcons() {} } }, alert() {} };
  vm.runInNewContext(source, context);

  context.inicializarTags('blandas');
  assert.equal(container.children.length, 2);
  assert.equal(container.children[0].querySelector('button').dataset.tag, 'Comunicación');
  assert.match(container.children[0].className, /emerald/);
  container.children[0].querySelector('button').click();
  assert.equal(hidden.value, 'Liderazgo');
  context.dibujarPildora('Empatía', 'blandas');
  assert.equal(hidden.value, 'Liderazgo, Empatía');
});
