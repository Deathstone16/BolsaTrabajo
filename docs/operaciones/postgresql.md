# Integración de PostgreSQL, CV y compatibilidad

> Alcance: registro de integración y verificaciones de su momento. Para preparar un nuevo entorno usá el `README.md` (raíz del repositorio) y el [runbook actual](despliegue.md); los resultados citados aquí no acreditan el estado de otro ambiente.


Estado: integrada y validada el 21 de octubre de 2026.

## Alcance

La rama reúne las mejoras de interfaz y SEO, la configuración de PostgreSQL para producción y el flujo de perfiles CV y compatibilidad v2. Incluye formularios accesibles, navegación de cursos, registro de empresas con estado de revisión, CV privado versionado, requisitos estructurados de ofertas y cálculo de match configurable.

## Decisiones técnicas

- PostgreSQL se selecciona mediante configuración de entorno; la configuración de producción requiere credenciales y validación TLS explícitas.
- Cada carga de CV crea una versión inmutable con hash y metadatos. Los perfiles y resultados se vinculan a esa versión para impedir que un análisis anterior se muestre como vigente después de reemplazar el archivo.
- Los CV se guardan en almacenamiento privado y se entregan mediante una vista autenticada que verifica la propiedad. Las rutas públicas de medios rechazan solicitudes de archivos privados.
- Los trabajos asíncronos y callbacks usan claves de idempotencia, leases y controles de propietario. Al recuperar un trabajo se vuelven a comprobar las versiones antes de publicar resultados.
- Las ofertas distinguen requisitos obligatorios y deseables. El match conserva dimensiones, evaluaciones por requisito, pesos, hash de configuración y fecha de evaluación.
- La clasificación de habilidades respeta el tipo explícito del contrato; los nombres conocidos solo se usan para perfiles antiguos sin clasificación.

## Verificación

La integración pasó **96 pruebas Django sobre PostgreSQL** y **123 pruebas de la API**, además de pruebas dirigidas de presentación, las comprobaciones de Django y la verificación de migraciones sin cambios pendientes.

Las pruebas de seguridad usan archivos y cuentas sintéticos para comprobar acceso por propietario, rechazo de acceso anónimo o cruzado y consistencia de versiones. Los resultados de una evaluación sintética verifican el transporte y la persistencia del contrato; no constituyen una medición de precisión del modelo.

## Operación

Configurar las variables de base de datos, TLS, almacenamiento y servicios externos según `.env.example` y el entorno de despliegue. No registrar documentos, datos personales ni secretos en los logs. Aplicar las migraciones aditivas antes de habilitar workers que escriban los contratos nuevos.
