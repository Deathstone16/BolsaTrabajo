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
    const picker = container.querySelector('[data-photo-picker]');
    const pickerLabel = container.querySelector('[data-photo-picker-label]');
    const pickerAction = container.querySelector('[data-photo-picker-action]');
    const photoStatus = container.querySelector('[data-photo-status]');
    const initialPickerLabel = pickerLabel ? pickerLabel.textContent : '';
    const initialPhotoStatus = photoStatus ? photoStatus.textContent : '';
    const original = preview.getAttribute('src');
    const form = input.form;
    let source = null;
    let pending = false;
    let version = 0;
    let positionX = 50;
    let positionY = 50;
    let drag = null;

    const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));

    function cropMetrics() {
      const scale = Math.max(canvas.width / source.width, canvas.height / source.height) * Number(zoom.value);
      const width = canvas.width / scale;
      const height = canvas.height / scale;
      return {
        width,
        height,
        x: (source.width - width) * positionX / 100,
        y: (source.height - height) * positionY / 100,
      };
    }

    function draw() {
      if (!source) return;
      const {x, y, width, height} = cropMetrics();
      const context = canvas.getContext('2d');
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(source, x, y, width, height, 0, 0, canvas.width, canvas.height);
    }

    function reset() {
      zoom.value = '1';
      positionX = positionY = 50;
      draw();
    }

    function startDrag(event) {
      if (!source || (event.button !== undefined && event.button !== 0)) return;
      event.preventDefault();
      const metrics = cropMetrics();
      drag = {
        pointerId: event.pointerId,
        clientX: event.clientX,
        clientY: event.clientY,
        cropX: metrics.x,
        cropY: metrics.y,
        cropWidth: metrics.width,
        cropHeight: metrics.height,
      };
      if (canvas.setPointerCapture && event.pointerId !== undefined) canvas.setPointerCapture(event.pointerId);
      if (canvas.classList) canvas.classList.add('is-dragging');
    }

    function moveDrag(event) {
      if (!drag || (drag.pointerId !== undefined && event.pointerId !== drag.pointerId)) return;
      event.preventDefault();
      const bounds = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : {width: canvas.width, height: canvas.height};
      const renderedWidth = bounds.width || canvas.width;
      const renderedHeight = bounds.height || canvas.height;
      const maxX = Math.max(0, source.width - drag.cropWidth);
      const maxY = Math.max(0, source.height - drag.cropHeight);
      const cropX = clamp(drag.cropX - (event.clientX - drag.clientX) * drag.cropWidth / renderedWidth, 0, maxX);
      const cropY = clamp(drag.cropY - (event.clientY - drag.clientY) * drag.cropHeight / renderedHeight, 0, maxY);
      positionX = maxX ? cropX / maxX * 100 : 50;
      positionY = maxY ? cropY / maxY * 100 : 50;
      draw();
    }

    function finishDrag(event) {
      if (!drag || (drag.pointerId !== undefined && event.pointerId !== drag.pointerId)) return;
      if (canvas.releasePointerCapture && event.pointerId !== undefined) canvas.releasePointerCapture(event.pointerId);
      drag = null;
      if (canvas.classList) canvas.classList.remove('is-dragging');
    }

    function moveWithKeyboard(event) {
      if (!source || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const step = event.shiftKey ? 10 : 2;
      if (event.key === 'ArrowLeft') positionX = clamp(positionX + step, 0, 100);
      if (event.key === 'ArrowRight') positionX = clamp(positionX - step, 0, 100);
      if (event.key === 'ArrowUp') positionY = clamp(positionY + step, 0, 100);
      if (event.key === 'ArrowDown') positionY = clamp(positionY - step, 0, 100);
      draw();
    }

    function showError(message) {
      error.textContent = message;
      error.hidden = !message;
    }

    function setPickerState(state, fileName = '') {
      if (!picker) return;
      if (picker.classList) picker.classList.toggle('has-file', state === 'ready');
      if (pickerLabel) pickerLabel.textContent = fileName || initialPickerLabel;
      if (pickerAction) pickerAction.textContent = state === 'ready' ? 'Listo' : state === 'loading' ? 'Cargando…' : 'Seleccionar';
      if (photoStatus) {
        photoStatus.textContent = state === 'ready' ? 'Imagen lista. Arrastrala para ajustar el encuadre.' : state === 'loading' ? 'Cargando la imagen seleccionada…' : initialPhotoStatus;
        if (photoStatus.classList) photoStatus.classList.toggle('is-ready', state === 'ready');
      }
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
        setPickerState('idle');
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
      if (!file) { setPickerState('idle'); return; }
      const maxMB = Number(container.dataset.maxMb || 2);
      if (file.size > maxMB * 1024 * 1024 || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        input.value = '';
        setPickerState('idle');
        showError(`Elegí una imagen JPG, PNG o WebP de hasta ${maxMB} MB.`);
        return;
      }
      setPickerState('loading', file.name);
      const url = URL.createObjectURL(file);
      await loadImage(url, currentVersion);
      URL.revokeObjectURL(url);
      if (source && version === currentVersion) setPickerState('ready', file.name);
    });
    zoom.addEventListener('input', draw);
    canvas.addEventListener('pointerdown', startDrag);
    canvas.addEventListener('pointermove', moveDrag);
    canvas.addEventListener('pointerup', finishDrag);
    canvas.addEventListener('pointercancel', finishDrag);
    canvas.addEventListener('keydown', moveWithKeyboard);
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
      const backgroundVersion = ++version;
      setPickerState('loading', 'Portada de color');
      loadImage(background.toDataURL('image/png'), backgroundVersion).then(() => {
        if (source && version === backgroundVersion) setPickerState('ready', 'Portada de color');
      });
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
