(() => {
  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    const input = document.getElementById(button.getAttribute('aria-controls'));
    if (!(input instanceof HTMLInputElement) || input.type !== 'password') return;

    const label = button.dataset.passwordLabel || 'contraseña';
    const showIcon = button.querySelector('[data-password-show-icon]');
    const hideIcon = button.querySelector('[data-password-hide-icon]');

    button.addEventListener('click', () => {
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.setAttribute('aria-pressed', String(visible));
      button.setAttribute('aria-label', `${visible ? 'Ocultar' : 'Mostrar'} ${label}`);
      button.title = button.getAttribute('aria-label');
      showIcon.hidden = visible;
      hideIcon.hidden = !visible;
    });

    button.hidden = false;
  });
})();
