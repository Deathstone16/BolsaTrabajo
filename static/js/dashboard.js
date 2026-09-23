function avisar(tipo, mensaje) {
  if (window.IenUI && typeof window.IenUI.aviso === 'function') window.IenUI.aviso(tipo, mensaje);
  else alert(mensaje);
}

function dibujarIconos(scope) {
  if (window.IenUI && window.IenUI.injectIcons) window.IenUI.injectIcons(scope || document);
  else if (typeof lucide !== 'undefined') lucide.createIcons();
}

function cambiarTab(nombre) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  const tab = document.getElementById('tab-' + nombre);
  if (!tab) return;
  tab.classList.remove('hidden');
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
  if (document.querySelector('.tab-link')) {
    const tab = window.location.hash.replace('#', '') || 'ofertas';
    cambiarTab(tab);
  }
  inicializarTags('duras');
  inicializarTags('blandas');
});

function inicializarTags(sufijo) {
  const container = document.getElementById('tags-container-' + sufijo);
  if (!container) return;
  container.innerHTML = '';
  const hiddenInput = document.getElementById('id_habilidades_' + sufijo);
  if (!hiddenInput) return;
  const valor = hiddenInput.value;
  if (valor && valor.trim()) {
    valor.split(',').forEach(tag => {
      const t = tag.trim();
      if (t) dibujarPildora(t, sufijo);
    });
  }
}

function dibujarPildora(texto, sufijo) {
  const container = document.getElementById('tags-container-' + sufijo);
  if (!container) return;
  const pildora = document.createElement('span');
  pildora.className = 'chip !text-sm';
  pildora.innerHTML = `${escapeHtml(texto)}
    <button type="button" data-tag="${escapeHtml(texto)}"
            class="rounded-full p-0.5 transition-opacity hover:opacity-60">
      <span data-icon="x" class="h-3 w-3"></span>
    </button>`;
  pildora.querySelector('button').addEventListener('click', function() {
    pildora.remove();
    actualizarHiddenInput(sufijo);
  });
  container.appendChild(pildora);
  actualizarHiddenInput(sufijo);
  dibujarIconos(pildora);
}

function actualizarHiddenInput(sufijo) {
  const container = document.getElementById('tags-container-' + sufijo);
  if (!container) return;
  const hiddenInput = document.getElementById('id_habilidades_' + sufijo);
  if (!hiddenInput) return;
  const tags = Array.from(container.children).map(el => el.childNodes[0].textContent.trim());
  hiddenInput.value = tags.join(', ');
}

function escapeHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto;
  return div.innerHTML;
}

function obtenerTagsSeleccionados(sufijo) {
  const container = document.getElementById('tags-container-' + sufijo);
  if (!container) return [];
  return Array.from(container.children).map(el => el.childNodes[0].textContent.trim().toLowerCase());
}

document.addEventListener('input', function(e) {
  const sufijo = e.target.id === 'tags-input-duras' ? 'duras'
                 : e.target.id === 'tags-input-blandas' ? 'blandas' : null;
  if (!sufijo) return;

  const valor = e.target.value.trim();
  const dropdown = document.getElementById('tags-dropdown-' + sufijo);
  if (!dropdown) return;
  dropdown.innerHTML = '';

  if (!valor) {
    dropdown.classList.add('hidden');
    return;
  }

  const lowerValor = valor.toLowerCase();
  const yaSeleccionadas = obtenerTagsSeleccionados(sufijo);
  const catalogo = sufijo === 'duras' ? window.HABILIDADES_DURAS : window.HABILIDADES_BLANDAS;

  const sugerencias = catalogo.filter(h =>
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
    li.addEventListener('click', () => seleccionarSugerencia(s, sufijo));
    dropdown.appendChild(li);
  });

  dropdown.classList.remove('hidden');
});

function seleccionarSugerencia(texto, sufijo) {
  document.getElementById('tags-input-' + sufijo).value = '';
  document.getElementById('tags-dropdown-' + sufijo).classList.add('hidden');
  dibujarPildora(texto, sufijo);
}

document.addEventListener('keydown', function(e) {
  const sufijo = e.target.id === 'tags-input-duras' ? 'duras'
                 : e.target.id === 'tags-input-blandas' ? 'blandas' : null;
  if (!sufijo) return;

  if (e.key === 'Enter') {
    e.preventDefault();
    const valor = e.target.value.trim();
    if (!valor) return;
    const primerSug = document.querySelector('#tags-dropdown-' + sufijo + ' li');
    if (primerSug) seleccionarSugerencia(primerSug.textContent, sufijo);
  }

  if (e.key === 'Escape') {
    document.getElementById('tags-dropdown-' + sufijo).classList.add('hidden');
  }

  if (e.key === 'Backspace' && e.target.value === '') {
    const ultima = document.querySelector('#tags-container-' + sufijo + ' span:last-child');
    if (ultima) ultima.querySelector('button')?.click();
  }
});

document.addEventListener('click', function(e) {
  ['duras', 'blandas'].forEach(sufijo => {
    const input = document.getElementById('tags-input-' + sufijo);
    const dropdown = document.getElementById('tags-dropdown-' + sufijo);
    if (input && dropdown && e.target !== input && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
});