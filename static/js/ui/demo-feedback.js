(() => {
  const mode = document.currentScript.dataset.demoFeedback;
  if (!window.IenUI) return;
  if (mode === 'confirmar') {
    window.IenUI.confirmar({titulo: '¿Eliminar tu CV?', mensaje: 'Vas a tener que volver a subirlo para analizarlo y completar tu perfil.', confirmar: 'Eliminar CV', peligro: true, icono: 'trash'});
  } else if (mode === 'cv-listo') {
    window.IenUI.aviso('exito', 'Tu CV ya está analizado.', 12000, {accion: {url: '/demo/POS-04/', texto: 'Ver mi perfil profesional'}});
  } else {
    const messages = {exito: 'CV eliminado.', error: 'No pudimos completar la acción. Intentá nuevamente.', info: 'Los cambios se guardaron en tu perfil.'};
    if (messages[mode]) window.IenUI.aviso(mode, messages[mode], 12000);
  }
})();
