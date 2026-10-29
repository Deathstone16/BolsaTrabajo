# Bolsa de Trabajo IEN (Django)

Aplicación web de la Bolsa de Trabajo IEN. Permite registrar postulantes y
empresas, moderar y consultar ofertas, guardar favoritas, cargar CV privados,
analizarlos con IA, comparar perfiles con ofertas y consultar cursos. El análisis
de CV y la compatibilidad usan el microservicio FastAPI del repositorio
`ia_api/backend`. La aplicación no registra postulaciones ni contrataciones.

Para desplegar los dos servicios en una VPS, seguir
[docs/DESPLIEGUE_VPS.md](docs/DESPLIEGUE_VPS.md).
La instalación de producción usa `requirements.lock` (Python 3.11) y comprueba
los dos entornos con `deploy/check_config.py` antes de iniciar los servicios.

## Documentación del proyecto

La [guía de documentación](docs/README.md) reúne los siete
componentes: requisitos y aceptación, arquitectura y ADR, contratos HTTP y
WebSocket, modelo de datos, operación y pruebas. El
[modelo de datos](docs/datos/modelo-datos.md) incluye el diccionario de las 21
entidades propias y un [diagrama ER editable](docs/datos/modelo-datos.mmd).
La [revisión de limpieza](docs/mantenimiento/analisis-limpieza.md) distingue
residuos locales, documentos históricos y candidatos a simplificar en el código.

## Requisitos

- Python **3.11**, versión usada por los dos lockfiles y las pruebas.
- Git; Redis local o instalado mediante Docker Compose; PostgreSQL para la VPS.
- Node.js y npm solo para pruebas JavaScript y de navegador.
- Claves de Gemini y Groq en el `.env` de la API, según los proveedores elegidos.

## Configuración: de dónde sale cada valor del .env

La plantilla corresponde al flujo actual: Django gestiona la web, **Gemini
extrae CV y Groq evalúa matches** desde la API. `.env.example` usa desarrollo
local; los cambios para VPS están al final de esta sección. Los `.env` privados
no se publican en Git.

### 1. Copiar los ejemplos e instalar

Clonar una versión compatible de cada repositorio (la API actual está en `main`):

```bash
git clone --branch develop https://github.com/Deathstone16/BolsaTrabajo.git BolsaTrabajo
git clone --branch main https://github.com/IENbolsa2026/ia_api.git ia_api
cd BolsaTrabajo
python3.11 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
cp .env.example .env
cd ../ia_api/backend
python3.11 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
cp .env.example .env
```

En Windows usar `py -3.11` en lugar de `python3.11`, `Copy-Item` en lugar de `cp`
y `.venv\Scripts\python.exe` en lugar de `.venv/bin/python`.

### 2. Generar los tres secretos internos

Ejecutar **tres veces**, guardando cada resultado por separado:

```bash
python3.11 -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Resultado | Dónde pegar exactamente el mismo valor | Uso |
| --- | --- | --- |
| Primero | Django: `SECRET_KEY` | Firma de datos de Django; no se comparte con la API. |
| Segundo | Django: `IA_API_TOKEN` y `MATCH_API_TOKEN`; API: `SERVICE_API_TOKEN` | Autenticar llamadas internas Django → API. |
| Tercero | Django: `IA_CALLBACK_HMAC_SECRET`; API: `CV_RESULT_CALLBACK_HMAC_SECRET` | Firmar y verificar los resultados API → Django. |

Estos secretos **se generan**, no se obtienen de Gemini, Groq, CORS ni
Cloudflare. No se necesita un JWT para este flujo. Las variables heredadas
`JWT_SECRET_KEY`, `SERVICE_USER`, `SERVICE_PASSWORD`, `IA_CALLBACK_TOKEN` y la
URL sin uso `IA_CALLBACK_URL` ya no se piden en los ejemplos nuevos. La
compatibilidad con instalaciones anteriores permanece en el código.

### 3. Obtener las claves de Gemini y Groq

**Gemini:** entrar en [Google AI Studio](https://aistudio.google.com/), iniciar
sesión con la cuenta del proyecto, abrir la sección de claves API, seleccionar
o crear el proyecto correspondiente y crear una clave. Copiarla únicamente en
`GEMINI_API_KEY` de `ia_api/backend/.env`. El proceso oficial se describe en
[claves de Gemini](https://ai.google.dev/gemini-api/docs/api-key).

Después, consultar los modelos y los límites del proyecto en AI Studio. Copiar
el ID exacto del modelo en `GEMINI_MODEL` y ajustar los presupuestos `GEMINI_*`
según [los límites reales del proyecto](https://ai.google.dev/gemini-api/docs/rate-limits).
Los números del ejemplo son límites del programa, no cuota garantizada ni un
plan contratado. Una clave distinta del mismo proyecto no crea cuota nueva.

**Groq:** abrir [Groq Console → API Keys](https://console.groq.com/keys), crear
una clave para este servicio y copiarla en `GROQ_API_KEY` de la API. Consultar
[los IDs de modelos](https://console.groq.com/docs/models) para
`MATCH_GROQ_MODEL`. La configuración actual selecciona `MATCH_PROVIDER=groq` y
`LLM_PROVIDER=gemini`; solo al cambiar la extracción a Groq se usa `CV_MODEL`.

En Django, `MATCH_MODEL_VERSION` es una **etiqueta de caché**, no una API key.
Mantenerla alineada con proveedor/modelo de match de la API, por ejemplo
`groq:qwen/qwen3.8-27b:strict-low`. Los IDs del ejemplo son los usados por la
configuración del proyecto; confirmar que la cuenta tenga acceso antes de usarlos.

### 4. Dominios, CORS y URLs: no llevan una clave

**CORS no es una contraseña ni un token.** `BACKEND_CORS_ORIGINS`, que está en
el `.env` de la API, es una lista JSON de orígenes de navegador. Cada origen
incluye esquema, dominio y puerto cuando corresponde; no incluye una ruta.
Referencia: [CORS en FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).

En este proyecto el navegador habla con Django y Django llama a FastAPI desde
el servidor. Por eso la plantilla usa `BACKEND_CORS_ORIGINS=[]`; esas llamadas
internas no necesitan CORS. Si se incorpora un cliente web que llame a una API
publicada, su origen podría ser `["https://app.example.com"]`. Eso no reemplaza
la autenticación ni autoriza exponer `SERVICE_API_TOKEN` en el navegador.

| Variable Django | De dónde sale / cómo escribirla |
| --- | --- |
| `ALLOWED_HOSTS` | Nombres que atiende Django, separados por coma, **sin** esquema ni ruta. Local: `localhost,127.0.0.1`. VPS: tu dominio DNS y `127.0.0.1` para el callback por Caddy. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS con los que se abre la web; por ejemplo `https://bolsa.example.com`. Local sin túnel puede quedar vacío. No es una clave. |
| `TRUST_PROXY_HEADERS` | `false` en local directo; `true` en la VPS detrás del Caddy de esta entrega. |
| `IA_API_URL` / `IA_OFFER_API_URL` | Host y puerto de la API, con `/api/v1/cv-analyses` y `/api/v1/offer-analyses`; ejemplo local en `127.0.0.1:8001`. |
| `MATCH_API_URL` / `MATCH_API_HTTP_URL` | WebSocket `ws://127.0.0.1:8001/api/v1/ws/v1/matches` y base HTTP `http://127.0.0.1:8001/api/v1`. |
| `DEBUG` | `true` en local; `false` en la VPS. |
| `SECURE_SSL_REDIRECT` / `SECURE_HSTS_SECONDS` | Ajustes HTTPS aplicados con `DEBUG=false`; el ejemplo usa `true` y un año. Caddy debe informar `X-Forwarded-Proto: https`. |

La URL inversa se define **en la API**, en `CV_RESULT_CALLBACK_URL`: en local
`http://127.0.0.1:8000/ia/llegue/`; en la VPS de esta entrega
`http://127.0.0.1:8080/ia/llegue/`, pasando por Caddy. Si ambos servicios corren
en contenedores o máquinas distintas, reemplazar loopback por una dirección
alcanzable entre ellos. Los puertos deben estar libres para esta aplicación.

### 5. Base de datos y Redis

Para local dejar `DB_ENGINE=sqlite`: las variables restantes `DB_*` no se usan
y Django crea `db.sqlite3` al migrar. En la VPS usar PostgreSQL:

1. Crear la base y su usuario siguiendo la [guía VPS](docs/DESPLIEGUE_VPS.md).
2. `DB_NAME` y `DB_USER` son los nombres que elegiste al crearlos.
3. `DB_PASSWORD` es la contraseña que asignaste al usuario PostgreSQL. Si es una
   base administrada, obtener estos datos del panel del proveedor.
4. `DB_HOST` es el host del servidor (`127.0.0.1` en la instalación local de la
   VPS) y `DB_PORT` el puerto publicado, normalmente `5432`.
5. Usar `DB_SSLMODE=require` para la conexión TCP de la guía; con un proveedor
   que entregue CA y hostname, configurar `verify-full` según sus instrucciones.
   Para socket Unix local, la guía explica el caso `disable`.

Redis no entrega una API key. Las URLs del ejemplo corresponden a un servidor
local en `127.0.0.1:6379`; los números finales identifican bases lógicas:

| Variable | Base y función |
| --- | --- |
| API: `CELERY_BROKER_URL` | `/0`: cola de tareas. |
| API: `CELERY_RESULT_BACKEND` | `/1`: resultados de Celery. |
| API: `JOB_STORE_REDIS_URL` | `/2`: trabajos y control de cuota. |
| Ambos: `CHANNEL_REDIS_URL` | `/3`: notificaciones; copiar la misma URL en los dos `.env`. |
| API: `MATCH_REDIS_URL` | `/4`: estado de matches. |
| Django: `MATCH_CACHE_REDIS_URL` | `/6`: caché de resultados. |

Si Redis es administrado, usar las URLs/credenciales que entrega su proveedor.
`MATCH_CACHE_TTL_SECONDS=604800` conserva la caché siete días y
`MATCH_REQUESTS_PER_HOUR=20` limita nuevas compatibilidades por postulante:
son parámetros elegidos por la aplicación, no credenciales.

### 6. Conseguir la contraseña SMTP y configurar los correos

Para Gmail:

1. Elegir la cuenta que enviará los correos y activar la verificación en dos
   pasos en su cuenta de Google.
2. Abrir [Contraseñas de aplicación](https://myaccount.google.com/apppasswords)
   y crear una para IEN. Si la opción no aparece, revisar las restricciones de
   la cuenta en la [ayuda oficial](https://support.google.com/accounts/answer/185833?hl=es).
3. Copiar el correo en `EMAIL_HOST_USER` y la contraseña generada en
   `EMAIL_HOST_PASSWORD`; no usar la contraseña habitual de la cuenta.
4. Conservar `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=true`,
   `EMAIL_USE_SSL=false`, `EMAIL_TIMEOUT=15` y el backend SMTP del ejemplo.
5. `DEFAULT_FROM_EMAIL` es el remitente autorizado; vacío usa `EMAIL_HOST_USER`.
   `IEN_CONTACT_EMAIL` es la dirección institucional para enlaces de contacto;
   puede ser distinta del remitente y debe confirmarla la institución.

Para otro proveedor, obtener host, puerto, usuario y contraseña de su panel
SMTP. Para pruebas locales sin enviar mensajes, cambiar `EMAIL_BACKEND` a
`django.core.mail.backends.console.EmailBackend`. No activar TLS y SSL juntos.

### 7. Opciones de documentos y RAG

Los PDF, DOCX, ODT y TXT no requieren una clave extra. Dejar
`CV_LEGACY_CONVERTER_IMAGE` vacío para no habilitar DOC/RTF. Solo al construir
y probar la imagen aislada indicada por el README de la API se coloca su tag
en los dos `.env`; `CV_DOCKER_COMMAND` es el ejecutable Docker y
`CV_LEGACY_CONVERSION_TIMEOUT_SECONDS` su tiempo máximo.

El catálogo vectorial, los límites de IA y el almacenamiento de artefactos se
configuran en el [README de la API](https://github.com/IENbolsa2026/ia_api/blob/main/backend/README.md).
Las contraseñas del catálogo opcional no son las de la base de negocio.

### 8. Cambios obligatorios para VPS y comprobación

Partir de los mismos ejemplos y aplicar los valores de
[Despliegue VPS](docs/DESPLIEGUE_VPS.md): `DEBUG=false`, `MODE=production`,
PostgreSQL, dominio y origen HTTPS reales, `TRUST_PROXY_HEADERS=true`, secretos
propios y callback por `8080`. Los ejemplos locales no hacen estos cambios solos.

```bash
cd /srv/ien/BolsaTrabajo
.venv/bin/python deploy/check_config.py
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy --fail-level WARNING
```

El verificador comprueba configuración sin imprimir secretos; no confirma
credenciales externas ni envía correos. Las migraciones y los servicios se
ejecutan después de preparar o respaldar la base según la guía. Reiniciar API,
Celery, Django y despachadores cuando se cambien sus variables.

Para local, desde Django ejecutar `manage.py migrate` y, si hace falta,
`manage.py createsuperuser` antes de iniciar los procesos siguientes.


## Iniciar los servicios en local


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
.venv/bin/python -m daphne -b 127.0.0.1 -p 8000 ientrabajo.asgi:application
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

## Pruebas

Desde `BolsaTrabajo`, con el entorno y las dependencias instalados:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python -m unittest ientrabajo.test_database_settings ientrabajo.test_proxy_settings
.venv/bin/python manage.py test usuarios categorias ofertas cursos ia matching moderacion emails
npm ci
npm run test:js
npm run test:e2e
```

En Windows reemplazá `.venv/bin/python` por `.\.venv\Scripts\python.exe`.
Las pruebas E2E necesitan los servicios locales en marcha; la variante
`npm run test:e2e:live` usa IA real y consume cuota de Groq. La suite del
microservicio se ejecuta en su propio repositorio. Consultá la
[estrategia de pruebas](docs/pruebas/estrategia.md) para el alcance y los casos
críticos.

## Puertos locales

| Servicio | Puerto | Uso |
| --- | --- | --- |
| Django | 8000 | Interfaz web y callback `/ia/llegue/` |
| FastAPI | 8001 | API de análisis de CV |
| Redis | 6379 | Cola entre FastAPI y Celery |

## Correo de recuperación y aprobación de empresas

Los dos correos salen desde Django con la misma configuración SMTP de
`BolsaTrabajo/.env`; FastAPI y Groq no intervienen. Completá las variables
`EMAIL_*` de la plantilla con una cuenta remitente habilitada por tu proveedor y
reiniciá Django. Para probar localmente sin enviar mensajes reales, cambiá
`EMAIL_BACKEND` a `django.core.mail.backends.console.EmailBackend`: el correo se
mostrará en la terminal del servidor, incluido el enlace de recuperación.

El enlace para recuperar la contraseña se genera con el dominio y el protocolo
de la petición. Antes de usarlo en producción, configurá el dominio en
`ALLOWED_HOSTS` y el proxy HTTPS como indica el
[procedimiento de despliegue](docs/operaciones/despliegue.md); un enlace a
`localhost` solo sirve en tu propia máquina. El formulario responde igual si
la cuenta existe o no, para no revelar usuarios registrados.

Al aprobar una empresa desde moderación o desde el admin de Django, el sistema
guarda la aprobación y manda el aviso al email del oferente con un enlace a su
panel. Guardar nuevamente una empresa ya aprobada no reenvía el correo. Si SMTP
falla, la aprobación permanece guardada: moderación muestra una advertencia y
el admin registra el error. Revisá la configuración antes de reenviar la
notificación por un medio acordado.

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
- **Error del proveedor IA**: comprobar `LLM_PROVIDER` y `MATCH_PROVIDER` en la
  API. El ejemplo actual usa `GEMINI_API_KEY`/`GEMINI_MODEL` para extraer CV y
  `GROQ_API_KEY`/`MATCH_GROQ_MODEL` para matches. Confirmar IDs y cuotas en las
  consolas de las cuentas correspondientes.
