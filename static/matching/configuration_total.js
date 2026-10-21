(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    const names = ['technical_skills', 'soft_skills', 'experience', 'education', 'languages', 'logistics', 'desirables'];
    const inputs = names.map(function (name) { return document.getElementById('id_' + name); }).filter(Boolean);
    if (!inputs.length) return;
    const total = document.createElement('div');
    total.className = 'form-row';
    total.innerHTML = '<div><label>Total de porcentajes</label><div id="matching-weight-total" aria-live="polite"></div></div>';
    const submitRow = document.querySelector('.submit-row');
    if (submitRow) submitRow.parentNode.insertBefore(total, submitRow);
    function update() {
      const sum = inputs.reduce(function (value, input) {
        const parsed = Number(String(input.value).replace(',', '.'));
        return value + (Number.isFinite(parsed) ? parsed : 0);
      }, 0);
      const output = document.getElementById('matching-weight-total');
      if (output) {
        output.textContent = sum.toFixed(2) + '%';
        output.style.color = sum > 100 ? '#ba2121' : (sum === 100 ? '#16823a' : '#666');
      }
    }
    inputs.forEach(function (input) { input.addEventListener('input', update); });
    update();
  });
})();
