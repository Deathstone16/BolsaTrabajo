# Bolsa de Trabajo IEN (Django)

Aplicación web de la bolsa de trabajo. Para el análisis de CV usa el
microservicio FastAPI ubicado en el repositorio `ia_api/backend`.

## Documentación del proyecto

La [guía de documentación](docs/README.md) reúne los siete
componentes: requisitos y aceptación, arquitectura y ADR, contratos HTTP y
WebSocket, modelo de datos, operación y pruebas. El
[modelo de datos](docs/datos/modelo-datos.md) incluye el diccionario de las 21
entidades propias y un [diagrama ER editable](docs/datos/modelo-datos.mmd).
La [revisión de limpieza](docs/mantenimiento/analisis-limpieza.md) distingue
residuos locales, documentos históricos y candidatos a simplificar en el código.

## Requisitos

- Python 3.12 (recomendado)
- Git
- Docker y Docker Compose (necesarios para Redis, usado por Celery)
- PostgreSQL para producción; en desarrollo podés seguir usando SQLite
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

Pegá el valor generado en `IA_CALLBACK_HMAC_SECRET` de Django y en
`CV_RESULT_CALLBACK_HMAC_SECRET` de una versión compatible de FastAPI. El
callback actual verifica una firma HMAC; `IA_CALLBACK_TOKEN` solo se conserva
como respaldo de configuraciones locales anteriores. Generá un segundo valor distinto y
copialo tanto en `IA_API_TOKEN` de Django como en `SERVICE_API_TOKEN` de
FastAPI. Generá otro valor distinto para `JWT_SECRET_KEY` de FastAPI. Nunca
subas los archivos `.env` a Git.

Aplica la base de datos y, opcionalmente, crea un administrador:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

#### Elegir SQLite o PostgreSQL

La opción predeterminada en desarrollo es SQLite (`DB_ENGINE=sqlite`). Para
probar PostgreSQL, instalá las dependencias de `requirements.txt`, creá una
base vacía y completá **solo en tu `.env` privado**:

```dotenv
DB_ENGINE=postgresql
DB_NAME=nombre_de_la_base
DB_USER=usuario_de_la_base
DB_PASSWORD=clave_privada
DB_HOST=127.0.0.1
DB_PORT=5432
```

Si PostgreSQL corre en Docker con otro puerto publicado, usá ese puerto en
`DB_PORT` (la prueba local de Windows usa `5433`). Ejecutá `manage.py migrate`
para crear las tablas y `manage.py createsuperuser` para el primer administrador.
No hace falta copiar los datos de SQLite si son solamente de prueba: cambiar
`DB_ENGINE` no borra `db.sqlite3`. En producción `DEBUG=false` exige
`DB_ENGINE=postgresql` y las cuatro credenciales no vacías; las variables
reales se cargan en el servicio de hosting, **nunca en Git**. El modo TLS se
puede ajustar con `DB_SSLMODE`: por defecto es `prefer` en desarrollo y
`require` en producción. Si el proveedor entrega un certificado CA, preferí
`verify-full` y seguí sus instrucciones para configurarlo.
En ese caso, configurá también el certificado raíz según
[PostgreSQL/libpq](https://www.postgresql.org/docs/current/libpq-ssl.html).

Para comprobar la selección de motor y las protecciones de producción sin
crear ni borrar bases de datos, ejecutá:

```bash
.venv/bin/python -m unittest ientrabajo.test_database_settings
```

En Windows reemplazá `.venv/bin/python` por
`.\.venv\Scripts\python.exe`. Antes de publicar, generá un secreto HMAC nuevo:
el valor de respaldo que existía en una versión anterior del código no debe
reutilizarse. Actualizalo también en el microservicio de IA.

La conexión local confirma la compatibilidad de la aplicación, pero **no
publica la base**. Cuando se elija el hosting faltará crear su PostgreSQL,
configurar respaldos y ejecutar allí las migraciones. Los CV e imágenes de
`media/` necesitan almacenamiento y controles de acceso separados; Redis y el
servidor ASGI/WebSocket también siguen siendo necesarios para el flujo de IA.

#### Qué quedó hecho en esta rama

- Se agregó `psycopg` y la selección de base por variables de entorno: SQLite para desarrollo y PostgreSQL para desarrollo o producción.
- La aplicación se detiene con un mensaje claro si faltan credenciales de PostgreSQL o si se intenta usar SQLite con `DEBUG=false`. En producción también exige un dominio permitido y un secreto de callback de IA.
- Se quitó del código el secreto de callback que antes tenía un valor fijo. El `.env` local sigue sin subirse y conserva compatibilidad con `IA_CALLBACK_TOKEN` mientras se prepara el secreto HMAC nuevo.
- Se verificó el arranque de Django con ambos motores, se aplicaron las migraciones en PostgreSQL local y pasaron las pruebas de configuración y de las aplicaciones con una base temporal. La base PostgreSQL de producción todavía no existe.

### 2. Preparar el microservicio de IA

Seguí la sección **Ejecutar la pila completa en local** del
[README del microservicio, rama `ia-match`](https://github.com/IENbolsa2026/ia_api/blob/ia-match/backend/README.md). Copiá también su
[`.env.example`](https://github.com/IENbolsa2026/ia_api/blob/ia-match/backend/.env.example) a `ia_api/backend/.env`. La rama `main` de la API no incluye todavía el callback HMAC que exige este Django. Para
conectar ambos servicios, verificá estas dos líneas en el archivo de FastAPI:

```dotenv
CV_RESULT_CALLBACK_URL=http://127.0.0.1:8000/ia/llegue/
CV_RESULT_CALLBACK_HMAC_SECRET=el-mismo-valor-de-IA_CALLBACK_HMAC_SECRET
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
| `DB_ENGINE` | `sqlite` en desarrollo por defecto; `postgresql` para usar PostgreSQL y siempre en producción. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Datos de conexión de PostgreSQL. `DB_PORT` usa `5432` si no se define; los demás son obligatorios cuando `DB_ENGINE=postgresql`. |
| `DB_SSLMODE` | Opcional: `prefer` por defecto en desarrollo y `require` en producción. El proveedor puede indicar `verify-full` y un certificado CA. |
| `IA_API_URL` | Dirección de FastAPI más `/api/v1/cv-analyses`. Con `make run-api` local, usá `http://127.0.0.1:8001/api/v1/cv-analyses`. Si FastAPI corre en otra máquina o contenedor, usá una dirección alcanzable desde Django. |
| `IA_CALLBACK_HMAC_SECRET` | Secreto aleatorio para firmar el callback. Debe coincidir con `CV_RESULT_CALLBACK_HMAC_SECRET` de una versión compatible de FastAPI. Obligatorio en producción. |
| `IA_CALLBACK_TOKEN` | Variable heredada: se usa como respaldo de `IA_CALLBACK_HMAC_SECRET` si esta no está definida. No hay un secreto por defecto en el código. |
| `CHANNEL_REDIS_URL` | Redis compartido para avisos WebSocket; debe apuntar a la misma instancia y base `/3` que FastAPI (por defecto `redis://localhost:6379/3`). |
| `IA_API_TOKEN` | Generá un secreto aleatorio distinto del callback y copialo también en `SERVICE_API_TOKEN` de FastAPI. Django lo envía como `Authorization: Bearer ...` para autenticar su llamada al microservicio. |
| `IA_CALLBACK_URL` | Reservada para una URL pública fija; el código actual no la utiliza. Dejala vacía. La URL efectiva del callback se configura en FastAPI con `CV_RESULT_CALLBACK_URL`. |
| `EMAIL_HOST_USER` | Dirección de la cuenta Gmail que enviará correos. Puede quedar vacía si no necesitás email local. |
| `EMAIL_HOST_PASSWORD` | [Contraseña de aplicación de Google](https://support.google.com/accounts/answer/185833?hl=es), no la contraseña habitual de Gmail. Requiere verificación en dos pasos; puede quedar vacía si no enviás correos. |

En `ia_api/backend/.env` se parte de la [plantilla del microservicio](https://github.com/IENbolsa2026/ia_api/blob/ia-match/backend/.env.example):

| Variable | Cómo completarla |
| --- | --- |
| `GROQ_API_KEY` | Creá una clave en la [consola de Groq](https://console.groq.com/keys) y copiala solamente en este `.env`. |
| `SERVICE_API_TOKEN` | Copiá exactamente `IA_API_TOKEN` de Django. Es el Bearer token que restringe `POST` y `GET /api/v1/cv-analyses` al servidor de Django; no es un JWT de usuario. |
| `CV_MODEL` | ID exacto de un modelo disponible en el [catálogo de Groq](https://console.groq.com/docs/models); la plantilla propone `qwen/qwen3.8-27b`. |
| `CV_RESULT_CALLBACK_URL` | URL de Django que recibe el resultado: `http://127.0.0.1:8000/ia/llegue/` en local. Desde un contenedor debe ser una dirección que ese contenedor pueda alcanzar. |
| `CV_RESULT_CALLBACK_HMAC_SECRET` | Copiá exactamente el valor de `IA_CALLBACK_HMAC_SECRET` de Django en una versión de la API que firme callbacks HMAC. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Direcciones de Redis para la cola y los resultados. Con Redis local del `docker compose` del microservicio, conservá `redis://localhost:6379/0` y `/1` respectivamente. |
| `CHANNEL_REDIS_URL` | Redis del canal de notificaciones; misma instancia y base `/3` que Django (`redis://localhost:6379/3` en local). |
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

Para la web y el servicio externo se necesitan estas cuatro terminales;
los dos despachadores Django se inician además, como se indica debajo:

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

En otras dos terminales, desde `BolsaTrabajo`, iniciá los procesos que entregan
los trabajos guardados en la outbox. Sin ellos, los nuevos trabajos pueden
quedar pendientes aunque FastAPI y Celery estén activos:

```bash
# Terminal 5
.venv/bin/python manage.py run_integration_dispatcher --kind extraction --interval 2

# Terminal 6
.venv/bin/python manage.py run_integration_dispatcher --kind match --interval 2
```

El [procedimiento operativo](docs/operaciones/despliegue.md) describe también
la ejecución acotada, el arranque ASGI y la propuesta de despliegue y recuperación.

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
Con ambos servicios apuntando al mismo Redis, el worker también avisa por
WebSocket al postulante conectado. Si la conexión en vivo falla, el navegador
consulta el estado cada 10 segundos. El enlace del aviso lleva a
`/perfil/#cv-analysis`.

## Puertos locales

| Servicio | Puerto | Uso |
| --- | --- | --- |
| Django | 8000 | Interfaz web y callback `/ia/llegue/` |
| FastAPI | 8001 | API de análisis de CV |
| Redis | 6379 | Cola entre FastAPI y Celery |

## Recomendaciones de cursos

Las recomendaciones de cursos aparecen en el detalle de cada match completado.
Priorizan cursos específicos y permiten declarar las habilidades que desarrolla
cada curso desde su formulario. No consumen llamadas adicionales de IA.
Configuración y criterios: [recomendaciones de cursos](docs/funcionalidades/recomendaciones-cursos.md).

## Problemas frecuentes

- **“El servicio de análisis no está configurado”**: falta `IA_API_URL` en el
  `.env` de Django o Django no fue reiniciado.
- **Error de callback 401**: verificá que la API firme el callback HMAC y que
  `IA_CALLBACK_HMAC_SECRET` coincida con `CV_RESULT_CALLBACK_HMAC_SECRET`.
- **Análisis pendiente**: confirma que Redis y `make run-worker` estén activos.
- **Error del modelo de Groq**: revisa `GROQ_API_KEY` y `CV_MODEL` en el `.env`
  del microservicio. Para esta integración se usa `qwen/qwen3.8-27b`.
