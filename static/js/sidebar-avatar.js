// La foto pertenece a la barra compartida y funciona desde cualquier sección.
(() => {
  function initSidebarAvatar() {
    document.querySelectorAll('[data-sidebar-avatar]').forEach((form) => {
      if (form.dataset.avatarReady) return;
      const input = form.querySelector('input[name="foto"]');
      const picker = form.querySelector('[data-avatar-picker]');
      const fields = form.querySelector('[data-avatar-fields]');
      const feedback = form.querySelector('[data-sidebar-avatar-feedback]');
      if (!input || !picker || !fields || typeof window.fetch !== 'function') return;
      form.dataset.avatarReady = 'true';
      fields.hidden = true;
      picker.disabled = false;
      picker.addEventListener('click', () => input.click());
      input.addEventListener('change', async () => {
        if (!input.files.length) return;
        picker.disabled = true;
        picker.setAttribute('aria-busy', 'true');
        feedback.hidden = true;
        try {
          const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'},
          });
          const result = await response.json();
          if (!response.ok || !result.success) throw new Error(result.mensaje || 'No se pudo actualizar la foto.');
          if (window.IenUI) window.IenUI.avisoTrasRecarga('exito', result.mensaje);
          location.reload();
        } catch (error) {
          feedback.textContent = error.message || 'No se pudo actualizar la foto. Intentá nuevamente.';
          feedback.hidden = false;
          input.value = '';
        } finally {
          picker.disabled = false;
          picker.removeAttribute('aria-busy');
        }
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initSidebarAvatar);
  else initSidebarAvatar();
})();
