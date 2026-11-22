(() => {
  const form = document.getElementById('form-cv-upload');
  if (!form) return;
  const input = form.querySelector('#cv-input');
  const picker = form.querySelector('[data-cv-file-picker]');
  const native = form.querySelector('[data-cv-native-upload]');
  if (!input || !picker || !native) return;
  picker.addEventListener('click', () => input.click());
  input.required = false;
  native.hidden = true;
  picker.hidden = false;
})();
