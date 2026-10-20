document.querySelectorAll('[data-character-limit]').forEach((input, index) => {
  const limit = Number(input.dataset.characterLimit);
  if (!Number.isFinite(limit) || limit < 1) return;
  const counter = document.createElement('p');
  counter.id = `character-limit-${index}`;
  counter.className = 'description-counter';
  counter.setAttribute('aria-live', 'polite');
  input.insertAdjacentElement('afterend', counter);
  const describedBy = input.getAttribute('aria-describedby') || '';
  input.setAttribute('aria-describedby', `${describedBy} ${counter.id}`.trim());
  const update = () => {
    const count = [...input.value].length;
    const over = count > limit;
    counter.textContent = `${count} / ${limit} caracteres${over ? ' · Superaste el límite' : ''}`;
    counter.classList.toggle('is-over-limit', over);
    input.classList.toggle('character-limit-exceeded', over);
    input.setCustomValidity(over ? `La descripción admite hasta ${limit} caracteres. Acortá el texto para continuar.` : '');
    if (over) input.setAttribute('aria-invalid', 'true');
    else input.removeAttribute('aria-invalid');
  };
  input.addEventListener('input', update);
  update();
});
