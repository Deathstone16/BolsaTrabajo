(function () {
  'use strict';
  const splitItems = (text) => text.split(/[,;\r\n]+/).map((item) => item.replace(/\s+/g, ' ').trim()).filter(Boolean);
  function separateKnown(text, vocabulary) {
    if (text.length > 100) return [text];
    const words = vocabulary.filter((word) => !/\s/.test(word) && word.length > 1);
    if (vocabulary.some((word) => word.toLowerCase() === text.toLowerCase())) return [text];
    const memo = new Map();
    function find(rest) {
      if (!rest) return [];
      if (memo.has(rest)) return memo.get(rest);
      for (const word of words) {
        if (!rest.startsWith(word.toLowerCase())) continue;
        const tail = find(rest.slice(word.length));
        if (tail) { const result = [word, ...tail]; memo.set(rest, result); return result; }
      }
      memo.set(rest, null);
      return null;
    }
    return find(text.toLowerCase()) || [text];
  }
  if (typeof module !== 'undefined') module.exports = {splitItems, separateKnown};
  if (typeof document === 'undefined') return;
  const root = document.getElementById('requirements-editor');
  if (!root) return;
  const form = root.closest('form');
  const mappingInput = form.querySelector('[name="categorias_requisitos"]');
  const labels = {
    technical_skills: 'Habilidad técnica',
    soft_skills: 'Habilidad blanda',
    experience: 'Experiencia', education: 'Formación', languages: 'Idioma',
    logistics: 'Disponibilidad o modalidad',
  };
  const vocabulary = [...(window.HABILIDADES_DURAS || []), ...(window.HABILIDADES_BLANDAS || []), 'Excel'];
  let saved = {};
  try { saved = JSON.parse(mappingInput.value || '{}'); } catch (_) { /* Se valida en el servidor. */ }
  const lists = [];
  function suggestCategory(text) {
    const value = text.toLocaleLowerCase('es');
    if ((window.HABILIDADES_BLANDAS || []).some((word) => word.toLocaleLowerCase('es') === value)) return 'soft_skills';
    if (/idioma|ingl[eé]s|portugu[eé]s|franc[eé]s/.test(value)) return 'languages';
    if (/experiencia|a[nñ]os|trayectoria/.test(value)) return 'experience';
    if (/terciario|secundario|t[ií]tulo|universitario/.test(value)) return 'education';
    if (/disponibilidad|licencia|residir|viajar|turno/.test(value)) return 'logistics';
    return 'technical_skills';
  }
  function sync() {
    const mapping = {};
    lists.forEach((list) => {
      list.source.value = list.items.map((item) => item.text).join('\n');
      mapping[list.kind] = list.items.map((item) => item.category);
      list.entry.required = list.kind === 'mandatory' && !list.items.length;
      list.entry.dispatchEvent(new Event('input', {bubbles: true}));
    });
    mappingInput.value = JSON.stringify(mapping);
  }
  function showError(list, text) {
    list.error.textContent = text;
    list.error.hidden = !text;
  }
  function render(list) {
    list.rows.replaceChildren();
    list.items.forEach((item, index) => {
      const row = document.createElement('li');
      row.className = 'ien-requirement-item';
      const text = document.createElement('span');
      text.textContent = item.text;
      const select = document.createElement('select');
      select.className = 'input-ien';
      select.setAttribute('aria-label', `Tipo de requisito: ${item.text}`);
      Object.entries(labels).forEach(([value, label]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.append(option);
      });
      select.value = item.category;
      select.addEventListener('change', () => { item.category = select.value; sync(); });
      const actions = document.createElement('div');
      actions.className = 'ien-requirement-item-actions';
      const move = document.createElement('button');
      move.type = 'button';
      move.textContent = list.kind === 'mandatory' ? 'Pasar a deseable' : 'Pasar a obligatorio';
      move.setAttribute('aria-label', `${move.textContent}: ${item.text}`);
      move.addEventListener('click', () => {
        const other = lists.find((candidate) => candidate !== list);
        if (other.items.length >= 30) { showError(list, 'La otra lista ya tiene 30 elementos.'); return; }
        list.items.splice(index, 1);
        other.items.push(item);
        render(list); render(other); sync();
      });
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = 'Quitar';
      remove.setAttribute('aria-label', `Quitar ${item.text}`);
      remove.addEventListener('click', () => { list.items.splice(index, 1); render(list); sync(); });
      actions.append(move, remove);
      row.append(text, select, actions);
      list.rows.append(row);
    });
  }
  function commit(list, acceptSuggestion = false) {
    let values = splitItems(list.entry.value);
    if (!values.length) return true;
    const separated = values.flatMap((value) => separateKnown(value, vocabulary));
    if (!acceptSuggestion && separated.length !== values.length) {
      list.suggestion.replaceChildren();
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn-ghost';
      button.textContent = `Separar en: ${separated.join(', ')}`;
      button.addEventListener('click', () => commit(list, true));
      list.suggestion.append(button);
      list.suggestion.hidden = false;
      showError(list, 'Parece que hay habilidades pegadas. Confirmá la separación o corregí el texto con comas.');
      return false;
    }
    if (acceptSuggestion) values = separated;
    if (values.some((value) => value.length < 2 || value.length > 100)) {
      showError(list, 'Cada elemento debe tener entre 2 y 100 caracteres.'); return false;
    }
    const existing = new Set(lists.flatMap((candidate) => candidate.items.map((item) => item.text.toLowerCase())));
    const unique = [];
    values.forEach((value) => {
      if (!existing.has(value.toLowerCase())) { existing.add(value.toLowerCase()); unique.push(value); }
    });
    if (unique.length + list.items.length > 30) { showError(list, 'Podés agregar hasta 30 elementos por lista.'); return false; }
    list.items.push(...unique.map((text) => ({text, category: suggestCategory(text)})));
    list.entry.value = '';
    list.suggestion.hidden = true;
    showError(list, unique.length < values.length ? 'Los elementos repetidos ya estaban cargados; no los agregamos otra vez.' : '');
    render(list); sync(); list.entry.focus();
    return true;
  }
  root.querySelectorAll('[data-requirement-list]').forEach((section) => {
    const kind = section.dataset.requirementList;
    const source = section.querySelector('textarea');
    const list = {
      kind, source,
      entry: section.querySelector('[data-requirement-entry]'),
      rows: section.querySelector('[data-requirement-items]'),
      error: section.querySelector('[data-requirement-error]'),
      suggestion: section.querySelector('[data-requirement-suggestion]'),
      items: splitItems(source.value).map((text, index) => ({text, category: saved[kind]?.[index] || 'technical_skills'})),
    };
    lists.push(list);
    source.required = false;
    section.querySelector('[data-requirement-source]').hidden = true;
    section.querySelector('[data-requirement-enhanced]').hidden = false;
    section.querySelector('[data-requirement-add]').addEventListener('click', () => commit(list));
    list.entry.addEventListener('keydown', (event) => {
      if (event.isComposing) return;
      if (['Enter', ',', ';'].includes(event.key)) { event.preventDefault(); commit(list); }
    });
    list.entry.addEventListener('paste', (event) => {
      const text = event.clipboardData.getData('text');
      if (!/[,;\r\n]/.test(text) || list.entry.value) return;
      event.preventDefault(); list.entry.value = text; commit(list);
    });
    render(list);
  });
  sync();
  const educationClass = form.querySelector('[name="educacion_clasificacion"]');
  const educationLevel = form.querySelector('[name="nivel_educativo"]');
  if (educationClass && educationLevel) {
    function updateEducation() {
      educationLevel.required = educationClass.value !== 'no_solicitado';
      educationLevel.dispatchEvent(new Event('input', {bubbles: true}));
    }
    educationClass.addEventListener('change', updateEducation);
    updateEducation();
  }
  form.addEventListener('submit', (event) => {
    for (const list of lists) {
      if (!commit(list)) { event.preventDefault(); list.entry.focus(); return; }
    }
    sync();
  });
})();
