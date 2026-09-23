document.addEventListener('DOMContentLoaded', function() {
    const cvInput = document.getElementById('cv-input');
    const feedback = document.getElementById('cv-feedback');
    const uploadArea = document.getElementById('cv-upload-area');
    const formUpload = document.getElementById('form-cv-upload');
    const formEliminar = document.getElementById('form-eliminar-cv');
    const formAnalizar = document.getElementById('form-analizar-cv');
    const botonResultado = document.getElementById('boton-ver-resultado');
    const AVISO_DEMORA_MS = 20000;
    let pollingAnalisisActivo = false;
    let temporizadorDemora = null;
    // Tienen que estar arriba: el codigo de inicio usa mostrarEstadoAnalisis
    // cuando la pagina carga con un analisis pendiente.
    const panelAnalisis = document.getElementById('analisis-estado');
    const SPINNER = '<svg class="ic h-5 w-5 animate-spin" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.2-8.56"></path></svg>';
    const ICONO_OK = '<svg class="ic h-5 w-5" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5L20 6"></path></svg>';
    const ICONO_ERROR = '<svg class="ic h-5 w-5" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 8v4"></path><path d="M12 16h.01"></path></svg>';

    if (!cvInput) return;

    cvInput.addEventListener('change', function(e) {
        const archivo = e.target.files[0];
        if (!archivo) return;

        // Validar formato
        const formatosPermitidos = ['pdf', 'doc', 'docx'];
        const extension = archivo.name.split('.').pop().toLowerCase();
        if (!formatosPermitidos.includes(extension)) {
            mostrarFeedback('error', 'Formato no permitido. Solo se aceptan PDF, DOC y DOCX.');
            cvInput.value = '';
            return;
        }

        // Validar tamaño (5MB)
        const tamanoMaximo = 5 * 1024 * 1024;
        if (archivo.size > tamanoMaximo) {
            mostrarFeedback('error', 'El archivo supera el tamaño máximo de 5 MB.');
            cvInput.value = '';
            return;
        }

        // Enviar por AJAX si hay form, si no submit directo
        if (formUpload) {
            enviarCV(archivo);
        } else {
            // Caso reemplazar CV - crear form temporal
            enviarCVReemplazo(archivo);
        }
    });

    // Eliminar CV
    if (formEliminar) {
        formEliminar.addEventListener('submit', function(e) {
            e.preventDefault();
            // Modal del sitio (IenUI.confirmar) en vez del confirm() del navegador.
            pedirConfirmacionEliminar().then(function(ok) {
                if (!ok) return;
                fetch(formEliminar.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': formEliminar.querySelector('[name=csrfmiddlewaretoken]').value,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (window.IenUI) window.IenUI.avisoTrasRecarga('exito', data.mensaje || 'CV eliminado.');
                        location.reload();
                    } else {
                        mostrarFeedback('error', data.mensaje || 'Error al eliminar el CV.');
                    }
                })
                .catch(() => {
                    mostrarFeedback('error', 'Error de conexión.');
                });
            });
        });
    }

    if (formAnalizar) {
        const ultimoAnalisisId = formAnalizar.dataset.ultimoAnalisisId;
        const ultimoAnalisisEstado = formAnalizar.dataset.ultimoAnalisisEstado;
        const botonInicial = formAnalizar.querySelector('button[type="submit"]');
        const textoInicial = botonInicial ? botonInicial.innerHTML : '';

        if (ultimoAnalisisId && ultimoAnalisisEstado === 'pendiente') {
            marcarBotonAnalisisPendiente(botonInicial);
            mostrarEstadoAnalisis('pendiente');
            iniciarTemporizadorDemora();
            consultarEstadoAnalisis(ultimoAnalisisId, botonInicial, textoInicial);
        }

        formAnalizar.addEventListener('submit', function(e) {
            e.preventDefault();
            const boton = formAnalizar.querySelector('button[type="submit"]');
            const textoOriginal = boton.innerHTML;
            boton.disabled = true;
            boton.classList.add('opacity-70', 'cursor-wait');
            boton.innerHTML = '<svg class="w-4 h-4 inline-block mr-2 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>Enviando...';
            mostrarEstadoAnalisis('pendiente', 'Enviando tu CV al servicio de análisis…');

            fetch(formAnalizar.action, {
                method: 'POST',
                keepalive: true,
                headers: {
                    'X-CSRFToken': formAnalizar.querySelector('[name=csrfmiddlewaretoken]').value,
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    marcarBotonAnalisisPendiente(boton);
                    deshabilitarBotonResultado();
                    mostrarEstadoAnalisis('pendiente');
                    iniciarTemporizadorDemora();
                    consultarEstadoAnalisis(data.analisis_id, boton, textoOriginal);
                } else {
                    mostrarEstadoAnalisis('error', data.mensaje || 'No se pudo enviar el CV.');
                    restaurarBotonAnalizar(boton, textoOriginal);
                }
            })
            .catch(() => {
                mostrarEstadoAnalisis('error', 'Error de conexión. Intentá nuevamente.');
                restaurarBotonAnalizar(boton, textoOriginal);
            });
        });
    }

    function iniciarTemporizadorDemora() {
        if (temporizadorDemora) return;

        temporizadorDemora = setTimeout(function () {
            mostrarEstadoAnalisis(
                'pendiente',
                'Está tardando un poco más de lo habitual, pero seguimos analizando tu CV.'
            );
        }, AVISO_DEMORA_MS);
    }

    function cancelarTemporizadorDemora() {
        if (!temporizadorDemora) return;

        clearTimeout(temporizadorDemora);
        temporizadorDemora = null;
    }

    function consultarEstadoAnalisis(analisisId, boton, textoOriginal) {
        if (pollingAnalisisActivo) return;
        pollingAnalisisActivo = true;
        const url = formAnalizar.dataset.estadoUrl.replace('/0/', '/' + analisisId + '/');

        function consultar() {
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(response => response.json())
                .then(data => {
                    if (data.estado === 'pendiente') {
                        setTimeout(consultar, 5000);
                        return;
                    }

                    pollingAnalisisActivo = false;
                    cancelarTemporizadorDemora();
                    restaurarBotonAnalizar(boton, textoOriginal);
                    if (data.estado === 'completado') {
                        mostrarEstadoAnalisis('completado', data.mensaje || 'El análisis del CV está listo.', data.resultado_url);
                        habilitarBotonResultado(data.resultado_url);
                    } else {
                        mostrarEstadoAnalisis('error', data.mensaje || 'No se pudo analizar el CV.');
                    }
                })
                .catch(() => {
                    pollingAnalisisActivo = false;
                    cancelarTemporizadorDemora();
                    restaurarBotonAnalizar(boton, textoOriginal);
                    mostrarEstadoAnalisis('error', 'No se pudo consultar el estado del análisis.');
                });
        }

        consultar();
    }

    function restaurarBotonAnalizar(boton, textoOriginal) {
        boton.disabled = false;
        boton.classList.remove('opacity-70', 'cursor-wait', 'cursor-not-allowed');
        boton.innerHTML = textoOriginal;
        // El texto original puede traer un <span data-icon> sin dibujar.
        if (window.IenUI) window.IenUI.injectIcons(boton);
    }

    function marcarBotonAnalisisPendiente(boton) {
        boton.disabled = true;
        boton.classList.remove('cursor-wait');
        boton.classList.add('opacity-70', 'cursor-not-allowed');
        boton.innerHTML = 'Análisis en proceso';
    }

    function deshabilitarBotonResultado() {
        if (!botonResultado) return;
        botonResultado.href = '#';
        botonResultado.setAttribute('aria-disabled', 'true');
        botonResultado.classList.remove('text-primary', 'border-primary', 'hover:bg-primary/5');
        botonResultado.classList.add('text-muted-foreground', 'border-border', 'opacity-50', 'pointer-events-none');
    }

    function habilitarBotonResultado(resultadoUrl) {
        if (!botonResultado) return;
        botonResultado.href = resultadoUrl;
        botonResultado.setAttribute('aria-disabled', 'false');
        botonResultado.classList.remove('text-muted-foreground', 'border-border', 'opacity-50', 'pointer-events-none');
        botonResultado.classList.add('text-primary', 'border-primary', 'hover:bg-primary/5');
    }

    function enviarCV(archivo) {
        const formData = new FormData();
        formData.append('cv', archivo);

        mostrarFeedback('loading', 'Cargando CV...');

        fetch(formUpload.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': formUpload.querySelector('[name=csrfmiddlewaretoken]').value,
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (window.IenUI) window.IenUI.avisoTrasRecarga('exito', data.mensaje || 'CV cargado con éxito.');
                location.reload();
            } else {
                mostrarFeedback('error', data.mensaje || 'Error al cargar el CV.');
                cvInput.value = '';
            }
        })
        .catch(() => {
            mostrarFeedback('error', 'Error de conexión. Intentá nuevamente.');
            cvInput.value = '';
        });
    }

    function enviarCVReemplazo(archivo) {
        const formData = new FormData();
        formData.append('cv', archivo);

        mostrarFeedback('loading', 'Reemplazando CV...');

        fetch(window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (window.IenUI) window.IenUI.avisoTrasRecarga('exito', data.mensaje || 'CV reemplazado con éxito.');
                location.reload();
            } else {
                mostrarFeedback('error', data.mensaje || 'Error al reemplazar el CV.');
                cvInput.value = '';
            }
        })
        .catch(() => {
            mostrarFeedback('error', 'Error de conexión. Intentá nuevamente.');
            cvInput.value = '';
        });
    }

    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    /*
     * Panel #analisis-estado de mi_perfil.html. Mientras el servicio externo
     * procesa el CV muestra spinner y barra animada; al terminar, el resultado
     * o el error. Se puede seguir navegando: el analisis corre en otro servicio.
     */

    function mostrarEstadoAnalisis(estado, mensaje, resultadoUrl) {
        if (!panelAnalisis) { mostrarFeedback(estado === 'pendiente' ? 'loading' : (estado === 'completado' ? 'success' : 'error'), mensaje || ''); return; }
        const icono = panelAnalisis.querySelector('[data-analisis-icono]');
        const titulo = panelAnalisis.querySelector('[data-analisis-titulo]');
        const texto = panelAnalisis.querySelector('[data-analisis-mensaje]');
        const link = panelAnalisis.querySelector('[data-analisis-link]');
        const barra = panelAnalisis.querySelector('[data-analisis-barra]');

        panelAnalisis.classList.remove('hidden');
        link.style.display = 'none';  // .btn-ien le gana a .hidden
        barra.classList.toggle('hidden', estado !== 'pendiente');

        if (estado === 'pendiente') {
            icono.className = 'grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#512DA8]/10 text-[#512DA8]';
            icono.innerHTML = SPINNER;
            titulo.textContent = 'Analizando tu CV con IA…';
            texto.textContent = mensaje || 'Puede tardar un par de minutos. Podés seguir usando la plataforma: te avisamos acá cuando termine.';
        } else if (estado === 'completado') {
            icono.className = 'grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#27AE60]/15 text-[#27AE60]';
            icono.innerHTML = ICONO_OK;
            titulo.textContent = '¡Tu análisis está listo!';
            texto.textContent = mensaje || 'Ya podés ver las habilidades que detectamos en tu CV.';
            if (resultadoUrl) { link.href = resultadoUrl; link.style.display = ''; }
        } else {
            icono.className = 'grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#d4183d]/10 text-[#d4183d]';
            icono.innerHTML = ICONO_ERROR;
            titulo.textContent = 'No se pudo analizar el CV';
            texto.textContent = mensaje || 'Intentá nuevamente en unos minutos.';
        }
    }

    function pedirConfirmacionEliminar() {
        if (!window.IenUI || typeof window.IenUI.confirmar !== 'function') {
            return Promise.resolve(confirm('¿Estás seguro de que deseas eliminar tu CV?'));
        }
        return window.IenUI.confirmar({
            titulo: '¿Eliminar tu CV?',
            mensaje: 'Vas a tener que volver a subirlo para postularte y para analizarlo con IA.',
            confirmar: 'Eliminar CV',
            peligro: true,
            icono: 'trash'
        });
    }

    function mostrarFeedback(tipo, mensaje) {
        // Los avisos salen como notificacion flotante (IenUI.aviso).
        if (window.IenUI && typeof window.IenUI.aviso === 'function') {
            window.IenUI.aviso({ success: 'exito', error: 'error', loading: 'info' }[tipo] || 'info', mensaje);
            return;
        }
        mostrarFeedbackEnLinea(tipo, mensaje);
    }

    // Respaldo si ien-ui.js no cargo: el aviso en linea de siempre.
    function mostrarFeedbackEnLinea(tipo, mensaje) {
        feedback.classList.remove('hidden');
        let icono = '';
        let clases = '';

        switch(tipo) {
            case 'success':
                icono = '<svg class="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
                clases = 'bg-green-50 text-green-800 border border-green-200 rounded-2xl';
                break;
            case 'error':
                icono = '<svg class="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';
                clases = 'bg-red-50 text-red-800 border border-red-200 rounded-2xl';
                break;
            case 'loading':
                icono = '<svg class="w-5 h-5 text-[#512DA8] animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
                clases = 'bg-[#512DA8]/10 text-[#43218F] border border-[#512DA8]/20 rounded-2xl';
                break;
        }

        feedback.innerHTML = '<div class="flex items-center gap-3 p-4 rounded-lg ' + clases + '">' + icono + '<p class="text-sm font-medium">' + mensaje + '</p></div>';
    }
});
