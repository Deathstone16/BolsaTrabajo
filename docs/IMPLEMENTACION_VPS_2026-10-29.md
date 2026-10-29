# Implementación y preparación para VPS — 29/10/2026

Esta entrega integra Django con `develop` hasta `1751ce4`, incluidos SMTP y las
plantillas de correo actualizadas, y prepara una versión compatible de la API.
El procedimiento de instalación está en [Despliegue VPS](DESPLIEGUE_VPS.md).

## Cambios en Django

- Se eliminó la integración antivirus: configuración, invocación durante la
  carga, pruebas específicas y variables de los ejemplos. Se conservaron las
  validaciones de formato, tamaño y contenido de documentos y su almacenamiento
  privado.
- El despachador reconoce la cancelación informada por la API. El estado
  cancelado queda como terminal y no vuelve a procesamiento por un evento tardío.
- Se agregó `requirements.lock` para Python 3.11 con versiones y hashes. Se
  instaló y validó en un entorno limpio separado del entorno habitual.
- Se agregó `deploy/check_config.py`, que verifica producción, hosts, orígenes,
  conexiones entre servicios, coincidencia de secretos y configuración SMTP sin
  imprimir credenciales ni modificar datos.
- Se corrigió el callback de producción para pasar por Caddy en `8080`, evitando
  que Django lo redirija a HTTPS antes de confirmar la entrega. El host local se
  incluye explícitamente en `ALLOWED_HOSTS`.
- Se actualizaron la guía de VPS y las referencias operativas. `staticfiles/`
  queda excluido de Git y los archivos de servicio usan finales de línea Linux.

## API compatible

Repositorio: [IENbolsa2026/ia_api](https://github.com/IENbolsa2026/ia_api).
Commit de esta entrega: `803782f`, destinado a `main`.

- Se retiró la integración antivirus y la condición de arranque que la exigía
  en producción, además de su configuración y metadatos de capacidades.
- Se agregó `POST /api/v1/matches/{request_id}/cancel`, autenticado con el token
  de servicio que usa Django.
- La cancelación se guarda en Redis con control transaccional e invalida el
  lease del worker para evitar que un resultado tardío la sobrescriba. También
  se conserva si llega antes de que se registre el trabajo. Los trabajos ya
  completados conservan su resultado.
- Los workers omiten trabajos cancelados y el WebSocket informa ese estado como
  terminal. Una llamada ya enviada al proveedor puede terminar en curso; la
  cancelación evita publicar el resultado y continuar con los siguientes lotes.
- Se agregó su propio `requirements.lock` con hashes, instalado y probado en un
  entorno limpio.

## Limpieza

Se retiraron 418 archivos de caché regenerables entre los dos repositorios y el
código y las pruebas que pertenecían exclusivamente al antivirus. Se conservaron
bases locales, CV, archivos privados, respaldos, secretos y entornos de trabajo.
La limpieza no purga datos de usuarios ni elimina migraciones históricas.

## Validación realizada

| Comprobación | Resultado |
| --- | --- |
| Suite Django con dependencias fijadas | 180 pruebas sin fallos; una omitida por requerir PostgreSQL |
| Regresión adicional del estado cancelado | 1 prueba aprobada |
| Suite API con dependencias fijadas | 269 pruebas aprobadas |
| JavaScript | 4 pruebas aprobadas |
| Verificador de configuración de despliegue | 5 pruebas aprobadas |
| `manage.py check --deploy --fail-level WARNING` | Sin incidencias con configuración sintética de producción |
| `manage.py makemigrations --check --dry-run` | Sin cambios pendientes |
| Sphinx con `-W --keep-going` | Compilación aprobada |

Las pruebas se ejecutaron en Windows con Python 3.11. No enviaron correos reales
ni ejecutaron análisis pagados. La configuración sintética de producción no
verifica una conexión a la base de datos real.

## Pendiente en la VPS

Instalar PostgreSQL y Redis, configurar los dos `.env`, ensayar la restauración
de datos y aplicar migraciones y `collectstatic`. Verificar permisos Linux,
systemd, Caddy, entrega SMTP y credenciales/cuotas de IA. El túnel debe apuntar a
`http://127.0.0.1:8080`; Django y la API escuchan solo en loopback, en `8000` y
`8001`. El despliegue y la validación Linux en el servidor real siguen pendientes.
