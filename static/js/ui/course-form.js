/* Course controls keep Django's field names and submission format. */
document.querySelectorAll('[data-course-skills]').forEach((root) => {
  const source = root.querySelector('[data-skills-source] select');
  const choice = root.querySelector('[data-skill-choice]');
  const list = root.querySelector('[data-skills-selected]');
  const add = root.querySelector('[data-skill-add]');
  const status = root.querySelector('[data-skills-status]');
  if (!source || !choice || !list || !add) return;
  const options = Array.from(source.options).filter((option) => option.value !== '');
  function render() {
    choice.replaceChildren(new Option('Elegir habilidad', ''));
    list.replaceChildren();
    options.forEach((option) => {
      if (!option.selected) {
        choice.add(new Option(option.text, option.value));
        return;
      }
      const item = document.createElement('li');
      const name = document.createElement('span');
      name.textContent = option.text;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Quitar ${option.text}`);
      remove.addEventListener('click', () => {
        option.selected = false;
        source.dispatchEvent(new Event('change', { bubbles: true }));
        render();
        status.textContent = `${option.text}: quitada.`;
        choice.focus();
      });
      item.append(name, remove);
      list.append(item);
    });
    root.querySelector('[data-skills-empty]').hidden = list.children.length > 0;
    choice.disabled = options.every((option) => option.selected);
    add.disabled = true;
  }
  choice.addEventListener('change', () => { add.disabled = choice.value === ''; });
  add.addEventListener('click', () => {
    const option = options.find((item) => item.value === choice.value);
    if (!option) return;
    option.selected = true;
    source.dispatchEvent(new Event('change', { bubbles: true }));
    render();
    status.textContent = `${option.text}: agregada.`;
    choice.focus();
  });
  choice.id = `${source.id}-choice`;
  root.querySelector('[data-skills-source]').hidden = true;
  root.querySelector('[data-skills-controls]').hidden = false;
  render();
});

document.querySelectorAll('[data-course-image]').forEach((root) => {
  const input = root.querySelector('input[type="file"]');
  const preview = root.querySelector('[data-image-preview]');
  const clear = root.querySelector('input[type="checkbox"]');
  const initial = preview.src;
  const fallback = root.dataset.defaultImage;
  let objectUrl;
  function release() { if (objectUrl) URL.revokeObjectURL(objectUrl); }
  input.addEventListener('change', () => {
    release();
    const file = input.files[0];
    preview.src = file ? (objectUrl = URL.createObjectURL(file)) : (clear?.checked ? fallback : initial);
    root.querySelector('[data-image-name]').textContent = file ? file.name : 'Portada del curso';
    if (file && clear) clear.checked = false;
  });
  clear?.addEventListener('change', () => {
    release();
    input.value = '';
    preview.src = clear.checked ? fallback : initial;
    root.querySelector('[data-image-name]').textContent = clear.checked ? 'Portada predeterminada' : 'Portada del curso';
  });
});

// Give the day group and hour range the same inline feedback as other fields.
document.querySelectorAll('[data-course-schedule]').forEach((root) => {
  const days = Array.from(root.querySelectorAll('input[type="checkbox"]'));
  const [start, end] = root.querySelectorAll('input[type="time"]');
  const error = root.querySelector('[data-schedule-days-error]');
  const group = root.querySelector('fieldset');
  let attempted = false;
  function validate() {
    const missing = !days.some((day) => day.checked);
    error.hidden = !attempted || !missing;
    group.setAttribute('aria-invalid', String(attempted && missing));
    const badRange = start.value && end.value && end.value <= start.value;
    end.setCustomValidity(badRange ? 'La hora de fin debe ser posterior a la de inicio.' : '');
    return !missing && !badRange;
  }
  root.addEventListener('change', validate);
  root.closest('form').addEventListener('submit', (event) => {
    attempted = true;
    if (!validate()) {
      event.preventDefault();
      if (!days.some((day) => day.checked)) days[0].focus();
    }
  });
});
