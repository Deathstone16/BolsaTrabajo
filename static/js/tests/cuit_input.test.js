const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('formats existing and pasted CUITs and preserves the caret during edits', () => {
  const events = {};
  const input = {
    value: '20123456786',
    selectionStart: 11,
    selectionEnd: 11,
    removeAttribute() {},
    setCustomValidity() {},
    addEventListener(type, listener) { events[type] = listener; },
    setSelectionRange(start, end) {
      this.selectionStart = start;
      this.selectionEnd = end;
    },
  };
  const script = fs.readFileSync(path.join(__dirname, '../cuit-input.js'), 'utf8');
  vm.runInNewContext(script, {document: {querySelectorAll: () => [input]}});
  assert.equal(input.value, '20-12345678-6');

  input.value = ' 30 12345678 1 ';
  input.setSelectionRange(15, 15);
  events.input();
  assert.equal(input.value, '30-12345678-1');
  assert.equal(input.selectionStart, 13);

  input.setSelectionRange(3, 3);
  events.keydown({key: 'Backspace'});
  assert.equal(input.selectionStart, 2);
  input.value = '3-12345678-1';
  input.setSelectionRange(1, 1);
  events.input();
  assert.equal(input.value, '31-23456781');
  assert.equal(input.selectionStart, 1);
});
