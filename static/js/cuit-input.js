document.querySelectorAll('[data-cuit-input]').forEach((input) => {
  input.addEventListener('input', () => {
    const cursor = input.selectionStart;
    const value = input.value;
    const cleaned = value.replace(/[^0-9-]/g, '');
    if (cleaned === value) return;

    const cleanedPrefix = value.slice(0, cursor).replace(/[^0-9-]/g, '');
    input.value = cleaned;
    input.setSelectionRange(cleanedPrefix.length, cleanedPrefix.length);
  });
});
