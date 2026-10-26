# Resultados de pruebas — 21 de octubre de 2026

## Resultado

Se ejecutó la [estrategia de testing](../plan-integracion.md). La verificación final
aprobó 240 pruebas entre API, Django, configuración, JavaScript y navegador.

| Capa | Resultado | Alcance |
|---|---|---|
| API | 125 aprobadas | Contratos v2, documentos, cuota, leases, recuperación y callbacks |
| Django/PostgreSQL | 98 aprobadas | Usuarios, ofertas, moderación, IA, matching, cursos y categorías |
| Configuración | 9 aprobadas | Base/TLS, proxy HTTPS y CSRF con origen permitido y ajeno |
| JavaScript | 4 aprobadas | Notificaciones y habilidades del dashboard |
| Playwright/Chromium | 4 aprobadas, 0 omitidas | Flujos reales de interfaz y cadena IA completa |

El último recorrido Playwright duró aproximadamente 2,1 minutos. El MCP oficial
también se registró y verificó por su transporte stdio: inicialización, listado
de herramientas, navegación, snapshot y cierre del navegador. La suite repetible
se ejecuta mediante Playwright Test, versión fijada en `package-lock.json`.

## E2E comprobado

1. Empresa aprobada inicia sesión, edita requisitos obligatorios/deseables y sus
   categorías. Se comprueba la persistencia; otra empresa no puede editarla.
2. Postulante carga un TXT sintético. La carga no inicia IA automáticamente.
   El propietario descarga su contenido exacto, otra cuenta obtiene 404 y el
   anónimo es redirigido. Un PDF falso se rechaza y conserva la versión vigente.
3. Desde el navegador se solicita la extracción real del CV; los workers y el
   callback publican `candidate-profile.v2`. Se muestran técnicas y blandas sin
   etiquetas de inferencia. La oferta sintética pasa por la extracción real.
   El navegador calcula y presenta `match-result.v2`; se verifica idempotencia.
   Reemplazar el CV deja el análisis anterior como histórico y el cálculo con
   aquel perfil devuelve 409. No se inicia otra extracción automáticamente.
4. El perfil funciona en un viewport móvil de 390 × 844 sin desbordamiento
   horizontal. Los casos de CV y matching no registraron errores JavaScript
   de página.

Una solicitud anónima independiente a la web pública devolvió 302 al dominio
de autenticación de Cloudflare Access. Esto verifica la barrera inicial, sin
probar el ingreso de un usuario autorizado ni modificar la política.

## Fallo encontrado y corregido

Las esperas de cuota incrementaban el contador de reintentos de Celery. Si el
broker fallaba al publicar el callback después de muchas esperas, el límite
global podía impedir reintentar la entrega de un resultado ya calculado.
La publicación del callback ahora tiene un contador persistido independiente,
limitado a cinco fallos. Conserva el resultado y no repite la inferencia.
Dos regresiones nuevas, incluyendo una con `Celery.retry` real, verifican el
comportamiento. La suite API completa pasó después de la corrección y se
recargó Celery antes del E2E, cuando no había trabajos activos.

Los dos intentos iniciales del navegador encontraron errores en la nueva prueba:
lectura tardía de una respuesta luego de la recarga del CV y búsqueda del aviso
en el fallback inline en lugar de la notificación visible. Se corrigieron las
esperas/aserciones del test, conservando las solicitudes reales de la aplicación.
Los intentos fallidos mantienen sus capturas, videos y trazas.

## Evidencia y limpieza

Los reportes privados se guardan en `.test-artifacts/e2e/`, uno por ejecución:
`html/index.html`, `results.json`, capturas y artefactos de diagnóstico.
Los logs de las suites y la comprobación MCP se conservan en el directorio
local de revisión de esta ejecución. Estos artefactos no se publican en Git.

La limpieza final reportó cuatro usuarios, dos ofertas, tres archivos, tres
eventos de salida y seis sesiones propios eliminados, sin errores de archivos.
Las identidades y la configuración global existentes no se modificaron.

## Límites pendientes

- Chromium es el navegador ejecutado; Firefox y WebKit quedan fuera de esta ronda.
- No se realizaron pruebas de carga, pentest, failover de Redis ni caída forzada
  de un worker durante una inferencia real.
- La muestra sintética valida transporte y comportamiento; no demuestra la
  precisión general del modelo ni garantiza tiempos ante cuotas distintas.
- La web continúa en modo de desarrollo. Cloudflare Access no sustituye la
  preparación de `DEBUG=false`, TLS de PostgreSQL y servido de estáticos/medios.
- Las suites emiten advertencias previas de dependencias y una fecha sin zona
  horaria en un fixture de Django; no produjeron fallos.

## Regresión de ofertas antiguas

El diagnóstico posterior encontró diez ofertas activas pendientes de revisión de requisitos: nueve fixtures DEMO con perfil v1 y una oferta real. Se actualizó exclusivamente el conjunto DEMO original mediante un comando que verifica sus campos, respalda los datos y aplica una transacción. Una segunda ejecución informó nueve registros ya actualizados; las nueve tienen perfil v2 listo y un trabajo completado con el hash de su fuente actual. La oferta real conserva la revisión de su empresa.

La interfaz muestra el aviso de revisión y oculta el formulario de compatibilidad para ofertas pendientes o con perfil antiguo. El servicio también rechaza una oferta marcada para revisión aunque tenga perfil v2. Pasaron 16 pruebas de matching y del comando DEMO sobre PostgreSQL de prueba.

El nuevo caso Playwright prepara una oferta legacy sintética y verifica el aviso y la ausencia del formulario. Su ejecución forma parte de la ronda local `2026-10-21T13-34-28-681Z-3ce477f0`.

Resultado de esa ronda: **5 pruebas aprobadas**, sin omisiones ni reintentos, en 4,4 minutos. Incluye extracción y callback reales, compatibilidad real, idempotencia, rechazo del CV obsoleto, privacidad y vista móvil. El proveedor siguió siendo Groq; se observaron esperas locales por margen de tokens. Este tiempo corresponde al conjunto E2E, no a una medición aislada de inferencia ni a Gemini.

## Activación de Gemini Flash-Lite

Se activó `gemini-3.5-flash-lite` en extracción y compatibilidad. El flujo de cuatro CV sintéticos, con extracción y consolidación reales, produjo cuatro perfiles válidos en ocho llamadas, con 19.953 tokens de entrada y 5.535 de salida (25.488 totales), sin errores 429. Se conserva el detalle en `docs/pruebas/evaluaciones/gemini-2026-10-21.md`.

Validación posterior: **145 pruebas API aprobadas**, **53 pruebas Django de IA y matching aprobadas**, comprobaciones de web y OpenAPI con HTTP 200 y **cinco E2E aprobados** en 2,2 minutos. El E2E exige que `model_version` sea `gemini-3.5-flash-lite` y que el namespace de caché sea `gemini:gemini-3.5-flash-lite`; incluye callback, perfiles, match, idempotencia, privacidad, CV obsoleto y vista móvil. La ejecución `2026-10-21T22-01-54-530Z-760501cb` terminó sin omisiones ni reintentos y limpió cuatro usuarios, tres ofertas, tres archivos, tres eventos de salida y siete sesiones, sin fallos de archivos.

El script de configuración ya conserva el proveedor Gemini al reiniciar. El versionado de CV impide reutilizar un análisis terminado con el prompt anterior y el namespace nuevo separa resultados de matching de Groq. La clave permanece en configuración privada, excluida de Git; los cambios de código de esta ronda siguen locales.

## Optimización v4 y cola de CV

La captura de AI Studio confirmó 15 RPM, 250.000 TPM de entrada y 500 RPD. La configuración usa el 80 %: 12 RPM, 200.000 TPM estimados y 400 solicitudes en ventana móvil de 24 horas. Se eliminó la pausa fija y se agregaron reserva Redis atómica de cuotas, un lease global para serializar CVs, prioridad efectiva para callbacks y consolidación local de una hoja sin ambigüedad. El tamaño de fragmento llega a 20.000 caracteres, con preflight de entrada y división al truncarse la salida.

Validación: **162 pruebas API**, **53 Django**, cinco E2E aprobados en **1,4 minutos** y prueba de cuatro solicitudes CV simultáneas completadas en **62,312 segundos**, con máximo observado de un CV procesándose. Los cuatro perfiles y callbacks fueron correctos; se limpiaron los cuatro conjuntos de fixtures. El plan de cola, los límites y sus restricciones se detallan en `docs/operaciones/cola-cuotas-ia.md`.

## Repetir las verificaciones

```powershell
npm ci
npx playwright install chromium
npm run test:js
npm run test:e2e
# Autoriza una extracción de CV, una de oferta y un matching con IA real:
npm run test:e2e:live
```

El runner necesita el entorno Python `.venv` y los servicios locales activos.
El modo sin IA omite explícitamente el caso que consume proveedor. Si una
ejecución se interrumpe, `scripts/e2e_fixture.py cleanup --state <state.json>`
permite repetir la limpieza; espera cuando todavía hay trabajos propios activos.
