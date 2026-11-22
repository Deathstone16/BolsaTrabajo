document.querySelectorAll('[data-company-validation], [data-required-validation]').forEach((form) => {
  form.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="file"]), select, textarea').forEach((input) => {
    if (!input.id) input.id = `validation-${input.name}`;
    const label = input.labels[0];
    let marker;
    if (label) {
      marker = document.createElement('span');
      marker.className = 'ien-required-marker';
      marker.textContent = ' *';
      marker.setAttribute('aria-hidden', 'true');
      label.append(marker);
    }

    const message = document.createElement('p');
    message.id = `${input.id}-required-message`;
    message.className = 'ien-required-message';
    message.setAttribute('aria-live', 'polite');
    input.insertAdjacentElement('afterend', message);
    const descriptions = input.getAttribute('aria-describedby');
    input.setAttribute('aria-describedby', [descriptions, message.id].filter(Boolean).join(' '));
    let serverInvalid = input.getAttribute('aria-invalid') === 'true';
    let touched = false;

    function update() {
      if (marker) marker.hidden = !input.required;
      const missing = input.required && !input.value.trim();
      const invalid = missing || serverInvalid || (touched && !input.validity.valid);
      input.classList.toggle('ien-field-invalid', invalid);
      input.setAttribute('aria-invalid', String(invalid));
      message.textContent = missing ? 'Completá este campo obligatorio.' : '';
      message.hidden = !missing;
    }

    input.addEventListener('input', () => {
      serverInvalid = false;
      update();
    });
    input.addEventListener('change', () => {
      serverInvalid = false;
      update();
    });
    ['blur', 'invalid'].forEach((event) => input.addEventListener(event, () => {
      touched = true;
      update();
    }));
    update();
  });
});
