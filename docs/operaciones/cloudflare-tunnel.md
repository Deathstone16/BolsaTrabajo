# Publicar la web mediante Cloudflare Tunnel

El conector y Django deben ejecutarse en la misma máquina para usar
`http://127.0.0.1:8000` como origen. La API, Redis, PostgreSQL y los callbacks
internos mantienen sus direcciones locales. El navegador usa HTTPS/WSS en el
hostname público; no se necesitan túneles adicionales para esos servicios.

## Conector adicional en Windows

Cuando ya existe un servicio `Cloudflared` para otro túnel, mantenerlo activo.
Para un segundo túnel administrado desde el panel, ejecutar en otra consola:

```powershell
cloudflared.exe tunnel run --token <TOKEN_DEL_SEGUNDO_TUNEL>
```

Cada túnel tiene su propio token. No copiarlo a Git, capturas ni documentación.
La consola debe permanecer abierta; este comando no instala un segundo servicio.
Si el token se compartió, rotarlo desde el panel antes de volver a utilizarlo.

En el panel, seleccionar el túnel, agregar una ruta de aplicación publicada,
elegir subdominio/dominio y configurar el servicio HTTP local. El nombre del
túnel no determina el hostname público. Verificar que el conector aparezca
conectado y que la ruta apunte al servidor correcto.

## Django

Configurar en el `.env` privado, reemplazando el ejemplo por el hostname elegido:

```ini
ALLOWED_HOSTS=localhost,127.0.0.1,bolsa.example.com
CSRF_TRUSTED_ORIGINS=https://bolsa.example.com
TRUST_PROXY_HEADERS=true
```

Mantener Daphne en loopback. Reiniciar los procesos de Django después del cambio;
`configure_ia_match.py` conserva `DEBUG` y `ALLOWED_HOSTS` ya configurados.
Los formularios siguen requiriendo el token CSRF y se rechazan orígenes ajenos.

## Preparación para acceso público

Usar `DEBUG=false`, un `SECRET_KEY` propio y el resto de los ajustes seguros
de `.env.example`. El proyecto exige PostgreSQL con TLS cuando `DEBUG=false`:
configurar TLS en la base o usar una base que ya lo admita. El HTTPS del túnel
no reemplaza el cifrado de la conexión de PostgreSQL.

Con `DEBUG=false`, Daphne no sirve archivos estáticos ni medios. Ejecutar
`manage.py collectstatic --noinput` y configurar un servidor local para entregar
`STATIC_ROOT`, las imágenes públicas y reenviar el resto a Daphne, incluidos los
WebSockets. En ese esquema, apuntar la ruta de Cloudflare al puerto de ese
servidor local. Servir solamente las carpetas de imágenes públicas; nunca
`private_uploads`, `media/postulantes/cv` ni `media/ia/extraction_snapshots`.
Una conexión Healthy del túnel confirma el conector; no verifica estos requisitos
ni el flujo de login, formularios, imágenes y notificaciones.

Referencias: [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/get-started/),
[tokens](https://developers.cloudflare.com/tunnel/reference/tunnel-tokens/),
[proxy HTTPS en Django](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header)
y [estáticos](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/).
