# Bolsa de Trabajo IEN (Django)

Aplicación web de la bolsa de trabajo. Para el análisis de CV usa el
microservicio FastAPI ubicado en el repositorio `ia_api/backend`.

## Requisitos

- Python 3.12 (recomendado)
- Git
- Docker y Docker Compose (necesarios para Redis, usado por Celery)
- Una clave válida de Groq; se configura en el repositorio del microservicio

## Ejecutar todo en local desde un clon nuevo

Cloná ambos repositorios en carpetas vecinas o elegí las rutas que prefieras:

```bash
git clone <URL-DEL-REPOSITORIO-DJANGO> BolsaTrabajo
git clone <URL-DEL-REPOSITORIO-IA> ia_api
```

### 1. Preparar Django

Desde `BolsaTrabajo`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz de `BolsaTrabajo`. Para desarrollo local, el
mínimo necesario para integrar el análisis es:

```dotenv
IA_API_URL=http://127.0.0.1:8001/api/v1/cv-analyses
IA_API_TOKEN=
IA_CALLBACK_TOKEN=elegi-un-secreto-local
```

`IA_CALLBACK_TOKEN` debe coincidir exactamente con
`CV_RESULT_CALLBACK_SECRET` del `.env` de FastAPI. Las variables de Gmail son
opcionales para iniciar la aplicación, pero necesarias para enviar correos.

Aplica la base de datos y, opcionalmente, crea un administrador:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

### 2. Preparar el microservicio de IA

Seguí la sección **Ejecutar la pila completa en local** del
[README del microservicio](../../ia_api/backend/README.md). Su `.env` debe usar
este callback local:

```dotenv
CV_RESULT_CALLBACK_URL=http://127.0.0.1:8000/ia/llegue/
CV_RESULT_CALLBACK_SECRET=elegi-un-secreto-local
```

### 3. Iniciar los servicios

Se necesitan cuatro terminales:

```bash
# Terminal 1, desde ia_api/backend
docker compose up -d redis

# Terminal 2, desde ia_api/backend
make run-worker

# Terminal 3, desde ia_api/backend
make run-api

# Terminal 4, desde BolsaTrabajo
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

Abre `http://127.0.0.1:8000/`.

## Comprobación rápida

Con los servicios iniciados, estas rutas deben responder:

```bash
curl -I http://127.0.0.1:8000/
curl http://127.0.0.1:8001/
```

Luego inicia sesión como postulante, carga un PDF y pulsa **Analizar CV**. La
solicitud responde sin esperar el análisis: FastAPI encola el PDF y Celery lo
extrae y procesa en segundo plano. El resultado se guarda cuando Django recibe
el callback.

## Puertos locales

| Servicio | Puerto | Uso |
| --- | --- | --- |
| Django | 8000 | Interfaz web y callback `/ia/llegue/` |
| FastAPI | 8001 | API de análisis de CV |
| Redis | 6379 | Cola entre FastAPI y Celery |

## Problemas frecuentes

- **“El servicio de análisis no está configurado”**: falta `IA_API_URL` en el
  `.env` de Django o Django no fue reiniciado.
- **Error de callback 401**: `IA_CALLBACK_TOKEN` y
  `CV_RESULT_CALLBACK_SECRET` no son iguales.
- **Análisis pendiente**: confirma que Redis y `make run-worker` estén activos.
- **Error del modelo de Groq**: revisa `GROQ_API_KEY` y `CV_MODEL` en el `.env`
  del microservicio. Para esta integración se usa `qwen/qwen3.8-27b`.
