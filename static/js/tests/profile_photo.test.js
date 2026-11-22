const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function element(properties = {}) {
  return Object.assign({
    hidden: false,
    events: {},
    addEventListener(name, callback) { this.events[name] = callback; },
    getAttribute() { return null; },
    removeAttribute() {},
  }, properties);
}

test('photo and cover crop independently and submit both processed images together', async () => {
  let submissions = 0;
  const form = element({
    requestSubmit() {
      const event = {preventDefault() { throw new Error('Second submit must proceed'); }};
      this.events.submit(event);
      submissions++;
    },
  });
  function makeEditor(name, width, height) {
    const draws = [];
    const controls = {
      '[data-photo-input]': element({name, form, files: []}),
      '[data-photo-preview]': element(),
      '[data-photo-placeholder]': element(),
      '[data-photo-editor]': element({hidden: true}),
      '[data-photo-error]': element(),
      '[data-photo-zoom]': element({value: '1'}),
      '[data-photo-picker]': element(),
      '[data-photo-picker-label]': element({textContent: name === 'logo' ? 'Elegir foto o logo' : 'Elegir imagen de portada'}),
      '[data-photo-picker-action]': element({textContent: 'Seleccionar'}),
      '[data-photo-status]': element({textContent: 'Ninguna imagen nueva seleccionada.'}),
      '[data-photo-reset]': element(),
      '[data-photo-canvas]': element({
        width, height,
        getBoundingClientRect: () => ({width, height}),
        getContext: () => ({clearRect() {}, drawImage(...args) { draws.push(args); }}),
        toBlob(callback) { callback(new Blob(['processed'], {type: 'image/webp'})); },
      }),
    };
    return {
      dataset: {}, controls, draws,
      querySelector: (selector) => controls[selector] || null,
    };
  }
  const photo = makeEditor('logo', 512, 512);
  const cover = makeEditor('banner', 1200, 240);
  const sandbox = {
    document: {querySelectorAll: () => [photo, cover]},
    Image: class {
      constructor() { this.width = 1000; this.height = 500; }
      async decode() {}
    },
    URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}},
    Blob, File,
    DataTransfer: class {
      constructor() {
        this.files = [];
        this.items = {add: (file) => this.files.push(file)};
      }
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../profile-photo.js'), 'utf8'), sandbox);
  for (const editor of [photo, cover]) {
    const input = editor.controls['[data-photo-input]'];
    input.files = [new File(['image'], 'original.png', {type: 'image/png'})];
    await input.events.change();
    assert.equal(editor.controls['[data-photo-editor]'].hidden, false);
    assert.equal(editor.controls['[data-photo-picker-label]'].textContent, 'original.png');
    assert.equal(editor.controls['[data-photo-picker-action]'].textContent, 'Listo');
    assert.match(editor.controls['[data-photo-status]'].textContent, /Imagen lista/);
  }
  assert.deepEqual(photo.draws.at(-1).slice(1, 5), [250, 0, 500, 500]);
  photo.controls['[data-photo-zoom]'].value = '2';
  photo.controls['[data-photo-zoom]'].events.input();
  assert.deepEqual(photo.draws.at(-1).slice(1, 5), [375, 125, 250, 250]);
  const photoCanvas = photo.controls['[data-photo-canvas]'];
  photoCanvas.events.pointerdown({button: 0, pointerId: 1, clientX: 100, clientY: 100, preventDefault() {}});
  photoCanvas.events.pointermove({pointerId: 1, clientX: 228, clientY: 100, preventDefault() {}});
  photoCanvas.events.pointerup({pointerId: 1});
  assert.ok(Math.abs(photo.draws.at(-1)[1] - 312.5) < 0.0001);
  assert.deepEqual(photo.draws.at(-1).slice(2, 5), [125, 250, 250]);
  assert.equal(cover.draws.at(-1)[3], 1000);
  let prevented = false;
  await form.events.submit({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(submissions, 1);
  assert.equal(photo.controls['[data-photo-input]'].files[0].name, 'logo.webp');
  assert.equal(cover.controls['[data-photo-input]'].files[0].name, 'banner.webp');
});
