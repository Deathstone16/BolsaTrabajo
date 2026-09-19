// Autocompletado de ubicación con la API Georef (datos.gob.ar)
const inputUbicacion = document.getElementById('input-ubicacion');
const listaSugerencias = document.getElementById('sugerencias-ubicacion');

let temporizador = null;
let indiceActivo = -1;

if (inputUbicacion && listaSugerencias) {


  inputUbicacion.addEventListener('input', () => {
    clearTimeout(temporizador);
    const texto = inputUbicacion.value.trim();

    if (texto.length < 3) {
      ocultarLista();
      return;
    }

    temporizador = setTimeout(() => buscarLocalidades(texto), 300);
  });


  async function buscarLocalidades(texto) {
    const url = 'https://apis.datos.gob.ar/georef/api/localidades'
      + '?nombre=' + encodeURIComponent(texto)
      + '&max=10&campos=nombre,provincia.nombre';

    try {
      const respuesta = await fetch(url);
      if (!respuesta.ok) throw new Error('Error en Georef');
      const data = await respuesta.json();

      const lista = data.localidades.map(
        (loc) => `${loc.nombre}, ${loc.provincia.nombre}`
      );
      
      mostrarSugerencias([...new Set(lista)]);
    } catch (error) {
     
      ocultarLista();
    }
  }


  function mostrarSugerencias(lista) {
    listaSugerencias.innerHTML = '';
    indiceActivo = -1;

    if (lista.length === 0) {
      const li = document.createElement('li');
      li.textContent = 'Sin resultados';
      li.className = 'px-4 py-2 text-muted-foreground';
      listaSugerencias.appendChild(li);
    } else {
      lista.forEach((texto) => {
        const li = document.createElement('li');
        li.textContent = texto;
        li.className = 'opcion-ubicacion px-4 py-2 cursor-pointer hover:bg-muted';
        li.addEventListener('mousedown', (e) => {
          e.preventDefault();
          elegir(texto);
        });
        listaSugerencias.appendChild(li);
      });
    }

    listaSugerencias.classList.remove('hidden');
  }

  function elegir(texto) {
    inputUbicacion.value = texto;
    ocultarLista();
  }

  function ocultarLista() {
    listaSugerencias.classList.add('hidden');
    listaSugerencias.innerHTML = '';
    indiceActivo = -1;
  }

  inputUbicacion.addEventListener('keydown', (e) => {
    const opciones = listaSugerencias.querySelectorAll('.opcion-ubicacion');
    if (listaSugerencias.classList.contains('hidden') || opciones.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      indiceActivo = (indiceActivo + 1) % opciones.length;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      indiceActivo = (indiceActivo - 1 + opciones.length) % opciones.length;
    } else if (e.key === 'Enter' && indiceActivo >= 0) {
      e.preventDefault(); // que no se envíe el form
      elegir(opciones[indiceActivo].textContent);
      return;
    } else if (e.key === 'Escape') {
      ocultarLista();
      return;
    } else {
      return;
    }

    opciones.forEach((li, i) => li.classList.toggle('bg-muted', i === indiceActivo));
  });

  inputUbicacion.addEventListener('blur', ocultarLista);
}