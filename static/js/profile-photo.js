(() => {
  const editors = new Map();
  document.querySelectorAll('[data-profile-photo]').forEach((container) => {
    const input = container.querySelector('[data-photo-input]');
    const preview = container.querySelector('[data-photo-preview]');
    const placeholder = container.querySelector('[data-photo-placeholder]');
    const editor = container.querySelector('[data-photo-editor]');
    const canvas = container.querySelector('[data-photo-canvas]');
    const error = container.querySelector('[data-photo-error]');
    const zoom = container.querySelector('[data-photo-zoom]');
    const horizontal = container.querySelector('[data-photo-x]');
    const vertical = container.querySelector('[data-photo-y]');
    const original = preview.getAttribute('src');
    const form = input.form;
    let source = null;
    let pending = false;
    let version = 0;

    function draw() {
      if (!source) return;
      const scale = Math.max(canvas.width / source.width, canvas.height / source.height) * Number(zoom.value);
      const width = canvas.width / scale;
      const height = canvas.height / scale;
      const x = (source.width - width) * Number(horizontal.value) / 100;
      const y = (source.height - height) * Number(vertical.value) / 100;
      const context = canvas.getContext('2d');
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(source, x, y, width, height, 0, 0, canvas.width, canvas.height);
    }

    function reset() {
      zoom.value = '1';
      horizontal.value = vertical.value = '50';
      draw();
    }

    function showError(message) {
      error.textContent = message;
      error.hidden = !message;
    }

    function restore() {
      source = null;
      pending = false;
      editor.hidden = true;
      if (original) preview.src = original;
      else preview.removeAttribute('src');
      preview.hidden = !original;
      placeholder.hidden = !!original;
    }

    async function loadImage(url, currentVersion) {
      pending = true;
      const image = new Image();
      image.src = url;
      try {
        await image.decode();
        if (version !== currentVersion) return;
        if (Math.max(image.width, image.height) > 4096) {
          throw new Error('La imagen debe tener hasta 4096 píxeles por lado.');
        }
        source = image;
        editor.hidden = false;
        preview.hidden = true;
        placeholder.hidden = true;
        reset();
      } catch (cause) {
        if (version !== currentVersion) return;
        input.value = '';
        restore();
        showError(cause.message.startsWith('La imagen') ? cause.message : 'No pudimos abrir la imagen. Elegí un archivo JPG, PNG o WebP.');
      } finally {
        if (version === currentVersion) pending = false;
      }
    }

    input.addEventListener('change', async () => {
      const currentVersion = ++version;
      showError('');
      restore();
      const file = input.files[0];
      if (!file) return;
      const maxMB = Number(container.dataset.maxMb || 2);
      if (file.size > maxMB * 1024 * 1024 || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        input.value = '';
        showError(`Elegí una imagen JPG, PNG o WebP de hasta ${maxMB} MB.`);
        return;
      }
      const url = URL.createObjectURL(file);
      await loadImage(url, currentVersion);
      URL.revokeObjectURL(url);
    });
    [zoom, horizontal, vertical].forEach((control) => control.addEventListener('input', draw));
    container.querySelector('[data-photo-reset]').addEventListener('click', reset);

    const backgroundButton = container.querySelector('[data-cover-background]');
    if (backgroundButton) backgroundButton.addEventListener('click', () => {
      const background = document.createElement('canvas');
      background.width = canvas.width;
      background.height = canvas.height;
      const context = background.getContext('2d');
      context.fillStyle = container.querySelector('[data-cover-color]').value;
      context.fillRect(0, 0, background.width, background.height);
      input.value = '';
      showError('');
      loadImage(background.toDataURL('image/png'), ++version);
    });

    if (!editors.has(form)) editors.set(form, []);
    editors.get(form).push(async () => {
      if (pending) throw new Error('Esperá a que termine de cargar la imagen.');
      if (!source) return;
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', 0.92));
      if (!blob) throw new Error('No pudimos preparar la imagen. Volvé a seleccionarla.');
      const transfer = new DataTransfer();
      transfer.items.add(new File([blob], `${input.name}.webp`, {type: 'image/webp'}));
      input.files = transfer.files;
    });
  });

  editors.forEach((prepareImages, form) => {
    let ready = false;
    let saving = false;
    form.addEventListener('submit', async (event) => {
      if (ready) { ready = false; return; }
      event.preventDefault();
      if (saving) return;
      saving = true;
      try {
        await Promise.all(prepareImages.map((prepare) => prepare()));
        ready = true;
        form.requestSubmit(event.submitter || undefined);
      } catch (error) {
        const message = form.querySelector('[data-photo-error]');
        message.textContent = error.message;
        message.hidden = false;
        message.scrollIntoView({block: 'center'});
      } finally {
        saving = false;
      }
    });
  });
})();
