(function() {
    const searchInput = document.getElementById('course-search');
    const typeFilter = document.getElementById('type-filter');
    const grid = document.getElementById('courses-grid');

    if (!searchInput || !typeFilter || !grid) return;

    let timeoutId = null;

    function filtrar() {
        const search = searchInput.value.toLowerCase().trim();
        const tipo = typeFilter.value;
        let visibleCount = 0;

        grid.querySelectorAll('[data-nombre]').forEach(card => {
            const nombre = card.dataset.nombre;
            const cardTipo = card.dataset.tipo;
            const coincide = nombre.includes(search) && (tipo === 'all' || cardTipo === tipo);
            card.style.display = coincide ? '' : 'none';
            if (coincide) visibleCount++;
        });

        let emptyMsg = grid.querySelector('.empty-message');
        if (visibleCount === 0) {
            if (!emptyMsg) {
                emptyMsg = document.createElement('div');
                emptyMsg.className = 'empty-message col-span-full text-center py-12 text-muted-foreground';
                emptyMsg.textContent = 'No se encontraron cursos con esos filtros';
                grid.appendChild(emptyMsg);
            }
        } else if (emptyMsg) {
            emptyMsg.remove();
        }
    }

    searchInput.addEventListener('input', function() {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(filtrar, 200);
    });

    typeFilter.addEventListener('change', filtrar);
})();