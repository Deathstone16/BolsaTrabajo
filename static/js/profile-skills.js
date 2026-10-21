document.querySelectorAll('[data-skill-picker]').forEach((root) => {
  const hidden = root.querySelector('input[type="hidden"]');
  const entry = root.querySelector('[role="combobox"]');
  const options = root.querySelector('[role="listbox"]');
  const tags = root.querySelector('[data-skill-tags]');
  const message = root.querySelector('[data-skill-message]');
  const addButton = root.querySelector('[data-skill-add]');
  const catalog = [...(window.HABILIDADES_DURAS || []), ...(window.HABILIDADES_BLANDAS || [])];
  const normalize = (text) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  let selected = [...new Set(hidden.value.split(',').map(s => s.trim()).filter(Boolean))];
  let suggestions = [];
  let active = -1;
  const close = () => { options.hidden = true; entry.setAttribute('aria-expanded', 'false'); entry.removeAttribute('aria-activedescendant'); active = -1; };
  const renderTags = () => {
    tags.replaceChildren();
    selected.forEach((name, index) => {
      const chip = document.createElement('span'); chip.className = 'chip'; chip.append(document.createTextNode(name));
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'skill-picker-remove'; remove.textContent = '×'; remove.setAttribute('aria-label', `Quitar ${name}`);
      remove.addEventListener('click', () => { selected.splice(index, 1); renderTags(); entry.focus(); message.textContent = `Se quitó ${name}.`; });
      chip.append(remove); tags.append(chip);
    });
    hidden.value = selected.join(', ');
  };
  const add = (raw) => {
    const name = raw.trim();
    if (!name) { message.textContent = 'Escribí una habilidad para agregarla.'; return; }
    if (name.includes(',')) { message.textContent = 'Agregá una habilidad por vez, sin comas.'; return; }
    if (selected.some(s => normalize(s) === normalize(name))) { message.textContent = 'Esa habilidad ya está agregada.'; return; }
    const nextValue = [...selected, name].join(', ');
    if (nextValue.length > 2000) { message.textContent = 'Alcanzaste el límite de habilidades del perfil.'; return; }
    selected.push(name); renderTags(); entry.value = ''; close(); entry.focus(); message.textContent = `Se agregó ${name}.`;
  };
  const highlight = () => {
    [...options.children].forEach((el, index) => el.setAttribute('aria-selected', String(index === active)));
    if (active >= 0) entry.setAttribute('aria-activedescendant', options.children[active].id);
    else entry.removeAttribute('aria-activedescendant');
  };
  entry.addEventListener('input', () => {
    message.textContent = ''; active = -1; options.replaceChildren();
    const query = normalize(entry.value.trim());
    suggestions = query ? catalog.filter(s => normalize(s).includes(query) && !selected.some(name => normalize(name) === normalize(s))).slice(0, 8) : [];
    suggestions.forEach((name, index) => {
      const li = document.createElement('li'); li.id = `${options.id}-${index}`; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false'); li.textContent = name;
      li.addEventListener('mousedown', e => e.preventDefault()); li.addEventListener('click', () => add(name)); options.append(li);
    });
    options.hidden = suggestions.length === 0; entry.setAttribute('aria-expanded', String(!options.hidden));
  });
  entry.addEventListener('keydown', (event) => {
    if (event.key === ',') { event.preventDefault(); message.textContent = 'Agregá una habilidad por vez con Enter o Agregar.'; }
    else if (event.key === 'Enter') { event.preventDefault(); add(!options.hidden && suggestions.length ? suggestions[active >= 0 ? active : 0] : entry.value); }
    else if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && !options.hidden) { event.preventDefault(); active = active < 0 ? (event.key === 'ArrowDown' ? 0 : suggestions.length - 1) : (active + (event.key === 'ArrowDown' ? 1 : -1) + suggestions.length) % suggestions.length; highlight(); }
    else if (event.key === 'Escape') close();
  });
  addButton.addEventListener('click', () => add(entry.value));
  document.addEventListener('click', event => { if (!root.contains(event.target)) close(); });
  renderTags();
});
