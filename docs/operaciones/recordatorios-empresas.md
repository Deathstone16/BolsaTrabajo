# Solicitudes de empresas y avisos inmediatos

Las altas y los reenvíos a revisión generan una solicitud persistente. El header
administrativo muestra las pendientes y el historial permite filtrar pendientes,
aprobadas y rechazadas. Solo staff puede acceder.

## Correo

- `IEN_REVIEW_EMAILS`: destinatarios separados por coma. Si está vacío, se usan
  los emails de cuentas staff activas. No se usa automáticamente el remitente SMTP.
- `IEN_PUBLIC_URL=https://empleo.ejemplo.org`: origen público para los enlaces.
- Configurar el backend SMTP, sus credenciales y `DEFAULT_FROM_EMAIL`.
- `IEN_COMPANY_REMINDER_HOURS` ya no configura demoras. El valor interno cero se
  conserva únicamente para compatibilidad con migraciones históricas.

Al confirmar el alta o el reenvío a revisión en la base se intenta enviar el aviso
correspondiente a esa solicitud. No hay espera de 24 horas ni separación mínima
entre solicitudes diferentes. No se envía antes de confirmar la transacción: si
el alta se revierte, no se genera el correo. Guardar otra vez un perfil pendiente
no crea otro aviso. La confirmación del proveedor SMTP no garantiza llegada a la
bandeja de entrada ni un tiempo exacto de entrega.

Los registros existentes conservan su fecha `recordar_desde`; este cambio no
notifica de forma masiva solicitudes antiguas ni altera datos de demostración.
Consultar el historial no cambia el estado ni vuelve a enviar el correo.

Si el proveedor falla, se conserva la solicitud y el comando permite reintentar
tras un minuto. El proceso de reintentos debe estar activo. Un lease en la base
impide enviar el mismo lote simultáneamente desde dos procesos. Si una solicitud
nueva coincide con un envío reservado, queda disponible para el siguiente ciclo.
Una solicitud ya aprobada/rechazada no se incluye en los reintentos. Como con
cualquier envío SMTP, un corte tras aceptar el mensaje y antes de registrar ese
resultado puede causar un reenvío; no se promete entrega exactamente una vez.

## Ejecución

El primer intento se realiza al confirmar la solicitud y no depende del proceso
periódico. El contacto SMTP puede añadir tiempo a esa petición; el timeout se
configura con `EMAIL_TIMEOUT`. Un fallo no debe deshacer el registro.

`deploy/start.py` inicia el proceso de reintentos. En VPS también se puede instalar
`deploy/systemd/ien-company-reminders.service`, adaptando usuario, rutas y archivo
de entorno al servidor. Mantener SMTP y destinatarios iguales en ambos procesos.

En desarrollo, junto a `runserver`, ejecutar en otra terminal:

```sh
.venv/bin/python manage.py run_integration_dispatcher --kind company-reminders --interval 60
```

Para una sola pasada: `python manage.py dispatch_company_reminders`.
Las pruebas usan una bandeja en memoria y no envían correo real.
