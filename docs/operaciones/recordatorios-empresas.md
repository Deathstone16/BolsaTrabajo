# Solicitudes de empresas y recordatorios

Las altas y los reenvíos a revisión generan una solicitud persistente. El header
administrativo muestra las pendientes y las últimas cinco solicitudes. El historial
completo permite filtrar pendientes, aprobadas y rechazadas. Solo staff puede verlo.
Las solicitudes anteriores a la instalación se incorporan como pendientes con un
plazo nuevo; la migración no envía correo.

## Correo

- `IEN_COMPANY_REMINDER_HOURS=24`: espera mínima desde la solicitud y separación
  mínima entre resúmenes. Puede haber demora adicional hasta el siguiente resumen.
- `IEN_REVIEW_EMAILS`: direcciones separadas por coma. Si está vacío, se usan los
  emails de cuentas staff activas. No se utiliza automáticamente el remitente SMTP.
- `IEN_PUBLIC_URL=https://empleo.ejemplo.org`: origen público para los enlaces.
- Configurar también el backend de correo y `DEFAULT_FROM_EMAIL` existentes.

Cada solicitud recibe un recordatorio cuando lleva al menos 24 horas pendiente.
Se agrupan las solicitudes vencidas en un mensaje y no se repiten recordatorios
exitosos de la misma solicitud. Revisar una solicitud antes del vencimiento evita
su recordatorio. Consultar el historial no la resuelve ni cancela el recordatorio.
Si el correo falla, se conserva el trabajo y se vuelve a intentar en una hora.
Un lease en base de datos evita que dos procesos envíen el mismo lote a la vez.
Como en cualquier envío SMTP, un corte tras aceptar el mensaje y antes de confirmar
el resultado en la base puede causar un reenvío; no se promete entrega exactamente una vez.

## Ejecución

Aplicar `python manage.py migrate`. `deploy/start.py` inicia el proceso de correo
junto a los despachadores existentes. Para VPS instalar y habilitar también
`deploy/systemd/ien-company-reminders.service`.

En desarrollo, junto a `runserver`, ejecutar en otra terminal:

```sh
.venv/bin/python manage.py run_integration_dispatcher --kind company-reminders --interval 60
```

Para una sola pasada: `python manage.py dispatch_company_reminders`.
No depende de visitas al sitio ni se programan esperas dentro de los requests.
El proceso debe estar activo para enviar; si estuvo detenido, retoma las solicitudes
vencidas al reiniciarse. Las pruebas usan una bandeja en memoria y no envían correo real.
