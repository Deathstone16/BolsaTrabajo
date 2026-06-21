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
  mostrarModalOferta();
}

async function openEditModal(pk) {
  document.getElementById('modal-title').textContent = 'Editar oferta laboral';
  document.getElementById('oferta-form').action = '/ofertas/editar/' + pk + '/';
  ocultarErroresModal();

  const response = await fetch('/ofertas/datos/' + pk + '/');
  const data = await response.json();

  if (data.error) {
    alert(data.error);
    return;
  }

  document.querySelector('[name="titulo"]').value = data.titulo || '';
  document.querySelector('[name="nombre_puesto"]').value = data.nombre_puesto || '';
  document.querySelector('[name="categoria"]').value = data.categoria || '';
  document.querySelector('[name="ubicacion"]').value = data.ubicacion || '';
  document.querySelector('[name="modalidad"]').value = data.modalidad || '';
  document.querySelector('[name="descripcion"]').value = data.descripcion || '';
  document.querySelector('[name="requisitos"]').value = data.requisitos || '';
  document.querySelector('[name="habilidades_requeridas"]').value = data.habilidades_requeridas || '';
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
    closeOfertaModal();
    await refrescarListaOfertas();
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
  lucide.createIcons();
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
  } else {
    alert('Error al eliminar la oferta');
  }
});
