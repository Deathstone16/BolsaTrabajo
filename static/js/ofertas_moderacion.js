(function() {
  'use strict';

  let modalOfertaId = null;

  function abrirDetalle(pk) {
    modalOfertaId = pk;
    fetch('/moderacion/oferta/' + pk + '/detalle/')
      .then(function(r) { return r.json(); })
      .then(function(data) { renderizarModal(data); });
    document.getElementById('detalle-overlay').classList.remove('hidden');
    document.getElementById('detalle-modal').classList.remove('hidden');
  }

  function cerrarDetalle() {
    document.getElementById('detalle-overlay').classList.add('hidden');
    document.getElementById('detalle-modal').classList.add('hidden');
  }

  function mostrarNotificacion(mensaje, tipo) {
    tipo = tipo || 'exito';
    var colores = tipo === 'exito'
      ? 'bg-green-50 border-green-200 text-green-700'
      : 'bg-red-50 border-red-200 text-red-700';
    var icono = tipo === 'exito' ? 'check-circle' : 'x-circle';

    var notif = document.createElement('div');
    notif.className = 'fixed top-6 right-6 z-[100] flex items-center gap-3 px-5 py-4 border rounded-xl shadow-lg ' + colores + ' transition-all';
    notif.innerHTML = '<i data-lucide="' + icono + '" class="w-5 h-5 flex-shrink-0"></i><span class="text-sm font-medium">' + mensaje + '</span>';
    document.body.appendChild(notif);
    if (typeof lucide !== 'undefined') lucide.createIcons();

    setTimeout(function() {
      notif.style.opacity = '0';
      notif.style.transform = 'translateY(-8px)';
      notif.style.transition = 'opacity 0.3s, transform 0.3s';
      setTimeout(function() { notif.remove(); }, 300);
    }, 3000);
  }

  function renderizarModal(data) {
    modalOfertaId = data.id;

    document.getElementById('modal-titulo').textContent = data.titulo;

    var estadoEl = document.getElementById('modal-estado');
    estadoEl.textContent = data.estado_display;
    estadoEl.className = 'px-3 py-1 rounded-full text-xs font-medium ' + (
      data.estado === 'activa'    ? 'bg-green-100 text-green-700' :
      data.estado === 'pendiente' ? 'bg-yellow-100 text-yellow-700' :
      data.estado === 'rechazada' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
    );

    document.getElementById('modal-empresa-nombre').textContent = data.empresa_nombre;
    document.getElementById('modal-empresa-logo').textContent = data.empresa_nombre.charAt(0).toUpperCase();
    document.getElementById('modal-empresa-link').href = data.empresa_perfil_url || '#';

    document.getElementById('modal-ubicacion').innerHTML = '<i data-lucide="map-pin" class="w-3.5 h-3.5"></i> ' + data.ubicacion;
    document.getElementById('modal-modalidad').innerHTML = '<i data-lucide="building2" class="w-3.5 h-3.5"></i> ' + data.modalidad_display;
    document.getElementById('modal-fecha-cierre').innerHTML = '<i data-lucide="calendar" class="w-3.5 h-3.5"></i> ' + data.fecha_cierre;

    document.getElementById('modal-descripcion').textContent = data.descripcion;

    var habilidadesEl = document.getElementById('modal-habilidades');
    habilidadesEl.innerHTML = data.habilidades_requeridas.split(',').map(function(h) {
      return '<span class="px-3 py-1 bg-muted rounded-full text-sm text-muted-foreground">' + h.trim() + '</span>';
    }).join('');

    document.getElementById('modal-experiencia').textContent = data.experiencia_requerida + ' años';
    document.getElementById('modal-educativo').textContent = data.nivel_educativo_display;
        var botonesEl = document.getElementById('modal-botones');
    if (botonesEl) {
      if (data.estado === 'pendiente') {
        botonesEl.innerHTML =
          '<button id="btn-aprobar" type="button" class="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium"><i data-lucide="check" class="w-4 h-4"></i> Aprobar oferta</button>' +
          '<button id="btn-rechazar" type="button" class="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-destructive text-white rounded-lg hover:bg-destructive/90 transition-colors font-medium"><i data-lucide="x" class="w-4 h-4"></i> Rechazar oferta</button>';
          document.getElementById('btn-aprobar').addEventListener('click', function() {
          if (modalOfertaId) aprobarOferta(modalOfertaId);
        });
        document.getElementById('btn-rechazar').addEventListener('click', function() {
          if (modalOfertaId) rechazarOferta(modalOfertaId);
        });

        } else if (data.estado === 'activa') {
        botonesEl.innerHTML =
          '<button id="btn-finalizar" type="button" class="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-medium"><i data-lucide="archive" class="w-4 h-4"></i> Dar de baja</button>';
          document.getElementById('btn-finalizar').addEventListener('click', function() {
          if (modalOfertaId) finalizarOferta(modalOfertaId);
        });
        } else {
        botonesEl.innerHTML = '<p class="text-sm text-muted-foreground text-center w-full py-3">No hay acciones disponibles.</p>';
      }
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

   function aprobarOferta(pk) {
    confirmarAccion('¿Aprobar esta oferta?', '', 'Aprobar', 'green', function() {
      fetch('/moderacion/oferta/' + pk + '/aprobar/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'X-Requested-With': 'XMLHttpRequest'
        }
      }).then(function(r) { return r.json(); }).then(function(data) {
        cerrarDetalle();
        if (data.success) {
          mostrarNotificacion('Oferta aprobada exitosamente.', 'exito');
          actualizarFila(pk, 'activa', 'Activa', 'bg-green-100 text-green-700');
        } else {
          mostrarNotificacion(data.error || 'No se pudo aprobar la oferta.', 'error');
        }
      });
    });
  }

  function rechazarOferta(pk) {
    confirmarAccion('¿Rechazar esta oferta?', '', 'Rechazar', 'red', function() {
      fetch('/moderacion/oferta/' + pk + '/rechazar/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'X-Requested-With': 'XMLHttpRequest'
        }
      }).then(function(r) { return r.json(); }).then(function(data) {
        cerrarDetalle();
        if (data.success) {
          mostrarNotificacion('Oferta rechazada.', 'error');
          actualizarFila(pk, 'rechazada', 'Rechazada', 'bg-red-100 text-red-700');
        } else {
          mostrarNotificacion(data.error || 'No se pudo rechazar la oferta.', 'error');
        }
      });
    });
  }

  function finalizarOferta(pk) {
    confirmarAccion('¿Dar de baja esta oferta?', '', 'Dar de baja', 'red', function() {
      fetch('/moderacion/oferta/' + pk + '/finalizar/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'X-Requested-With': 'XMLHttpRequest'
        }
      }).then(function(r) { return r.json(); }).then(function(data) {
        cerrarDetalle();
        if (data.success) {
          mostrarNotificacion('Oferta dada de baja correctamente.', 'exito');
          actualizarFila(pk, 'finalizada', 'Finalizada', 'bg-gray-100 text-gray-700');
        } else {
          mostrarNotificacion(data.error || 'No se pudo dar de baja la oferta.', 'error');
        }
      });
    });
  }
    function actualizarFila(pk, estado, textoEstado, claseEstado) {
    var fila = document.querySelector('.fila-oferta[data-oferta-id="' + pk + '"]');
    if (!fila) return;

    fila.querySelectorAll('td')[3].innerHTML = '<span class="px-3 py-1 rounded-full text-xs font-medium ' + claseEstado + '">' + textoEstado + '</span>';

    var celdaAcciones = fila.querySelectorAll('td')[4];
    if (estado === 'pendiente') {
      celdaAcciones.innerHTML =
        '<div class="flex items-center gap-2">' +
          '<button type="button" onclick="aprobarOferta(' + pk + ')" class="btn-accion-rapida p-1.5 rounded-lg border border-green-200 text-green-600 hover:bg-green-50 transition-colors" title="Aprobar"><i data-lucide="check" class="w-4 h-4"></i></button>' +
          '<button type="button" onclick="rechazarOferta(' + pk + ')" class="btn-accion-rapida p-1.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition-colors" title="Rechazar"><i data-lucide="x" class="w-4 h-4"></i></button>' +
        '</div>';
    } else if (estado === 'activa') {
      celdaAcciones.innerHTML =
        '<button type="button" onclick="finalizarOferta(' + pk + ')" class="btn-accion-rapida px-3 py-1.5 rounded-lg border border-orange-200 text-orange-600 hover:bg-orange-50 transition-colors text-xs font-medium" title="Dar de baja"><i data-lucide="archive" class="w-4 h-4 inline"></i> Dar de baja</button>';
    } else {
      celdaAcciones.innerHTML = '<span class="text-xs text-muted-foreground">—</span>';
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }


    function confirmarAccion(mensaje, detalle, textoBoton, colorBoton, callback) {
        var overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black/50 z-[200] flex items-center justify-center p-4';
        overlay.style.animation = 'fadeIn 0.2s ease';

    var modal = document.createElement('div');
    modal.className = 'bg-white rounded-2xl shadow-xl max-w-sm w-full p-6';
    modal.onclick = function(e) { e.stopPropagation(); };

    modal.innerHTML =
      '<div class="text-center mb-4">' +
        '<div class="w-12 h-12 mx-auto mb-3 rounded-full bg-' + (colorBoton === 'red' ? 'red' : 'green') + '-100 flex items-center justify-center">' +
          '<i data-lucide="' + (colorBoton === 'red' ? 'alert-triangle' : 'check-circle') + '" class="w-6 h-6 text-' + (colorBoton === 'red' ? 'red' : 'green') + '-600"></i>' +
        '</div>' +
        '<h3 class="text-lg font-medium mb-1">' + mensaje + '</h3>' +
        (detalle ? '<p class="text-sm text-muted-foreground">' + detalle + '</p>' : '') +
      '</div>' +
      '<div class="flex gap-3">' +
        '<button id="btn-cancelar-confirm" type="button" class="flex-1 px-4 py-2.5 border border-border rounded-lg text-sm font-medium hover:bg-muted transition-colors">Cancelar</button>' +
        '<button id="btn-confirmar-accion" type="button" class="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-' + (colorBoton === 'red' ? 'red' : 'green') + '-600 hover:bg-' + (colorBoton === 'red' ? 'red' : 'green') + '-700 transition-colors">' + textoBoton + '</button>' +
      '</div>';

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    if (typeof lucide !== 'undefined') lucide.createIcons();

    document.getElementById('btn-cancelar-confirm').onclick = function() { overlay.remove(); };
    overlay.onclick = function() { overlay.remove(); };
    document.getElementById('btn-confirmar-accion').onclick = function() {
      overlay.remove();
      callback();
    };
  }


  // ====== Event listeners (al cargar la página) ======

  document.addEventListener('DOMContentLoaded', function() {
    var overlay = document.getElementById('detalle-overlay');
    if (overlay) overlay.addEventListener('click', cerrarDetalle);

    var btnCerrar = document.getElementById('btn-cerrar-modal');
    if (btnCerrar) btnCerrar.addEventListener('click', cerrarDetalle);


    var buscarInput = document.getElementById('buscar');
    if (buscarInput) {
      buscarInput.addEventListener('input', function() {
        var texto = this.value.toLowerCase().trim();
        document.querySelectorAll('.fila-oferta').forEach(function(fila) {
          var puesto = fila.children[1].textContent.toLowerCase();
          var empresa = fila.children[2].textContent.toLowerCase();
          fila.style.display = puesto.includes(texto) || empresa.includes(texto) ? '' : 'none';
        });
      });
    }
  });

  window.abrirDetalle = abrirDetalle;
  window.aprobarOferta = aprobarOferta;
  window.rechazarOferta = rechazarOferta;
  window.finalizarOferta = finalizarOferta;
})();