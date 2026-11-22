const test = require('node:test');
const assert = require('node:assert/strict');
const {splitItems, separateKnown} = require('../../ofertas/requirements.js');

test('separa por comas, punto y coma y saltos; conserva nombres compuestos', () => {
  assert.deepEqual(splitItems(' Python, HTML; Excel\nTrabajo  en equipo\r\n;'), ['Python', 'HTML', 'Excel', 'Trabajo en equipo']);
});

test('sugiere separar habilidades conocidas sin inventar cortes en otras palabras', () => {
  const vocabulary = ['Python', 'HTML', 'Excel', 'Java', 'JavaScript', 'Script', 'Trabajo en equipo'];
  assert.deepEqual(separateKnown('PythonHTML', vocabulary), ['Python', 'HTML']);
  assert.deepEqual(separateKnown('pythonEXCEL', vocabulary), ['Python', 'Excel']);
  assert.deepEqual(separateKnown('JavaScript', vocabulary), ['JavaScript']);
  assert.deepEqual(separateKnown('Trabajo en equipo', vocabulary), ['Trabajo en equipo']);
  assert.deepEqual(separateKnown('UnaHerramientaPropia', vocabulary), ['UnaHerramientaPropia']);
});
