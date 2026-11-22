(function () {
  'use strict';
  async function json(url, options, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs || 30000);
    try {
      const response = await fetch(url, Object.assign({}, options, {signal: controller.signal}));
      if (response.status >= 500) {
        const error = new Error('Servicio no disponible');
        error.code = response.status === 504 ? 'timeout' : 'unavailable';
        throw error;
      }
      if (!response.headers.get('Content-Type')?.includes('application/json')) {
        const error = new Error('Respuesta no válida');
        error.code = response.redirected ? 'session' : 'invalid';
        throw error;
      }
      return await response.json();
    } catch (error) {
      if (controller.signal.aborted) {
        const timeoutError = new Error('Tiempo de espera agotado', {cause: error});
        timeoutError.code = 'timeout';
        throw timeoutError;
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }
  function message(error) {
    if (error?.code === 'timeout') return 'La respuesta tardó demasiado. Revisá el estado antes de volver a enviar la operación.';
    if (error?.code === 'session') return 'Tu sesión puede haber vencido. Volvé a ingresar para continuar.';
    if (error?.code === 'unavailable') return 'El servicio no está disponible. Intentá nuevamente en unos minutos.';
    if (error?.code === 'invalid') return 'No pudimos confirmar la respuesta. Revisá el estado antes de volver a intentarlo.';
    return 'No pudimos conectarnos. Revisá tu conexión y volvé a intentar.';
  }
  window.IenHTTP = {json, message};
})();
