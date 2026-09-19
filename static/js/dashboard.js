/*
 * Las plantillas del rediseno usan <span data-icon> + ien-ui.js en vez de
 * <i data-lucide> + lucide. Este helper dibuja los iconos con el sistema que
 * este disponible, para que dashboard.js sirva en las dos bases.
 */
// Notificacion flotante del sitio (IenUI.aviso); si no cargo, el alert de siempre.
function avisar(tipo, mensaje) {
  if (window.IenUI && typeof window.IenUI.aviso === 'function') window.IenUI.aviso(tipo, mensaje);
  else alert(mensaje);
}

function dibujarIconos(scope) {
  if (window.IenUI && window.IenUI.injectIcons) window.IenUI.injectIcons(scope || document);
  else if (typeof lucide !== 'undefined') lucide.createIcons();
}

function getCSRFToken() {
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    if (cookie.trim().startsWith('csrftoken=')) {
      return cookie.trim().substring('csrftoken='.length);
    }
  }
  return '';
}
const csrfToken = getCSRFToken();

function cambiarTab(nombre) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.getElementById('tab-' + nombre).classList.remove('hidden');
  document.querySelectorAll('.tab-link').forEach(el => {
    el.classList.remove('border-primary', 'text-primary');
    el.classList.add('border-transparent', 'text-muted-foreground');
  });
  const activeLink = document.querySelector(`.tab-link[data-tab="${nombre}"]`);
  if (activeLink) {
    activeLink.classList.remove('border-transparent', 'text-muted-foreground');
    activeLink.classList.add('border-primary', 'text-primary');
  }
  window.location.hash = nombre;
}

document.addEventListener('DOMContentLoaded', function() {
  const tab = window.location.hash.replace('#', '') || 'ofertas';
  cambiarTab(tab);
});

function openCreateModal() {
  document.getElementById('modal-title').textContent = 'Nueva oferta laboral';
  document.getElementById('oferta-form').reset();
  document.getElementById('oferta-form').action = window.URLS.crearOferta;
  ocultarErroresModal();
  inicializarTags();
  mostrarModalOferta();
}

async function openEditModal(pk) {
  document.getElementById('modal-title').textContent = 'Editar oferta laboral';
  document.getElementById('oferta-form').action = '/ofertas/editar/' + pk + '/';
  ocultarErroresModal();

  const response = await fetch('/ofertas/datos/' + pk + '/');
  const data = await response.json();

  if (data.error) {
    avisar('error', data.error);
    return;
  }

  document.querySelector('[name="titulo"]').value = data.titulo || '';
  document.querySelector('[name="nombre_puesto"]').value = data.nombre_puesto || '';
  document.querySelector('[name="categoria"]').value = data.categoria || '';
  document.querySelector('[name="ubicacion"]').value = data.ubicacion || '';
  document.querySelector('[name="modalidad"]').value = data.modalidad || '';
  document.querySelector('[name="descripcion"]').value = data.descripcion || '';
  document.querySelector('[name="habilidades_requeridas"]').value = data.habilidades_requeridas || '';
  inicializarTags();
  document.querySelector('[name="experiencia_requerida"]').value = data.experiencia_requerida || '';
  document.querySelector('[name="nivel_educativo"]').value = data.nivel_educativo || '';
  document.querySelector('[name="es_confidencial"]').checked = data.es_confidencial || false;
  document.querySelector('[name="fecha_cierre"]').value = data.fecha_cierre || '';

  mostrarModalOferta();
}

function mostrarModalOferta() {
  document.getElementById('oferta-modal').classList.remove('hidden');
  document.getElementById('oferta-modal-overlay').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeOfertaModal() {
  document.getElementById('oferta-modal').classList.add('hidden');
  document.getElementById('oferta-modal-overlay').classList.add('hidden');
  document.body.style.overflow = '';
}

document.addEventListener('submit', async function(e) {
  const form = e.target;
  if (form.id !== 'oferta-form') return;
  e.preventDefault();

  const formData = new FormData(form);
  const response = await fetch(form.action, {
    method: 'POST',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': csrfToken,
    },
    body: formData,
  });

  const result = await response.json();

  if (result.success) {
    const esNueva = form.action.endsWith(window.URLS.crearOferta);
    closeOfertaModal();
    await refrescarListaOfertas();
    // Crear y editar dejan la oferta en estado pendiente hasta que la apruebe moderacion.
    avisar('exito', esNueva
      ? 'Oferta creada. Queda pendiente hasta que la apruebe el equipo del IEN.'
      : 'Cambios guardados. La oferta vuelve a revisión antes de publicarse.');
  } else {
    mostrarErroresModal(result.errors);
  }
});

function ocultarErroresModal() {
  document.getElementById('modal-errors').classList.add('hidden');
  document.getElementById('modal-errors').innerHTML = '';
}

const CAMPOS_ES = {
  titulo: 'Título',
  nombre_puesto: 'Nombre del puesto',
  categoria: 'Categoría',
  ubicacion: 'Ubicación',
  modalidad: 'Modalidad',
  descripcion: 'Descripción',
  requisitos: 'Requisitos',
  habilidades_requeridas: 'Habilidades requeridas',
  experiencia_requerida: 'Experiencia requerida',
  nivel_educativo: 'Nivel educativo',
  fecha_cierre: 'Fecha de cierre',
  es_confidencial: 'Publicación confidencial',
};

function mostrarErroresModal(errors) {
  const container = document.getElementById('modal-errors');
  container.classList.remove('hidden');
  let html = '<p class="font-medium mb-1">Corregí los siguientes errores:</p><ul class="list-disc pl-5 text-sm">';
  for (const campo in errors) {
    const nombre = CAMPOS_ES[campo] || campo;
    for (const msg of errors[campo]) {
      html += '<li><strong>' + nombre + ':</strong> ' + msg + '</li>';
    }
  }
  html += '</ul>';
  container.innerHTML = html;
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function refrescarListaOfertas() {
  const response = await fetch(window.URLS.listaOfertasParcial);
  const html = await response.text();
  document.getElementById('ofertas-list').innerHTML = html;
  dibujarIconos();
}

let pkEliminar = null;

function confirmDelete(pk) {
  pkEliminar = pk;
  document.getElementById('delete-modal').classList.remove('hidden');
}

function closeDeleteModal() {
  document.getElementById('delete-modal').classList.add('hidden');
  pkEliminar = null;
}

document.getElementById('confirm-delete-btn').addEventListener('click', async function() {
  if (!pkEliminar) return;

  const response = await fetch('/ofertas/eliminar/' + pkEliminar + '/', {
    method: 'POST',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': csrfToken,
    },
  });

  const result = await response.json();
  closeDeleteModal();

  if (result.success) {
    await refrescarListaOfertas();
    avisar('exito', 'Oferta eliminada.');
  } else {
    avisar('error', 'No se pudo eliminar la oferta.');
  }
});


function inicializarTags() {
  const container = document.getElementById('tags-container');
  container.innerHTML = '';
  const hiddenInput = document.getElementById('id_habilidades_requeridas');
  const valor = hiddenInput.value;
  if (valor && valor.trim()) {
    valor.split(',').forEach(tag => {
      const t = tag.trim();
      if (t) dibujarPildora(t);
    });
  }
}

function dibujarPildora(texto) {
  const container = document.getElementById('tags-container');
  const pildora = document.createElement('span');
  pildora.className = 'chip !text-sm';
  pildora.innerHTML = `${escapeHtml(texto)}
    <button type="button" data-tag="${escapeHtml(texto)}"
            class="rounded-full p-0.5 transition-opacity hover:opacity-60">
      <span data-icon="x" class="h-3 w-3"></span>
    </button>`;
  pildora.querySelector('button').addEventListener('click', function() {
    pildora.remove();
    actualizarHiddenInput();
  });
  container.appendChild(pildora);
  actualizarHiddenInput();
  dibujarIconos(pildora);
}

function actualizarHiddenInput() {
  const container = document.getElementById('tags-container');
  const hiddenInput = document.getElementById('id_habilidades_requeridas');
  const tags = Array.from(container.children).map(el => el.childNodes[0].textContent.trim());
  hiddenInput.value = tags.join(',');
}

function escapeHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto;
  return div.innerHTML;
}

function obtenerTagsSeleccionados() {
  const container = document.getElementById('tags-container');
  return Array.from(container.children).map(el => el.childNodes[0].textContent.trim().toLowerCase());
}


document.addEventListener('input', function(e) {
  if (e.target.id !== 'tags-input') return;
  const valor = e.target.value.trim();
  const dropdown = document.getElementById('tags-dropdown');
  dropdown.innerHTML = '';

  if (!valor) {
    dropdown.classList.add('hidden');
    return;
  }

  const lowerValor = valor.toLowerCase();
  const yaSeleccionadas = obtenerTagsSeleccionados();

  const sugerencias = window.HABILIDADES.filter(h =>
    h.toLowerCase().includes(lowerValor) &&
    !yaSeleccionadas.includes(h.toLowerCase())
  );

  if (sugerencias.length === 0) {
    dropdown.classList.add('hidden');
    return;
  }

  sugerencias.forEach(s => {
    const li = document.createElement('li');
    li.className = 'px-4 py-2 cursor-pointer hover:bg-primary/10 text-sm transition-colors';
    li.textContent = s;
    li.addEventListener('click', () => seleccionarSugerencia(s));
    dropdown.appendChild(li);
  });

  dropdown.classList.remove('hidden');
});

function seleccionarSugerencia(texto) {
  document.getElementById('tags-input').value = '';
  document.getElementById('tags-dropdown').classList.add('hidden');
  dibujarPildora(texto);
}

document.addEventListener('keydown', function(e) {
  if (e.target.id !== 'tags-input') return;

  if (e.key === 'Enter') {
    e.preventDefault();
    const valor = e.target.value.trim();
    if (!valor) return;
    const primerSug = document.querySelector('#tags-dropdown li');
    if (primerSug) {
      seleccionarSugerencia(primerSug.textContent);
    }
  }

  if (e.key === 'Escape') {
    document.getElementById('tags-dropdown').classList.add('hidden');
  }

  if (e.key === 'Backspace' && e.target.value === '') {
    const ultima = document.querySelector('#tags-container span:last-child');
    if (ultima) ultima.querySelector('button')?.click();
  }
});

document.addEventListener('click', function(e) {
  const input = document.getElementById('tags-input');
  const dropdown = document.getElementById('tags-dropdown');
  if (e.target !== input && !dropdown.contains(e.target)) {
    dropdown.classList.add('hidden');
  }
});