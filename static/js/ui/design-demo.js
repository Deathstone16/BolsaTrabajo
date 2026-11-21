// Local-only interactions for the design demo; never call application services.
document.addEventListener('click', function (event) {
  const save = event.target.closest('[data-save]');
  if (!save) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const wasSaved = save.dataset.saveOn === 'true';
  save.dataset.saveOn = String(!wasSaved);
  save.setAttribute('aria-pressed', String(!wasSaved));
  const label = save.querySelector('[data-save-label]');
  if (label) label.textContent = wasSaved ? 'Guardar' : 'Guardada';
  const card = save.closest('[data-save-card]');
  if (card && wasSaved) {
    card.remove();
    const count = document.querySelectorAll('[data-save-card]').length;
    const counter = document.querySelector('[data-save-count]');
    if (counter) counter.textContent = `${count} ofertas guardadas`;
    if (!count) document.getElementById('favoritos-vacio')?.classList.remove('hidden');
  }
}, true);
