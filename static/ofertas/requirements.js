(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    const mandatory = document.getElementById('id_requisitos_obligatorios');
    const desirable = document.getElementById('id_requisitos_deseables');
    const categoriesInput = document.getElementById('id_categorias_requisitos');
    const categoryRows = document.getElementById('categorias-obligatorias');
    const summary = document.getElementById('resumen-requisitos');
    const experienceClass = document.getElementById('id_experiencia_clasificacion');
    const educationClass = document.getElementById('id_educacion_clasificacion');
    if (!mandatory || !categoriesInput || !categoryRows || !summary) return;
    const labels = {
      technical_skills: 'Habilidades técnicas', soft_skills: 'Habilidades blandas',
      experience: 'Experiencia', education: 'Formación', languages: 'Idiomas', logistics: 'Ubicación, modalidad y disponibilidad',
    };
    let saved = {};
    try { saved = JSON.parse(categoriesInput.value || '{}'); } catch (_) { saved = {}; }
    const selectItems = ['technical_skills', 'soft_skills', 'experience', 'education', 'languages', 'logistics'];
    function suggest(text) {
      const value = text.toLocaleLowerCase('es');
      if (/idioma|ingl[eé]s|portugu[eé]s|franc[eé]s|nivel b[12]/.test(value)) return 'languages';
      if (/experiencia|a[nñ]os|antig[uü]edad|trayectoria/.test(value)) return 'experience';
      if (/universidad|terciario|secundario|t[ií]tulo|formaci[oó]n|certificaci[oó]n/.test(value)) return 'education';
      if (/licencia|registro|disponibilidad|viaje|viajar|ubicaci[oó]n|residir|presencial|remoto|turno/.test(value)) return 'logistics';
      if (/comunicaci[oó]n|liderazgo|equipo|empat[ií]a|negociaci[oó]n|organizaci[oó]n/.test(value)) return 'soft_skills';
      return 'technical_skills';
    }
    function render() {
      const lines = mandatory.value.split(/\r?\n/).map(function (line) { return line.trim(); }).filter(Boolean);
      const previous = saved.mandatory || [];
      categoryRows.replaceChildren();
      const mapping = [];
      lines.forEach(function (line, index) {
        const row = document.createElement('label');
        row.className = 'grid grid-cols-1 gap-2 rounded-lg border border-border p-3 sm:grid-cols-[1fr_16rem] sm:items-center';
        const text = document.createElement('span');
        text.className = 'text-sm text-[#26222E]';
        text.textContent = line;
        const suggestion = document.createElement('small');
        suggestion.className = 'block text-xs text-[#6B645C]';
        suggestion.textContent = 'Sugerencia: ' + labels[suggest(line)] + '. Confirmá la categoría.';
        text.appendChild(suggestion);
        const select = document.createElement('select');
        select.className = 'input-ien';
        select.setAttribute('aria-label', 'Categoría del requisito: ' + line);
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Confirmá la categoría';
        select.appendChild(placeholder);
        selectItems.forEach(function (key) {
          const option = document.createElement('option');
          option.value = key;
          option.textContent = labels[key];
          select.appendChild(option);
        });
        select.value = previous[index] || '';
        select.dataset.suggestion = suggest(line);
        select.addEventListener('change', function () { saved.mandatory = mapping.slice(); renderSummary(); });
        row.append(text, select);
        categoryRows.appendChild(row);
        mapping.push(select.value);
      });
      saved.mandatory = mapping;
      categoriesInput.value = JSON.stringify(saved);
      renderSummary();
    }
    function renderSummary() {
      summary.replaceChildren();
      const mandatoryLines = mandatory.value.split(/\r?\n/).map(function (line) { return line.trim(); }).filter(Boolean);
      const desirableLines = desirable ? desirable.value.split(/\r?\n/).map(function (line) { return line.trim(); }).filter(Boolean) : [];
      const categorySelects = categoryRows.querySelectorAll('select');
      const mandatorySet = new Set(mandatoryLines.map(function (line) { return line.toLocaleLowerCase('es'); }));
      mandatoryLines.forEach(function (line, index) {
        const selected = categorySelects[index]?.value;
        add(line, 'Obligatorio · ' + (selected ? labels[selected] : 'Categoría pendiente de confirmar'));
      });
      desirableLines.filter(function (line) { return !mandatorySet.has(line.toLocaleLowerCase('es')); }).forEach(function (line) { add(line, 'Deseable'); });
      if (experienceClass && experienceClass.value !== 'no_solicitado') {
        add(document.getElementById('id_experiencia_requerida')?.selectedOptions[0]?.textContent || 'Experiencia seleccionada', experienceClass.value === 'obligatorio' ? 'Obligatorio · Experiencia' : 'Deseable · Experiencia');
      }
      if (educationClass && educationClass.value !== 'no_solicitado') {
        add(document.getElementById('id_nivel_educativo')?.selectedOptions[0]?.textContent || 'Formación seleccionada', educationClass.value === 'obligatorio' ? 'Obligatorio · Formación' : 'Deseable · Formación');
      }
      if (!summary.children.length) {
        const empty = document.createElement('li');
        empty.textContent = 'Agregá requisitos para revisar cómo quedarán clasificados.';
        summary.appendChild(empty);
      }
      function add(text, category) {
        const item = document.createElement('li');
        item.textContent = text + ' — ' + category;
        summary.appendChild(item);
      }
    }
    mandatory.addEventListener('input', function () { saved.mandatory = []; render(); });
    if (desirable) desirable.addEventListener('input', renderSummary);
    [experienceClass, educationClass, document.getElementById('id_experiencia_requerida'), document.getElementById('id_nivel_educativo')]
      .filter(Boolean).forEach(function (field) { field.addEventListener('change', renderSummary); });
    const form = mandatory.closest('form');
    if (form) form.addEventListener('submit', function () {
      saved.mandatory = Array.from(categoryRows.querySelectorAll('select')).map(function (select) { return select.value; });
      categoriesInput.value = JSON.stringify(saved);
    });
    render();
  });
})();
