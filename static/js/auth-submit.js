// Keep native browser navigation and block only duplicate submissions.
(() => {
  document.querySelectorAll('[data-auth-form]').forEach(form => {
    const buttons = [...form.querySelectorAll('button[type="submit"]')];
    const original = buttons.map(button => button.innerHTML);
    let pending = false;
    form.addEventListener('submit', event => {
      if (pending) { event.preventDefault(); return; }
      if (event.defaultPrevented) return;
      pending = true;
      form.setAttribute('aria-busy', 'true');
      buttons.forEach(button => { button.disabled = true; button.textContent = form.dataset.submitLabel || 'Enviando…'; });
    });
    window.addEventListener('pageshow', () => {
      pending = false;
      form.removeAttribute('aria-busy');
      buttons.forEach((button, index) => { button.disabled = false; button.innerHTML = original[index]; });
    });
  });
})();
