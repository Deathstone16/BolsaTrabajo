# Cola de CV y presupuesto de Gemini

> Alcance: snapshot de una configuración local del servicio externo de IA, conservado como referencia. No verifica sus cuotas o modelos actuales. Ver [operación general](despliegue.md) y [evaluación de cobertura](../pruebas/evaluaciones/cobertura-habilidades-v6.md).


Configuración local activa: proveedor `gemini-3.5-flash-lite`; extracción `cv-extraction.v2-packets-soft.v6`. La cola y su primera medición se incorporaron en v4. La revisión v6 de cobertura y sus límites están documentados en [revisión de cobertura v6](../pruebas/evaluaciones/cobertura-habilidades-v6.md).

## Cuotas verificadas y margen local

La captura de Google AI Studio aportada por el usuario muestra 15 RPM, 250.000 TPM de entrada y 500 RPD. Son valores de ese proyecto y modelo; pueden cambiar. La configuración usa un margen del 20 %:

| Parámetro | Google AI Studio | Presupuesto local |
|---|---:|---:|
| Solicitudes por minuto | 15 | 12 |
| Tokens de entrada por minuto | 250.000 | 200.000 estimados |
| Solicitudes por día | 500 | 400 en ventana móvil de 24 horas |

Google restablece RPD a medianoche del Pacífico; la ventana local móvil es deliberadamente conservadora y no equivale a ese calendario. Las solicitudes realizadas fuera de esta aplicación también consumen cuota del proyecto. Por ello el margen reduce riesgo, pero no garantiza ausencia de 429. [Cuotas oficiales](https://ai.google.dev/gemini-api/docs/rate-limits).

La pausa fija se eliminó: `GEMINI_PAUSA_SEGUNDOS=0`. Redis reserva atómicamente RPM, TPM de entrada y RPD, compartidos por extracción y matching. Se estima la entrada como `ceil(caracteres/2)`; no es un conteo exacto del tokenizer ni incluye salida. Las reservas se conservan ante fallos de red, de forma conservadora. No se hacen peticiones de conteo adicionales por fragmento.

Si falta presupuesto, no se envía la petición HTTP. Una espera diaria o mayor de dos minutos libera el worker y reprograma la tarea, conservando el progreso. Los 429 respetan RetryInfo/Retry-After; los errores estructurados de cuota diaria esperan hasta el próximo reinicio del día del Pacífico en vez de insistir cada minuto.

## Uso por CV

- Fragmentos de hasta 20.000 caracteres, en lugar de 4.000.
- Presupuesto máximo local de 60.000 tokens estimados de entrada por petición. Si el fragmento lo supera, se divide antes de llamar al modelo.
- Salida máxima de 16.384 tokens: es un techo, no consumo obligatorio. Si el proveedor trunca una respuesta, se divide el fragmento y se conserva toda la cobertura del texto.
- Una única hoja válida sin posibles duplicados se ensambla en código, sin segunda llamada. Se conservan título/resumen y las validaciones de hechos, evidencias y citas.
- Si hay varias hojas o posibles duplicados se mantiene la consolidación con el modelo.
- Un fragmento inválido admite un único reintento de corrección. No se eliminan citas ni hechos para forzar un resultado válido.

Se amplía el texto útil enviado, no se rellena una petición hasta un límite arbitrario del modelo. Los CV extensos o ambiguos pueden necesitar más de una llamada.

## Cola y recuperación

Las solicitudes de personas distintas quedan persistidas y encoladas. Celery usa concurrencia uno y prefetch uno. Un lease Redis global adicional permite que como máximo un CV posea el turno de extracción aunque se inicien varios workers. El lease y el lock del trabajo se renuevan mediante heartbeat; una ejecución que pierde propiedad no publica resultados. Si un worker cae, los leases expiran y el trabajo puede reanudarse.

Los callbacks tienen prioridad Redis 0 frente a prioridad normal 5, incluida la opción efectiva del task: una ruta por sí sola quedaba sobrescrita por el valor predeterminado de Celery. Esto favorece entregar un resultado terminado antes de empezar otras inferencias. El orden normal de entrada se conserva dentro de la cola; reintentos o recuperación pueden alterar el orden, así que no se promete FIFO estricto ante fallos.

## Validación

- API: 162 pruebas aprobadas, incluidas cola, recuperación, presupuesto y consolidación rápida.
- Django: 53 pruebas de IA y matching aprobadas.
- Playwright: cinco E2E aprobados en 1,4 minutos, con Gemini confirmado, análisis optimizado, callbacks, match, idempotencia, privacidad, CV obsoleto y vista móvil. Ejecución `2026-10-21T22-51-04-108Z-b7f29a91`; sus datos sintéticos fueron limpiados.
- Lua probado contra Redis real con un namespace aislado: 4 admisiones entre 20 intentos concurrentes con RPM=4; rechazo TPM sin consumo adicional; cuota diaria independiente del minuto; cooldown sin reservas nuevas y TTL válidos. Solo se borraron las claves del test.
- Cuatro CV sintéticos solicitados simultáneamente por Django: cuatro HTTP 202, cuatro perfiles canónicos y callbacks correctos, máximo observado de un CV procesándose y un lease, finalización en 62,312 segundos. El muestreo fue de dos segundos; la exclusión también está cubierta por los tests de lease. Se limpiaron los cuatro conjuntos de fixtures, sin borrar datos ajenos.

Los documentos y tiempos de esta muestra no garantizan la latencia de CVs largos, nuevas cuotas o tráfico externo. Los reportes detallados permanecen en el directorio privado de revisión. La clave se mantiene en `.env`, excluida de Git. Los cambios de esta ronda están locales.

## Estimación del nivel de habilidades (v5)

Los niveles pueden estimarse desde acciones concretas atribuibles a cada habilidad, aplicando la misma rúbrica a cualquier ocupación. La práctica guiada o con supervisión respalda principiante; ejecución habitual con responsabilidad, intermedio; resolución autónoma de problemas no rutinarios, avanzado. Experto requiere una declaración explícita o evidencia amplia de dominio, métodos validados y resultados; no se deduce de antigüedad, cargo o supervisión por sí solos.

La explicación `e` identifica las señales que sostienen la estimación y `q` conserva las citas literales mediante el catálogo del servidor. El origen de la habilidad sigue siendo independiente: una habilidad nombrada en el CV conserva `declared` aunque el nivel se estime. No se infieren años, niveles de idiomas, licencias ni certificaciones. Una lista de herramientas sin tareas suficientes mantiene `unknown`; la interfaz omite ese indicador y traduce los niveles conocidos al español.

Validación real: seis CV sintéticos de salud, comercio, operaciones, educación, administración y un oficio cumplieron sus rangos esperados, incluida la abstención en herramientas sin contexto y la conservación del nivel declarado. Todos los perfiles pasaron las validaciones; los casos no generaron idiomas ni años de habilidad ausentes. Es una evaluación pequeña con casos controlados, no una garantía de precisión para todos los CV.

La versión v5 en ambos servicios evita reutilizar el análisis anterior. Para aplicar esta evaluación a un CV ya procesado, el usuario debe pulsar nuevamente **Analizar CV**; los resultados históricos se conservan.

Validación v5: 165 pruebas de API y 54 pruebas Django aprobadas; los seis casos reales con Gemini cumplieron sus rangos esperados. Los cinco E2E pasaron en 1,4 minutos (ejecución `2026-10-21T23-25-02-389Z-861f84ba`), incluidos callback, resultado, matching y limpieza de los datos sintéticos.
