# Preparación del despliegue en Render

Esta rama parte de `182b3a0`, la versión de Django anterior a la actualización
de `feature/rag-contexto-cv`. El Dockerfile prepara una **demo visual** en Render.
Usa `ientrabajo.settings.render` y deja intacta la configuración local de
`ientrabajo.settings.base`. No ejecuta FastAPI, Celery ni análisis de CV.

## Contenedor web

```sh
docker build -t bolsatrabajo-render:local .
docker run --rm --env-file /ruta/privada/render.env -p 10000:10000 bolsatrabajo-render:local
```

El archivo privado de variables necesita:

```dotenv
DEBUG=false
SECRET_KEY=generar-un-secreto-exclusivo-de-produccion
ALLOWED_HOSTS=nombre-del-servicio.onrender.com
CSRF_TRUSTED_ORIGINS=https://nombre-del-servicio.onrender.com
DB_ENGINE=postgresql
DB_HOST=host-de-neon
DB_PORT=5432
DB_NAME=nombre-de-la-base
DB_USER=usuario
DB_PASSWORD=configurar-en-render
DB_SSLMODE=require
```

Render proporciona `PORT` y `RENDER_EXTERNAL_HOSTNAME`; este último configura
el dominio y el origen CSRF cuando no se definen explícitamente. Para un
dominio propio, configurar ambas listas en Render.

El arranque comprueba Django, aplica migraciones, reúne estáticos y ejecuta
Daphne en `0.0.0.0:$PORT`. WhiteNoise sirve los estáticos con `DEBUG=false`.
El endpoint `/health` comprueba PostgreSQL y devuelve 503 si no está disponible.
La imagen excluye `.env`, bases locales, archivos subidos y respaldos.
El antivirus de CV queda desactivado únicamente en `ientrabajo.settings.render`.
La vista del perfil avisa que solo deben usarse CV ficticios y oculta el botón
de análisis. La ruta de análisis responde 503 para impedir trabajos pendientes.
La capa de notificaciones es local al proceso y no necesita Redis en esta
demo. Un aviso visible en todas las páginas identifica el entorno de prueba.
Las imágenes de cursos y empresas que están versionadas en Git se sirven en la
demo. Los archivos subidos por visitantes quedan en el disco efímero.

## Requisitos pendientes para publicar la aplicación completa

- Conectar PostgreSQL de Neon y comprobar altas, consultas y persistencia.
- Configurar almacenamiento persistente de imágenes, CV y snapshots privados.
  La versión actual usa el filesystem local; Render Free lo pierde al
  reiniciar. El Dockerfile no resuelve todavía ese almacenamiento.
- Alojar FastAPI, Celery y los despachadores de extracción y match.
- Configurar Redis compartido, tokens de servicio, firma HMAC y URLs HTTPS/WSS.
- Adaptar el escaneo de la API a Linux. La versión de API restaurada
  (`b30b33e`) exige un escáner en `MODE=production` y ejecuta argumentos de
  Windows Defender. No desactivar esta comprobación para forzar el arranque.
- Resolver correo transaccional: Render Free bloquea los puertos SMTP usados
  por la configuración Gmail actual.
- Probar registro, login, archivos privados, análisis de CV, callback y match
  antes de considerar completo el despliegue.

## Restricciones verificadas

Render Free no ofrece workers separados ni discos persistentes. Sus servicios
web se suspenden tras inactividad. Redis gratuito pierde su estado al
reiniciarse. Por ello, el arranque del contenedor web no demuestra por sí solo
que el análisis de CV esté disponible ni que los archivos sean persistentes.

Referencias: https://render.com/docs/free y https://render.com/docs/docker.

No se crearon servicios de Render ni se publicaron credenciales desde esta
preparación. El proyecto Neon `BolsaTrabajo` fue creado por el usuario en su
cuenta con plan gratuito; aún no se conectó a la aplicación.
