document.querySelectorAll('[data-cuit-input]').forEach((input) => {
  function formatCuit() {
    const raw = input.value;
    const cursor = input.selectionStart ?? raw.length;
    const digits = raw.replace(/[^0-9]/g, '').slice(0, 11);
    const formatted = [digits.slice(0, 2), digits.slice(2, 10), digits.slice(10)]
      .filter(Boolean).join('-');
    if (raw === formatted) return;

    let remaining = raw.slice(0, cursor).replace(/[^0-9]/g, '').length;
    let position = 0;
    while (remaining > 0 && position < formatted.length) {
      if (formatted[position] !== '-') remaining--;
      position++;
    }
    input.value = formatted;
    input.setSelectionRange(position, position);
  }

  input.removeAttribute('maxlength');
  formatCuit();

  // Skip separators when deleting in the middle of the CUIT.
  input.addEventListener('keydown', (event) => {
    const position = input.selectionStart;
    if (position === null || position !== input.selectionEnd) return;
    if (event.key === 'Backspace' && input.value[position - 1] === '-') {
      input.setSelectionRange(position - 1, position - 1);
    } else if (event.key === 'Delete' && input.value[position] === '-') {
      input.setSelectionRange(position + 1, position + 1);
    }
  });

  input.addEventListener('invalid', () => {
    if (!input.value) {
      input.setCustomValidity('Ingresá el CUIT de tu empresa.');
    } else if (input.value.replace(/\D/g, '').length !== 11) {
      input.setCustomValidity('El CUIT debe tener 11 números. Revisá que esté completo.');
    } else if (input.validity.patternMismatch) {
      input.setCustomValidity('Escribí el CUIT con o sin guiones, con el formato XX-XXXXXXXX-X.');
    }
  });
  input.addEventListener('input', () => {
    input.setCustomValidity('');
    formatCuit();
  });
});
