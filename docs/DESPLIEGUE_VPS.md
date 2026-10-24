# Despliegue de IEN Bolsa en una VPS Ubuntu

Esta guía corresponde a los dos repositorios que forman la aplicación: Django
`Deathstone16/BolsaTrabajo` y FastAPI `IENbolsa2026/ia_api/backend`. Los procesos
son Django/Daphne, FastAPI/Uvicorn, Celery, dos despachadores de Django, Redis,
PostgreSQL, Caddy y `cloudflared`. El catálogo vectorial de habilidades es
opcional; sin él la API usa el catálogo JSON local. Se probó la configuración en
el código, pero **los comandos de Linux deben verificarse en la VPS real** antes
de dirigir tráfico al nuevo servidor.

## 1. Preparación y datos existentes

Usar Ubuntu 24.04 LTS, una cuenta SSH administrativa y espacio para la base,
archivos subidos, logs y copias. Elegir el mismo commit compatible de **ambos**
repositorios; no desplegar `develop` de uno con una rama distinta del otro sin
verificar el contrato de extracción y callback. Preparar una ventana de
mantenimiento: el túnel hoy puede apuntar al equipo Windows y los usuarios
podrían seguir modificando datos durante la copia.

En la VPS, con una cuenta con `sudo`:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates postgresql postgresql-client redis-server caddy clamav clamav-freshclam libgomp1 acl
sudo useradd --system --create-home --home-dir /home/ienapp --shell /bin/bash ienapp
sudo install -d -o ienapp -g ienapp -m 0750 /srv/ien
sudo systemctl enable --now postgresql redis-server
```

Instalar `cloudflared` desde el paquete oficial de Cloudflare para la
arquitectura de la VPS. No instalar el servicio de túnel todavía: primero
terminar las pruebas locales. Usar [la guía oficial de paquetes de
Cloudflare](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).

## 2. Código y Python

Python **3.11** sirve para los dos repositorios. Como Ubuntu 24.04 trae otra
versión por defecto, instalar 3.11 con `uv` para `ienapp`:

```bash
sudo -iu ienapp
curl -LsSf https://astral.sh/uv/install.sh | sh
/home/ienapp/.local/bin/uv python install 3.11
git clone https://github.com/Deathstone16/BolsaTrabajo.git /srv/ien/BolsaTrabajo
git clone https://github.com/IENbolsa2026/ia_api.git /srv/ien/ia_api
cd /srv/ien/BolsaTrabajo
git checkout feature/rag-contexto-cv
/home/ienapp/.local/bin/uv venv --python 3.11 .venv
/home/ienapp/.local/bin/uv pip install --python .venv/bin/python -r requirements.txt
cd /srv/ien/ia_api/backend
git checkout feature/rag-contexto-cv
/home/ienapp/.local/bin/uv venv --python 3.11 .venv
/home/ienapp/.local/bin/uv pip install --python .venv/bin/python -r requirements.txt
exit
```

Si el repositorio de la API es privado, usar una llave SSH de despliegue de
solo lectura y clonar por SSH. Registrar los SHA de ambos commits antes de
actualizar; así se puede volver a la pareja anterior.

## 3. PostgreSQL y Redis

Crear usuario y base de negocio. Reemplazar la contraseña de ejemplo antes de
ejecutar, sin guardarla en el historial del shell. El `psql` siguiente es un
esquema de los comandos SQL, no un secreto para copiar literalmente:

```sql
CREATE ROLE ienapp LOGIN PASSWORD 'CLAVE_LARGA_ALEATORIA';
CREATE DATABASE ien_bolsa OWNER ienapp;
```

Ejecutarlos dentro de `sudo -u postgres psql`. En `.env` usar
`DB_HOST=127.0.0.1`, `DB_PORT=5432`, `DB_SSLMODE=require`. Comprobar con `psql`
que PostgreSQL acepta TLS local (`\conninfo` debe indicar SSL); si el servidor
no lo ofrece, configurar SSL en PostgreSQL antes de iniciar Django. Para una
base remota usar `verify-full` con CA y restringir red. Como alternativa local,
`DB_HOST=/var/run/postgresql` selecciona socket Unix y `DB_SSLMODE=disable`;
configurar `pg_hba.conf` para autenticar la cuenta de la aplicación. Nunca usar
`disable` para un host TCP. Redis debe escuchar solo en loopback; las bases
Redis usadas son 0 (cola), 1 (resultados), 2 (trabajos), 3 (Channels), 4
(match) y 6 (caché Django). Comprobar `redis-cli ping` → `PONG`.

## 4. Secretos y configuración

Crear `/srv/ien/BolsaTrabajo/.env` y `/srv/ien/ia_api/backend/.env` a partir de
sus `.env.example`, propiedad `ienapp`, permisos `0600`. Generar secretos
independientes con `python -c 'import secrets; print(secrets.token_urlsafe(48))'`.
La clave de Gemini que se compartió anteriormente en el chat debe **rotarse**
antes de este despliegue. No pegar tokens del túnel, LLM ni contraseñas en Git.

Valores indispensables de Django:

```dotenv
DEBUG=false
SECRET_KEY=<nuevo-secreto-django>
ALLOWED_HOSTS=bolsa.neadev.com
CSRF_TRUSTED_ORIGINS=https://bolsa.neadev.com
TRUST_PROXY_HEADERS=true
SECURE_SSL_REDIRECT=true
DB_ENGINE=postgresql
DB_NAME=ien_bolsa
DB_USER=ienapp
DB_PASSWORD=<clave-postgresql>
DB_HOST=127.0.0.1
DB_PORT=5432
DB_SSLMODE=require
IA_API_URL=http://127.0.0.1:8001/api/v1/cv-analyses
IA_OFFER_API_URL=http://127.0.0.1:8001/api/v1/offer-analyses
IA_API_TOKEN=<token-servicio>
IA_CALLBACK_HMAC_SECRET=<secreto-callback-hmac>
MATCH_API_URL=ws://127.0.0.1:8001/api/v1/ws/v1/matches
MATCH_API_HTTP_URL=http://127.0.0.1:8001/api/v1
MATCH_API_TOKEN=<token-servicio>
CHANNEL_REDIS_URL=redis://127.0.0.1:6379/3
MATCH_CACHE_REDIS_URL=redis://127.0.0.1:6379/6
CV_SCAN_ENABLED=true
CV_SCAN_BACKEND=clamav
CV_SCAN_COMMAND=/usr/bin/clamscan
```

Valores indispensables de FastAPI (con los mismos secretos compartidos):

```dotenv
MODE=production
LLM_PROVIDER=gemini
MATCH_PROVIDER=groq
GEMINI_API_KEY=<clave-nueva-de-gemini>
GROQ_API_KEY=<clave-de-groq>
SERVICE_API_TOKEN=<token-servicio>
CV_RESULT_CALLBACK_URL=http://127.0.0.1:8000/ia/llegue/
CV_RESULT_CALLBACK_HMAC_SECRET=<secreto-callback-hmac>
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
JOB_STORE_REDIS_URL=redis://127.0.0.1:6379/2
CHANNEL_REDIS_URL=redis://127.0.0.1:6379/3
MATCH_REDIS_URL=redis://127.0.0.1:6379/4
CV_SCAN_ENABLED=true
CV_SCAN_BACKEND=clamav
CV_SCAN_COMMAND=/usr/bin/clamscan
```

Copiar del `.env.example` los presupuestos y modelos confirmados para la cuenta
real. `GEMINI_REQUESTS_PER_DAY` y demás límites locales deben coincidir con la
cuota visible en AI Studio; el plan gratuito puede cambiar. Configurar
`EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en Django si se envían correos.
No activar DOC/RTF (`CV_LEGACY_CONVERTER_IMAGE`) sin construir y probar la
imagen aislada de LibreOffice.

Actualizar firmas de ClamAV antes de habilitar cargas. En Ubuntu el servicio
`clamav-freshclam` suele actualizar automáticamente; verificar que descargó
firmas. Probar `clamscan --no-summary /etc/hosts` y confirmar código de salida
0. Los códigos 1 (infectado) y 2 (error) bloquean la carga. En producción el
arranque de FastAPI exige el escáner configurado.

## 5. Migraciones y archivos

Si es una instalación nueva:

```bash
sudo -iu ienapp
cd /srv/ien/BolsaTrabajo
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
.venv/bin/python manage.py createsuperuser
exit
```

**Si hay datos reales en Windows**, no empezar con una base vacía. Dejar
terminar los trabajos pendientes de Celery, detener nuevas escrituras en el
origen, hacer una copia verificable y transferir por
canal cifrado la base, `media/` y `private_uploads/`. Los CV están en rutas
privadas; `media/postulantes/cv` y `media/ia/extraction_snapshots` históricos
tampoco se deben publicar. Dar propiedad `ienapp` y permisos restrictivos a
`private_uploads/` y `media/` en la VPS. Los archivos de `media/cursos/` y
`media/empresas/` versionados en Git pueden estar referenciados por la base.

- Origen PostgreSQL: `pg_dump -Fc` con el mismo usuario, transferir el archivo
  y restaurar con `pg_restore` en la base vacía; aplicar después `migrate`.
- Origen SQLite: con la aplicación detenida, guardar `db.sqlite3`, ejecutar
  `manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes
  --exclude auth.permission > datos.json` en la versión de código del origen;
  en la VPS ejecutar primero `migrate` y luego `loaddata datos.json`. Verificar
  conteos, referencias, usuarios y secuencias PostgreSQL en un ensayo antes
  del corte. Los datos exportados contienen información personal: usar
  almacenamiento cifrado, permisos `0600` y borrarlos al terminar.

No borrar la base ni los archivos originales hasta haber comprobado usuarios,
ofertas, CV, imágenes y permisos desde la VPS. El traspaso SQLite→PostgreSQL
es un ensayo obligatorio, no una operación automática del script de deploy.

## 6. Catálogo vectorial de habilidades (opcional)

Para RAG completo, instalar Docker con el procedimiento oficial y ejecutar
desde `/srv/ien/ia_api/backend`:

```bash
docker compose -f docker-compose.yml -f docker-compose.rag.yml up -d skill_catalog_postgres
.venv/bin/python -m tools.import_skill_catalog app/data/skill_catalog.v1.json --initialize --embed
```

Definir `SKILL_CATALOG_DB_PASSWORD` para Compose y
`SKILL_CATALOG_DATABASE_URL=postgresql://skill_catalog:<clave>@127.0.0.1:5434/ien_skill_catalog`
en el `.env` privado de la API. `--embed` descarga un modelo de embeddings en
la primera ejecución y requiere memoria/disco. Reiniciar API y Celery luego de
configurarla. El catálogo no guarda CV. Respaldar también el volumen
`skill_catalog_data` si se agregan conceptos propios; para el catálogo base
se puede reconstruir mediante el comando de importación.

## 7. Procesos y proxy local

Los archivos listos para copiar están en `deploy/systemd/` y
`deploy/Caddyfile`. Sus rutas presuponen `/srv/ien` y el usuario `ienapp`.
Antes de habilitarlos, validar permisos de lectura para Caddy en `staticfiles/`
y solo medios públicos. Caddy debe poder atravesar los directorios padre;
se recomienda ACL de lectura para el usuario `caddy`, nunca para
`private_uploads/`. Ejemplo:

```bash
sudo install -d -o ienapp -g ienapp -m 0755 /srv/ien/BolsaTrabajo/media/postulantes/fotos
sudo setfacl -m u:caddy:--x /srv/ien /srv/ien/BolsaTrabajo
sudo setfacl -R -m u:caddy:rX /srv/ien/BolsaTrabajo/staticfiles /srv/ien/BolsaTrabajo/media/cursos /srv/ien/BolsaTrabajo/media/empresas /srv/ien/BolsaTrabajo/media/postulantes/fotos
sudo find /srv/ien/BolsaTrabajo/media/cursos /srv/ien/BolsaTrabajo/media/empresas /srv/ien/BolsaTrabajo/media/postulantes/fotos -type d -exec setfacl -m d:u:caddy:rX {} +
sudo cp /srv/ien/BolsaTrabajo/deploy/systemd/*.service /etc/systemd/system/
sudo cp /srv/ien/BolsaTrabajo/deploy/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now ien-api ien-django ien-celery ien-extraction-dispatcher ien-match-dispatcher caddy
```

Crear directorios de medios faltantes antes de aplicar ACL. Caddy entrega `/static/`, cursos, imágenes de empresas y fotos
de postulantes; niega el resto de `/media/`. Daphne y FastAPI solo escuchan en
`127.0.0.1` y Caddy acepta conexiones solo por loopback. El proxy pone
`X-Forwarded-Proto: https` para que Django reconozca la conexión externa del
túnel y genere cookies/redirects seguros. No configurar otro proxy público que
pueda inyectar esa cabecera.

## 8. Cloudflare Tunnel y firewall

En Zero Trust, editar el túnel **bolsa_trabajo** y fijar la aplicación pública
`bolsa.neadev.com` con origen `http://127.0.0.1:8080`. Instalar en la VPS el
conector de ese túnel siguiendo el comando del panel, preferiblemente mediante
el servicio Linux oficial. El token es secreto: no pegarlo en tickets ni
guardarlo en el repositorio. Confirmar `systemctl status cloudflared`, estado
*Healthy* del conector nuevo y respuesta del origen antes de retirar el
conector de Windows. Mantener la política Cloudflare Access existente sobre
`bolsa.neadev.com`; probarla desde una sesión privada.

Permitir solo SSH entrante en el firewall de la VPS (y conservar una sesión SSH
abierta al habilitarlo). No publicar 8000, 8001, 8080, 5432, 5434 ni 6379.
Cloudflared establece una conexión saliente con Cloudflare. Evitar que dos
conectores apunten a aplicaciones o bases divergentes durante la migración.

## 9. Verificación y operación

```bash
sudo systemctl --no-pager --full status ien-django ien-api ien-celery ien-extraction-dispatcher ien-match-dispatcher caddy cloudflared
sudo journalctl -u ien-api -u ien-celery -u ien-django -n 100 --no-pager
curl -I -H 'Host: bolsa.neadev.com' http://127.0.0.1:8080/
curl -I -H 'Host: bolsa.neadev.com' http://127.0.0.1:8080/static/admin/css/base.css
curl -I -H 'Host: bolsa.neadev.com' http://127.0.0.1:8080/media/postulantes/cv/secreto.pdf
```

La última URL debe responder 404. Después de habilitar el túnel, probar login,
carga de CV, análisis completo, visualización del perfil, publicación de oferta,
match, recomendación de cursos y correo saliente. Verificar que el CV llegue a
`private_uploads`, que Celery y los dos despachadores procesen trabajos y que
los callbacks HMAC no den 401/403. Para revisar servicios:
`journalctl -fu ien-celery`, `journalctl -fu ien-api` y
`journalctl -fu ien-extraction-dispatcher`.

Programar respaldo automático de PostgreSQL (por ejemplo `pg_dump -Fc`),
`media/`, `private_uploads/` y secretos `.env` en un destino cifrado **fuera de
la VPS**. Ensayar restauración periódica. Monitorizar espacio, memoria,
servicios, salud del túnel y límites/rate limits de Gemini y Groq. Fijar una
versión probada de ambos repositorios para cada release; el rollback requiere
volver los dos SHA compatibles y restaurar la base si hubo migraciones no
reversibles. Ejecutar `manage.py migrate`, `collectstatic`, reiniciar servicios
y repetir los flujos después de cada actualización.

Como base para una tarea programada, `pg_dump -h 127.0.0.1 -U ienapp -Fc
ien_bolsa > /ruta/segura/ien_bolsa.dump` y una copia incremental de
`/srv/ien/BolsaTrabajo/media` y `private_uploads` deben salir de la VPS con
retención y cifrado. El destino, credenciales, frecuencia y restauración se
deben concretar antes del corte. Registrar además
`git -C /srv/ien/BolsaTrabajo rev-parse HEAD`,
`git -C /srv/ien/ia_api rev-parse HEAD` y las versiones instaladas de paquetes
Python de cada `.venv` para repetir la misma release.

Referencias: [Django: lista de producción](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[Django: archivos estáticos](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/),
[Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/get-started/),
[Caddy `reverse_proxy`](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy),
[ClamAV](https://docs.clamav.net/manual/Usage/Scanning.html),
[PostgreSQL/libpq](https://www.postgresql.org/docs/current/libpq-connect.html).
