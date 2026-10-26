# Análisis de archivos sobrantes y mantenimiento

Fecha: 22/10/2026. Alcance: inventario local, búsquedas de referencias y comparación de archivos de texto. El diagnóstico inicial fue de solo lectura. Después, con autorización del usuario, se eliminaron únicamente los residuos claros detallados debajo. Se conservaron código de aplicación, bases, medios, backups y dependencias.

## Limpieza realizada con autorización

Se retiraron **202 archivos de bytecode Python**, **5 archivos `.DS_Store`** y **30 carpetas `__pycache__`** del proyecto, incluyendo la carpeta residual `emails/` de la raíz después de verificar que no contenía código fuente. Total de archivos retirados: **897078 bytes**, aproximadamente **876 KiB**.

Se excluyeron `.git/`, `.venv/`, `node_modules/` y enlaces simbólicos del recorrido de limpieza. La aplicación `apps/emails/` y las plantillas de correo se conservaron. Las cachés pueden regenerarse al ejecutar Python; ya están excluidas de Git. Los candidatos que requerían revisión no se eliminaron.

Las tablas siguientes conservan el inventario del diagnóstico inicial; las filas de caché, `.DS_Store` y `emails/` residual ya fueron atendidas. La diferencia entre conteos corresponde al inventario actualizado al momento de ejecutar la limpieza.

## Resultado principal

Hay residuos locales regenerables, documentación que necesitaba orden y candidatos a simplificación de código. No se encontraron archivos de texto exactamente duplicados mayores a 100 bytes en el recorrido analizado. Eso no descarta duplicación parcial ni lógica equivalente.

Los 7 componentes de la guía tienen ahora un Markdown principal cada uno; el [índice](../README.md) los reúne. Los planes, informes y notas se clasificaron por finalidad, conservando su contenido e indicando vigencia cuando corresponde.

## Residuos locales que se pueden limpiar

Medición tomada antes de generar nuevamente la documentación. Se excluyeron `.git`, `.venv`, `node_modules`, `private_uploads` y `media` del conteo de cachés/duplicados para no recorrer dependencias ni datos personales. Los tamaños son aproximados donde se usa `du`.

| Hallazgo | Evidencia local | Evaluación | Acción propuesta |
| --- | --- | --- | --- |
| Caché Python del proyecto | 200 archivos `.pyc`/bajo `__pycache__`, 857264 bytes (aprox. 837 KiB). | Regenerable; el conteo cambia al ejecutar Python. | Limpiar en una tarea de mantenimiento; no versionar. No borrar código fuente ni migraciones junto con la caché. |
| Metadatos macOS | 4 archivos `.DS_Store`, 28688 bytes (aprox. 28 KiB), en el recorrido anterior. | Basura de navegación local. | Eliminar cuando se haga la limpieza; ya está cubierta por las exclusiones de Git. |
| Carpeta `emails/` de la raíz | Solo contiene `__pycache__` y `migrations/__pycache__`, sin `.py` fuente. La aplicación vigente está en `apps/emails/`. | Residuo de una ubicación anterior; candidata clara a retirar. | Quitar esa carpeta residual durante la limpieza. Conservar `apps/emails/` y `templates/emails/`. |
| Backup SQLite antiguo | `db.sqlite3.ia-match-20261015-setup.bak`, aprox. 236 KiB. | Respaldo fechado, no basura demostrada. | Verificar necesidad, restaurabilidad y copia externa antes de retirar. Puede contener datos personales. |
| Dependencias Node locales | `node_modules/` aprox. 140 KiB, con dotenv; el manifiesto actual declara Playwright. | Instalación local que no parece corresponder al manifiesto actual. | Verificar resolución de Playwright y reconstruir con `npm ci` al preparar E2E; no cambiar el lockfile solo para “limpiar”. |

Los residuos no están entre los archivos rastreados consultados para `.DS_Store`, `.bak` y `.sqlite3`. El reporte no expone nombres/contenido de CV ni credenciales.

## Archivos grandes que no deben confundirse con basura

| Ruta | Tamaño local observado | Motivo para conservar / condición |
| --- | --- | --- |
| `.venv/` | aprox. 269 MiB | Entorno Python activo. Regenerable con dependencias, pero borrarlo interrumpe herramientas y servidores que lo usan. |
| `.git/` | aprox. 13 MiB | Historial y metadatos Git. No limpiar manualmente como si fuera caché de aplicación. |
| `media/` | aprox. 18 MiB | Imágenes y cargas. Un nombre de archivo extraño no demuestra que esté huérfano. |
| `private_uploads/` | aprox. 8.7 MiB | CV y snapshots privados; su purga exige cruzar referencias de BD, versiones e historial. |
| `db.sqlite3` | aprox. 736 KiB | Base local existente. Puede conservar datos aunque otro ambiente use PostgreSQL. |
| `output/` | aprox. 156 KiB | PDF solicitado en la entrega anterior; es un entregable, no un temporal. Su contenido es una exportación anterior a este reordenamiento. |

No se consultaron filas de la base para detectar archivos huérfanos. Antes de purgar medios hay que comparar, en modo de solo lectura, referencias de Curso, Oferente, Postulante, CVVersion y TrabajoExtraccion contra ambos almacenamientos; considerar snapshots, respaldo y plazo de retención.

## Duplicación y contenido desactualizado

| Hallazgo | Evidencia | Recomendación |
| --- | --- | --- |
| Dependencias repetidas | `requirements.txt` declara Channels dos veces y channels-redis dos veces; también declara daphne además del extra `channels[daphne]`. | Consolidar restricciones compatibles y comprobar arranque ASGI/tests en una tarea aparte. No quitar daphne automáticamente: su declaración directa puede ser intencional. |
| Inicio Windows describe pesos antiguos | La nota `inicio-local-windows.md` conserva 45/25/15/15 y confianza del modelo; el contrato actual tiene siete dimensiones y el flujo v2 no entrega confianza cuantificada. | Se agregó aviso de vigencia. Mantener comandos útiles; reemplazar instrucciones históricas cuando se valide el flujo Windows actual. |
| Proveedor/modelo dependiente del momento | README cita Groq; notas posteriores registran Gemini. La API externa no está en esta carpeta. | No inferir el proveedor activo desde una nota; contrastar configuración privada sin publicarla y versión externa. Conservar las mediciones como historia. |
| Dos documentos de pruebas relacionados | `pruebas/estrategia.md` fija comandos/criterio de salida; `pruebas/plan-integracion.md` describe riesgos, aislamiento y E2E. | Se conservaron ambos con funciones distintas y enlace entre sí; evitar repetir resultados en ellos. |
| Referencias breves antiguas | Primeros pasos y arquitectura MVT estaban sueltos en RST. | Se movieron a `referencia/`, conservando Sphinx; el procedimiento principal es el Markdown/README vigente. |
| Informes mezclados con instrucciones | Resultados de pruebas, evaluaciones y registros de integración en la raíz de docs. | Se movieron a `pruebas/reportes`, `pruebas/evaluaciones` e `historial`, sin borrar evidencia. |

## Código y plantillas para revisar antes de eliminar

La búsqueda fue estática por referencias literales. La ausencia de una referencia no prueba desuso: pueden existir carga dinámica, imports indirectos, rutas configuradas o consumidores externos.

| Candidato | Evidencia encontrada | Riesgo / próximo paso |
| --- | --- | --- |
| `templates/nueva_ui/partials/_aviso.html` | Sin referencia literal externa en fuentes de aplicación, templates, estáticos, scripts y tests inspeccionados. | Candidato a retirar si se confirma que no lo incluyen nombres dinámicos. |
| `templates/nueva_ui/partials/_footer.html` | Mismo resultado que el anterior. | Revisar composición del layout y vista móvil antes de retirar. |
| `guardar_comparacion` en `apps/ia/matching.py` | Se encontró la definición, sin llamadas textuales fuera de ella. El flujo histórico de la vista ya delega a matching. | Revisar consumidores y migración del flujo antes de quitar la función. |
| Comparador antiguo en `apps/ia/matching.py` | `comparar_oferta_con_analisis` sigue importado por tests; `ultimo_analisis_completado` sigue usado por `apps/ofertas/views.py`. | No borrar todo el módulo: tiene uso activo. Decidir por función, con tests. |
| `ComparacionOfertaCV` | Modelo y migración presentes, consultas en tests y rama de presentación histórica incluida en la oferta. | No borrar tabla/modelo por falta de nuevas escrituras. Requiere decisión sobre datos, compatibilidad y migración explícita. |
| Archivos mínimos de apps | Algunos `models.py`, `views.py`, `admin.py` y tests de emails/moderación solo tienen scaffolding. | Beneficio de borrado mínimo; conservar estructura o depurar imports/comentarios en una revisión de código. `apps/emails/apps.py` carga señales activas. |
| Scripts UI independientes | `test_cv_background.cjs` y `test_match_cancel_ui.cjs` no están incluidos en `npm run test:js`. | Son pruebas manuales de flujos concretos; decidir integrarlas al runner o documentar su ejecución, no marcarlas como basura. |

Todos los JS/CSS de aplicación inspeccionados tuvieron alguna referencia literal por ruta o nombre. No se detectó una base suficiente para borrarlos. Las migraciones históricas, incluso las que crean y luego eliminan tablas, son parte del grafo de instalación y **se conservan**.

## Orden recomendado de una futura limpieza

1. Retirar `.DS_Store`, caché Python y la carpeta residual `emails/` de la raíz. Es la limpieza más clara; libera menos de 1 MiB según el inventario inicial, por lo que su beneficio principal es el orden.
2. Revisar el backup SQLite y trasladarlo a un respaldo restringido si se necesita conservarlo.
3. Alinear dependencias locales con sus manifiestos; consolidar repeticiones de requirements en un cambio probado.
4. Revisar los dos parciales sin referencias y el guardado histórico por función, con pruebas de UI/integración antes de eliminar código.
5. Separar cualquier purga de CV/medios de la limpieza técnica: necesita inventario relacional, política de retención y respaldo.

El orden documental está implementado y el primer paso de limpieza fue ejecutado con autorización. Los pasos restantes continúan como propuestas; no se presenta el desuso de código o datos como confirmado.
