# Despliegue académico gratuito: Django + Render + Neon + IA local

Esta es la adaptación de la guía del docente al stack real del IEN. La guía
propone recursos gratuitos, persistencia externa, Docker, comprobación de salud y
una actualización demostrable. Los ejemplos Laravel/MySQL no se aplican a Django.

**Modalidad acordada:** web pública en Render Free, PostgreSQL y archivos en Neon
Free, IA en la computadora durante la demostración. No es un servicio permanente:
la compatibilidad y el análisis necesitan esa computadora encendida y conectada.
Si cualquier pantalla exige tarjeta, pago o cambio de plan, detenerse y consultar
al docente. No elegir workers, discos o instancias pagos.

## 1. Qué se despliega

| Componente | Dónde | Persistencia |
| --- | --- | --- |
| Django, Daphne y dos despachadores | Un Web Service Docker Free de Render | Datos en Neon |
| Usuarios, ofertas, cursos, perfiles y resultados | PostgreSQL Free de Neon | Externa al contenedor |
| CV, snapshots privados, fotos y logos | Un bucket **privado** de Neon Object Storage | Externa al contenedor |
| Channels y caché de compatibilidad | Key Value Free de Render | Caché descartable |
| FastAPI, Celery y ClamAV | Docker Desktop en la computadora | Volumen local `ia-data` |
| Cola y trabajos de la IA | Redis local en Docker | Volumen local `ia-redis`, AOF |
| Conexión HTTPS hacia la IA | Quick Tunnel de Cloudflare | URL temporal |
| Correo de recuperación/validación | API HTTPS de Brevo, cuenta Free | Remitente verificado |

Se usa `feature/rag-contexto-cv` de BolsaTrabajo. La imagen de IA descarga una
revisión concreta compatible de `IENbolsa2026/ia_api`:
`50794f0d4e732f0b57ed9a557d4776bd22558536`. No depende de que la copia local antigua
esté actualizada. No cambiar esa revisión sin verificar juntos los dos servicios.

El antivirus se mantiene obligatorio en la API (`MODE=production`). Para Docker
Desktop reservar al menos 4 GiB disponibles para la IA y el escáner, además de
los recursos del sistema. El primer inicio descarga las firmas y puede tardar.
No habilitar conversores DOC/RTF ni servicios pagos para esta demo; usar TXT, PDF,
DOCX u ODT ficticios. RAG usa el catálogo léxico incluido; PostgreSQL/pgvector y
embeddings son opcionales y no se aprovisionan en este recorrido gratuito.

## 2. Preparar Neon Free

1. Crear la cuenta del equipo y confirmar el plan **Free**.
2. Crear un proyecto PostgreSQL en una región compatible con Object Storage, por
   ejemplo **AWS US East (N. Virginia)**. Evitar cambiar recursos a un plan pago.
3. En **Connect**, copiar las dos conexiones:
   - Con pooling → `DATABASE_URL`.
   - Sin pooling → `DATABASE_URL_UNPOOLED`, para migraciones.
4. Conservar `sslmode=require` y `channel_binding=require` si Neon los entrega.
   Copiar las URL completas, sin `psql`, comillas externas ni otros comandos.
   Los caracteres especiales de contraseñas deben estar codificados como en la
   URL original. `DATABASE_URL` tiene prioridad sobre los campos `DB_*`.
5. En **Object Storage**, crear el bucket `ien-demo-privado` con acceso
   **private**, nunca `public_read`. Usar la misma rama de Neon que la base.
6. Obtener su endpoint S3, región y credencial con permisos `storage:read` y
   `storage:write`. Los valores van en las variables `AWS_*` del ejemplo.
   Neon requiere direccionamiento `path`; ya está configurado en Django.
7. Si Object Storage no aparece en esa región/cuenta, revisar la disponibilidad
   con el docente. No reemplazarlo por el disco efímero de Render.

El bucket contiene `media/` para imágenes y `private/cv/` para CV y snapshots.
Las imágenes usan enlaces firmados temporales; los CV solo se descargan desde la
vista autenticada de Django. El bucket completo debe permanecer privado.

Esto crea una base nueva. No importa automáticamente SQLite, CV anteriores ni
usuarios reales. Para una demo cargar datos ficticios desde la aplicación/admin.
Antes de migrar datos existentes se necesita un respaldo de la base **y** de los
archivos. El comando heredado `migrar_cv_privados` trabaja con archivos locales;
no sirve para copiar por sí solo una instalación completa a S3.

## 3. Generar los secretos y preparar la IA

Desde la raíz de BolsaTrabajo, en PowerShell, con Docker Desktop iniciado:

```powershell
Copy-Item -LiteralPath deploy/ia.env.example -Destination .env.ia-demo
```

Editar `.env.ia-demo`. Generar dos secretos distintos y largos con un gestor de
contraseñas, o con este comando de Docker (ejecutarlo dos veces):

```powershell
docker run --rm python:3.12-slim-bookworm python -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Valor | Debe coincidir con |
| --- | --- |
| `SERVICE_API_TOKEN` en IA | `IA_API_TOKEN` **y** `MATCH_API_TOKEN` en Render |
| `CV_RESULT_CALLBACK_HMAC_SECRET` en IA | `IA_CALLBACK_HMAC_SECRET` en Render |
| `CV_RESULT_CALLBACK_URL` en IA | `https://DOMINIO-REAL-DE-RENDER/ia/llegue/` |
| `GROQ_API_KEY` en IA | Clave del equipo en Groq; nunca va en el navegador |

Usar una cuenta Groq con cuota gratuita, sin activar facturación. Verificar que
`CV_MODEL` y `MATCH_GROQ_MODEL` estén disponibles en esa cuenta. Si se alcanza
una cuota, esperar o reducir las pruebas; no activar un plan pago. La guía no
garantiza la disponibilidad de un modelo específico de terceros.

Se puede construir y probar la imagen antes de publicar la web:

```powershell
docker compose -f compose.ia-demo.yaml build api
docker compose -f compose.ia-demo.yaml up -d redis api tunnel
docker compose -f compose.ia-demo.yaml logs --tail 100 api
docker compose -f compose.ia-demo.yaml logs --tail 100 tunnel
```

Esperar a que FastAPI indique que inició. El segundo registro muestra una URL
`https://...trycloudflare.com`. Guardarla para los endpoints de Render. Visitar
su raíz debe mostrar que la API está disponible. Los endpoints de negocio
requieren el token de servicio; no compartirlo ni pegarlo en capturas.

El túnel publica únicamente la API. Redis no tiene puerto público y la API solo
se publica en `127.0.0.1:8001` en el host. No agregar autenticación interactiva por
correo al túnel, porque Django es un cliente de servidor.

## 4. Preparar el correo gratuito

Render Free bloquea los puertos SMTP habituales. Por eso el perfil usa HTTPS:

1. Crear una cuenta **Free** de Brevo y completar la activación que solicite.
2. Verificar el remitente y, si el proveedor lo exige, su dominio.
3. Crear una clave de API y colocarla en `BREVO_API_KEY` de Render.
4. Usar el remitente verificado en `DEFAULT_FROM_EMAIL` y el correo institucional
   confirmado en `IEN_CONTACT_EMAIL`.
5. Probar recuperación de contraseña con una cuenta ficticia propia.

No dar este punto por validado solo porque se guardó la clave. El proveedor
puede restringir el envío hasta aprobar la cuenta/remitente. Si no se consigue
un remitente gratuito válido, registrar esta limitación para el docente.

## 5. Publicar la web en Render Free

1. Revisar y subir estos archivos a GitHub en `feature/rag-contexto-cv`.
2. En Render, **New → Blueprint**, conectar el repositorio y seleccionar esa
   rama. Revisar que lea `render.yaml`.
3. Confirmar que **los dos recursos** tengan plan **Free**:
   `ien-bolsa-demo` (web Docker) y `ien-cache-demo` (Key Value).
4. Completar las variables solicitadas, usando `deploy/render.env.example` como
   referencia. No subir el archivo con valores reales al repositorio.
5. Los endpoints de IA usan la URL actual del túnel:

   | Variable | Valor |
   | --- | --- |
   | `IA_API_URL` | `https://TUNEL/api/v1/cv-analyses` |
   | `IA_OFFER_API_URL` | `https://TUNEL/api/v1/offer-analyses` |
   | `MATCH_API_URL` | `wss://TUNEL/api/v1/ws/v1/matches` |
   | `MATCH_API_HTTP_URL` | `https://TUNEL/api/v1` |

6. Render genera `SECRET_KEY` y conecta los dos valores Redis automáticamente.
   No copiar las URL locales `localhost` a Render. No exponer Key Value a Internet.
7. Crear los recursos y revisar los logs: primero instala dependencias y reúne
   estáticos; al arrancar aplica migraciones, comprueba Django y levanta Daphne
   con los dos despachadores. Si una migración falla, el servicio no inicia.
8. Copiar el dominio real que asignó Render. El perfil permite automáticamente
   ese hostname para Django y CSRF. Si se agrega un dominio propio, definir
   también `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con valores exactos.
9. Actualizar `CV_RESULT_CALLBACK_URL` en `.env.ia-demo` con el dominio real y
   recrear la API, conservando el túnel para no cambiar su URL:

```powershell
docker compose -f compose.ia-demo.yaml up -d --force-recreate api
```

No hace falta `preDeployCommand`, consola remota paga, cron ni Background Worker.
El despliegue automático queda desactivado: seleccionar manualmente el commit a
publicar después de revisar los cambios.

## 6. Crear el administrador sin una consola paga

Construir la imagen web en la computadora. Crear `.env.render` copiando el
ejemplo y completar conexiones reales. **No** sobrescribir el `.env` de desarrollo.
En este archivo local los Redis deben ser accesibles desde donde se ejecute el
comando si se va a levantar el servidor completo; `createsuperuser` solo necesita
la base y la configuración completa, no abre conexiones a Redis/S3.

```powershell
docker build -t ien-bolsa-demo .
Copy-Item -LiteralPath deploy/render.env.example -Destination .env.render
docker run --rm -it --env-file .env.render ien-bolsa-demo python manage.py createsuperuser
```

Hacerlo después de que Render haya aplicado las migraciones. Introducir una
contraseña propia; nunca usar credenciales de ejemplo. Entrar a `/admin/` y crear
categorías/cursos de muestra y los usuarios necesarios para la demostración.

## 7. Verificar antes de presentar

- [ ] `/health/` devuelve `200` y `{"status":"ok"}`. Si la base o Redis fallan,
      responde `503`, sin mostrar credenciales. No comprueba la IA ni el correo.
- [ ] Home carga con estilos e imágenes; cursos y ofertas de muestra aparecen.
- [ ] Registro/login, búsqueda, filtros y detalle de ofertas funcionan.
- [ ] Subir un CV **ficticio**, pedir análisis y comprobar que sale de pendiente.
- [ ] Revisar resultado, guardar habilidades y consultar compatibilidad/cursos.
- [ ] Como oferente aprobado, crear, editar y desactivar una oferta.
- [ ] Probar recuperación de contraseña y correos de validación del oferente.
- [ ] Un usuario diferente no puede descargar el CV ajeno; sin sesión tampoco.
- [ ] Los objetos bajo `private/cv/` no abren con una URL anónima de Neon.
- [ ] Reiniciar/republicar **la web en Render**, volver a entrar y verificar la
      misma oferta, usuario, CV, foto y resultado. No basta recargar el navegador.
- [ ] Guardar evidencia del plan Free, commit, logs, URL, persistencia y flujo.

Las pruebas de código no sustituyen este recorrido en las cuentas reales.

## 8. Demostrar una actualización y volver atrás

1. Realizar un cambio pequeño visible, revisarlo y subir su commit a la rama.
2. Render → servicio web → **Manual Deploy → Deploy a specific commit**.
3. Esperar estado saludable y verificar el cambio y la persistencia.
4. Si se necesita volver atrás, desplegar el commit anterior compatible. Esto
   **no revierte** automáticamente las migraciones ni los datos de Neon.
   Respaldar antes de cambios de esquema destructivos y evitar esos cambios
   durante la presentación.

## 9. Apagar y volver a iniciar la demo

```powershell
docker compose -f compose.ia-demo.yaml stop
docker compose -f compose.ia-demo.yaml up -d
docker compose -f compose.ia-demo.yaml logs --tail 100 tunnel
```

Si el túnel cambió, actualizar los cuatro endpoints de Render y guardar/reiniciar
la web. No usar `down -v`: elimina los volúmenes de cola, firmas y archivos de la
IA. Reiniciar la API antes de cada jornada para actualizar las firmas antivirus.
No suspender la computadora mientras haya trabajos en curso.

## Limitaciones del recorrido gratuito

- Render Free se suspende tras inactividad y tarda en despertar. No usar pings
  artificiales para evitarlo. Hay cuotas de horas, transferencia y memoria.
- Key Value Free es efímero: se puede perder la caché y la notificación en vivo.
  Los datos de negocio y resultados se conservan en PostgreSQL.
- La cola local de la IA necesita conservar sus volúmenes. Las tareas en curso
  pueden necesitar reintento si se interrumpe la computadora o el túnel.
- Los despachadores funcionan mientras el servicio web esté despierto. Abrir la
  web antes de probar análisis y esperar su inicio. Si Render está suspendido,
  el callback puede requerir el reintento previsto en Celery.
- Neon y Groq también tienen cuotas Free. Revisarlas en sus paneles antes de la
  presentación. No activar facturación como solución a un límite.
- La configuración inicial no migra archivos históricos ni convierte DOC/RTF.
- Este recorrido es una demostración académica; no garantiza disponibilidad
  permanente de la IA, correo entregado ni ejecución completamente en la nube.

## Fuentes oficiales consultadas el 26/10/2026

- [Render Free: límites, disco y SMTP](https://render.com/docs/free)
- [Blueprint y planes explícitos](https://render.com/docs/blueprint-spec)
- [Neon: planes](https://neon.com/pricing)
- [Neon Object Storage: inicio](https://neon.com/docs/storage/get-started)
- [Neon: autenticación de almacenamiento](https://neon.com/docs/storage/authentication)
- [Neon: compatibilidad S3 y acceso privado](https://neon.com/docs/storage/s3-compatibility)
- [ClamAV: memoria recomendada](https://docs.clamav.net/manual/Installing/Docker.html)
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Brevo: correo transaccional HTTPS](https://developers.brevo.com/docs/send-a-transactional-email)
