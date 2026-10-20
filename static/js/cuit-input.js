document.querySelectorAll('[data-cuit-input]').forEach((input) => {
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
    const cursor = input.selectionStart;
    const value = input.value;
    const cleaned = value.replace(/[^0-9-]/g, '');
    if (cleaned === value) return;

    const cleanedPrefix = value.slice(0, cursor).replace(/[^0-9-]/g, '');
    input.value = cleaned;
    input.setSelectionRange(cleanedPrefix.length, cleanedPrefix.length);
  });
});
