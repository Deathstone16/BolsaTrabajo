document.addEventListener('DOMContentLoaded', function() {
    const cvInput = document.getElementById('cv-input');
    const feedback = document.getElementById('cv-feedback');
    const uploadArea = document.getElementById('cv-upload-area');
    const formUpload = document.getElementById('form-cv-upload');
    const formEliminar = document.getElementById('form-eliminar-cv');

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
            if (confirm('¿Estás seguro de que deseas eliminar tu CV?')) {
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
                        location.reload();
                    } else {
                        mostrarFeedback('error', data.mensaje || 'Error al eliminar el CV.');
                    }
                })
                .catch(() => {
                    mostrarFeedback('error', 'Error de conexión.');
                });
            }
        });
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
                mostrarFeedback('success', data.mensaje || 'CV cargado con éxito.');
                setTimeout(() => location.reload(), 1500);
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
                mostrarFeedback('success', data.mensaje || 'CV reemplazado con éxito.');
                setTimeout(() => location.reload(), 1500);
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

    function mostrarFeedback(tipo, mensaje) {
        feedback.classList.remove('hidden');
        let icono = '';
        let clases = '';

        switch(tipo) {
            case 'success':
                icono = '<svg class="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
                clases = 'bg-green-50 text-green-800 border border-green-200';
                break;
            case 'error':
                icono = '<svg class="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';
                clases = 'bg-red-50 text-red-800 border border-red-200';
                break;
            case 'loading':
                icono = '<svg class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
                clases = 'bg-blue-50 text-blue-800 border border-blue-200';
                break;
        }

        feedback.innerHTML = '<div class="flex items-center gap-3 p-4 rounded-lg ' + clases + '">' + icono + '<p class="text-sm font-medium">' + mensaje + '</p></div>';
    }
});
