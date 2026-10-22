# Estrategia y plan de pruebas

## Objetivo

Comprobar que los flujos de postulantes y empresas funcionan con PostgreSQL,
la API y los workers, y que el navegador presenta sus resultados sin filtrar CV
entre cuentas ni reutilizar perfiles obsoletos. La ejecución debe ser repetible
y dejar evidencia verificable, incluso cuando falla.

## Alcance y prioridad

| Prioridad | Riesgo | Verificación |
|---|---|---|
| P0 | Acceso al CV o al match de otra persona | Propietario, otra cuenta y anónimo; rutas privadas y medios públicos |
| P0 | Resultado de un CV anterior presentado como vigente | Reemplazo de CV, versiones, callbacks tardíos y respuesta 409 al recalcular |
| P0 | Pérdida o duplicación de tareas | Idempotencia, leases, recuperación, reintentos y entrega de callbacks |
| P0 | El usuario no puede completar el flujo | Login, carga de CV, análisis y compatibilidad desde Chromium |
| P1 | Requisitos de oferta o pesos incorrectos | Formularios, clasificación obligatoria/deseable, contratos v2 y scoring |
| P1 | Error detrás del túnel | Host permitido, HTTPS del proxy, CSRF válido y rechazo de otro origen |
| P1 | JavaScript falla o el resultado no se actualiza | Eventos, notificaciones, estado final, errores de página y recarga |
| P2 | Regresión de presentación | Navegación móvil, capturas y elementos accesibles |

## Capas de prueba

1. **API:** ejecutar la suite completa de contratos, parsers, puntuación,
   checkpoints, recuperación y cuota con proveedor controlado. Estas pruebas no
   consumen IA externa y deben ser deterministas.
2. **Django/PostgreSQL:** ejecutar las pruebas de aplicaciones contra la base
   temporal creada por Django; comprobar permisos, formularios, versiones,
   migraciones e integración de callbacks.
3. **Configuración y JavaScript:** verificar TLS/base/proxy/CSRF y los módulos de
   interfaz con sus runners. No considerar esto una prueba de navegador.
4. **E2E Playwright:** Chromium, servidor local real, cuentas y archivos
   sintéticos. Verificar acciones y resultados visibles; las comprobaciones
   adicionales de HTTP/DB confirman privacidad, vigencia y persistencia.
5. **Integración IA real:** habilitar deliberadamente `--live-ai` para recorrer
   extracción y matching con proveedor real, respetando la cuota. Reportar por
   separado las esperas y errores del proveedor. Un porcentaje válido no es una
   medición de precisión del modelo.

## Datos y aislamiento

Las suites de Django usan su base de pruebas; la API usa sus dobles de prueba.
El smoke E2E usa el stack local existente y crea identidades `example.invalid`
con un identificador único. Solo elimina filas, sesiones y archivos de esas
identidades. No publica pesos globales, no altera cuentas existentes, no manda
correos ni modifica Cloudflare Access. Credenciales, videos, trazas y estado de
ejecución se guardan en `.test-artifacts/`, fuera de Git.

El runner rechaza hosts remotos y exige autorización explícita para usar IA.
Cloudflare Access se verifica por separado: su autenticación necesita una
identidad autorizada y no debe puentearse para automatizar el navegador.

## Secuencia y criterio de salida

Ejecutar primero API y Django/configuración/JS en paralelo. Corregir los fallos
reproducibles, repetir el conjunto afectado y verificar la suite completa cuando
se modifica lógica compartida. Recargar únicamente los procesos que necesiten
el código corregido antes del E2E.

Finalizar con Playwright: acceso, permisos de empresa, carga y privacidad del CV,
extracción real cuando se autoriza, consulta de oferta, match y reemplazo de CV.
Usar esperas por estado o aserciones del navegador, sin sleeps para decidir éxito.
Guardar reporte HTML/JSON, capturas y trazas; conservar los intentos fallidos.

Aceptar la ejecución cuando pasan los controles P0, no hay errores JavaScript
propios sin explicar y la limpieza queda confirmada. Un caso omitido, una
dependencia externa fallida o una prueba con dobles debe identificarse como tal;
no reportarlo como E2E real aprobado. Los tiempos son observaciones, no un SLA.

## Reejecución

Consultar `package.json` y `playwright.config.cjs`. `npm run test:js` ejecuta la
suite JavaScript. `npm run test:e2e` ejecuta los casos de navegador sin inferencia;
`npm run test:e2e:live` autoriza la cadena real de IA. El entorno Python del
proyecto y los servicios locales deben estar disponibles.
