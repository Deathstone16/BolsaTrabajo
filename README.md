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

Copiá la plantilla de configuración y completá el secreto del callback:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegá el valor generado en `IA_CALLBACK_TOKEN` de Django y en
`CV_RESULT_CALLBACK_SECRET` de FastAPI. Generá un segundo valor distinto y
copialo tanto en `IA_API_TOKEN` de Django como en `SERVICE_API_TOKEN` de
FastAPI. Generá otro valor distinto para `JWT_SECRET_KEY` de FastAPI. Nunca
subas los archivos `.env` a Git.

Aplica la base de datos y, opcionalmente, crea un administrador:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

### 2. Preparar el microservicio de IA

Seguí la sección **Ejecutar la pila completa en local** del
[README del microservicio](../../ia_api/backend/README.md). Copiá también su
[`.env.example`](../../ia_api/backend/.env.example) a `ia_api/backend/.env`. Para
conectar ambos servicios, verificá estas dos líneas en el archivo de FastAPI:

```dotenv
CV_RESULT_CALLBACK_URL=http://127.0.0.1:8000/ia/llegue/
CV_RESULT_CALLBACK_SECRET=el-mismo-valor-de-IA_CALLBACK_TOKEN
SERVICE_API_TOKEN=el-mismo-valor-de-IA_API_TOKEN
```

### De dónde sale cada variable

En `BolsaTrabajo/.env`:

| Variable | Cómo completarla |
| --- | --- |
| `DEBUG` | `true` solo para desarrollo local. En producción usá `false`. |
| `SECRET_KEY` | Clave propia, larga y aleatoria para firmar sesiones, CSRF y otros datos de Django. Generala con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. Es obligatoria si `DEBUG=false`. |
| `ALLOWED_HOSTS` | Lista separada por comas de los dominios/IP que atenderá Django, por ejemplo `empleos.ejemplo.org,www.empleos.ejemplo.org`. Es obligatoria si `DEBUG=false`. |
| `SECURE_SSL_REDIRECT` | En producción HTTPS, dejá `true` para redirigir HTTP a HTTPS. Solo desactivalo si el proxy ya hace esa redirección y conserva `X-Forwarded-Proto`. |
| `SECURE_HSTS_SECONDS` | Tiempo que el navegador recordará usar HTTPS. `31536000` equivale a un año; usá `0` temporalmente al probar una migración HTTPS. |
| `IA_API_URL` | Dirección de FastAPI más `/api/v1/cv-analyses`. Con `make run-api` local, usá `http://127.0.0.1:8001/api/v1/cv-analyses`. Si FastAPI corre en otra máquina o contenedor, usá una dirección alcanzable desde Django. |
| `IA_CALLBACK_TOKEN` | Secreto aleatorio generado con el comando anterior. Debe ser idéntico a `CV_RESULT_CALLBACK_SECRET` de FastAPI; Django lo verifica en el header `X-IA-Callback-Token`. |
| `IA_API_TOKEN` | Generá un secreto aleatorio distinto del callback y copialo también en `SERVICE_API_TOKEN` de FastAPI. Django lo envía como `Authorization: Bearer ...` para autenticar su llamada al microservicio. |
| `IA_CALLBACK_URL` | Reservada para una URL pública fija; el código actual no la utiliza. Dejala vacía. La URL efectiva del callback se configura en FastAPI con `CV_RESULT_CALLBACK_URL`. |
| `EMAIL_HOST_USER` | Dirección de la cuenta Gmail que enviará correos. Puede quedar vacía si no necesitás email local. |
| `EMAIL_HOST_PASSWORD` | [Contraseña de aplicación de Google](https://support.google.com/accounts/answer/185833?hl=es), no la contraseña habitual de Gmail. Requiere verificación en dos pasos; puede quedar vacía si no enviás correos. |

En `ia_api/backend/.env` se parte de la [plantilla del microservicio](../../ia_api/backend/.env.example):

| Variable | Cómo completarla |
| --- | --- |
| `GROQ_API_KEY` | Creá una clave en la [consola de Groq](https://console.groq.com/keys) y copiala solamente en este `.env`. |
| `SERVICE_API_TOKEN` | Copiá exactamente `IA_API_TOKEN` de Django. Es el Bearer token que restringe `POST` y `GET /api/v1/cv-analyses` al servidor de Django; no es un JWT de usuario. |
| `CV_MODEL` | ID exacto de un modelo disponible en el [catálogo de Groq](https://console.groq.com/docs/models); la plantilla propone `qwen/qwen3.8-27b`. |
| `CV_RESULT_CALLBACK_URL` | URL de Django que recibe el resultado: `http://127.0.0.1:8000/ia/llegue/` en local. Desde un contenedor debe ser una dirección que ese contenedor pueda alcanzar. |
| `CV_RESULT_CALLBACK_SECRET` | Copiá exactamente el valor de `IA_CALLBACK_TOKEN`; no es una clave de Groq ni un JWT. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Direcciones de Redis para la cola y los resultados. Con Redis local del `docker compose` del microservicio, conservá `redis://localhost:6379/0` y `/1` respectivamente. |
| `JWT_SECRET_KEY` | Generá otro secreto aleatorio con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. FastAPI exige esta variable al arrancar, pero el flujo actual de CV no genera ni comprueba JWT; no debe coincidir con `IA_CALLBACK_TOKEN`. |
| `SERVICE_USER` / `SERVICE_PASSWORD` | Elegí un identificador y una contraseña local distinta. La configuración actual los exige, aunque ninguna ruta del análisis los usa para autenticarse. |
| `PROJECT_NAME` | Nombre descriptivo que muestra FastAPI; puede quedar como en la plantilla. |
| `MODE` | `development` para local; también admite `testing` y `production`. |
| `BACKEND_CORS_ORIGINS` | Lista JSON de orígenes autorizados si un navegador llama directamente a FastAPI, por ejemplo `["http://localhost:3000"]`. La llamada de Django a FastAPI ocurre entre servidores y no necesita CORS. |
| `API_VERSION` | Versión usada en el prefijo de las rutas; dejá `v1` salvo que versionés la API de forma explícita. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración prevista para JWT heredados. El flujo actual no emite JWT, por lo que puede conservar el valor de la plantilla (`60`). |
| `CV_BLOQUE_CARACTERES` | Tamaño de los fragmentos de texto del CV. Usá el valor de la plantilla (`4000`) salvo que ajustes el procesamiento. |
| `GROQ_MAX_TOKENS` | Máximo de tokens de respuesta solicitados al modelo. La plantilla usa `950`. |
| `GROQ_PAUSA_SEGUNDOS` | Pausa entre consultas al modelo. La plantilla usa `12`. |

`JWT_SECRET_KEY` y `SERVICE_USER`/`SERVICE_PASSWORD` son variables heredadas
requeridas por la configuración del microservicio; actualmente no hay una ruta
para obtener un JWT. El token que se coloca en `IA_API_TOKEN` es
`SERVICE_API_TOKEN`, una credencial compartida entre ambos servidores.

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
