# 01 · Presentación, instalación y ejecución

Revisión: 22/10/2026. Responsable sugerido: responsable técnico o quien modifica el entorno. Actualizar ante cambios de instalación, dependencias, comandos o estructura.

## Objetivo y alcance

Permitir comprender e iniciar Bolsa de Trabajo IEN sin depender de otra persona. El sistema gestiona usuarios, empresas validadas, ofertas moderadas, CV privados, análisis y compatibilidad con IA, favoritas y cursos. No registra postulaciones ni contrataciones.

El `README.md` (raíz del repositorio) es la fuente principal de instalación y variables; este componente explica qué hay que preparar y conecta las instrucciones. No mantener aquí otra copia completa de la tabla de configuración.

## Stack y prerrequisitos

Python 3.12 recomendado; Django >=5.2,<6, Channels/Daphne y Pydantic. SQLite para desarrollo o PostgreSQL, obligatorio en producción. Redis para canales, caché y el stack externo. Node.js/npm para pruebas JavaScript y Playwright. Las dependencias están en `requirements.txt` y `package.json`.

FastAPI y Celery pertenecen al repositorio externo `ia_api/backend`. Para probar la cadena completa se necesita una versión compatible y configurar allí el proveedor LLM. No se presupone que un modelo o proveedor citado en un informe histórico siga vigente.

## Preparación local

Desde la raíz del repositorio, en macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

Completar `.env` antes de iniciar: secretos propios, URL de la API y tokens coincidentes entre servicios, HMAC del callback y conexiones Redis. Consultar la tabla completa del `README.md` (raíz del repositorio). Nunca subir `.env` ni usar cuentas demo en producción. En Windows usar `.\.venv\Scripts\python.exe` en lugar de `.venv/bin/python`.

## Procesos necesarios

En terminales independientes, desde BolsaTrabajo:

```bash
.venv/bin/python manage.py runserver 0.0.0.0:8000
.venv/bin/python manage.py run_integration_dispatcher --kind extraction --interval 2
.venv/bin/python manage.py run_integration_dispatcher --kind match --interval 2
```

En otras terminales, desde el repositorio externo y verificando sus comandos/Makefile:

```bash
docker compose up -d redis
make run-worker
make run-api
```

Los comandos externos son los documentados por la integración local; este repositorio no contiene su implementación. Abrir `http://127.0.0.1:8000/`. Los despachadores deben estar activos para entregar los trabajos encolados en Django. Ver [operación general](../operaciones/despliegue.md) y [arranque Windows](../operaciones/inicio-local-windows.md).

## Verificación y pruebas

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test usuarios categorias ofertas cursos ia matching moderacion emails
npm ci
npm run test:js
npm run test:e2e
```

Las pruebas E2E requieren servicios locales y configuración; la ejecución con IA real es una variante explícita que consume cuota. Ver [pruebas y calidad](../pruebas/estrategia.md) y [datos demo](../pruebas/datos-demo.md).

## Documentación y mantenimiento

El [índice general](../README.md) enlaza los siete componentes y el material complementario. Para generar HTML:

```bash
.venv/bin/python -m sphinx -b html docs docs/_build/html
```

`docs/index.rst` es el índice de Sphinx; los Markdown se procesan con MyST. Los diagramas Mermaid permanecen como fuentes editables; su representación gráfica depende del visor. La [referencia de módulos](../referencia/apps/index.rst) conserva autodocumentación del código.
