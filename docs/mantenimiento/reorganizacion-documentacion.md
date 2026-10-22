# Reorganización de documentación

Fecha: 22/10/2026. Se preservó el contenido de los documentos y se actualizaron enlaces internos; se añadieron avisos cuando una nota describe una rama o configuración histórica. No se movió código, migraciones ni datos.

## Los siete Markdown principales

| Componente de la guía | Archivo |
| --- | --- |
| 01 · README y arranque | [inicio/proyecto.md](../inicio/proyecto.md) |
| 02 · Requisitos y aceptación | [requisitos/index.md](../requisitos/index.md) |
| 03 · Arquitectura y decisiones | [arquitectura/general.md](../arquitectura/general.md) |
| 04 · Contratos y API | [api/contratos.md](../api/contratos.md) |
| 05 · Modelo de datos | [datos/modelo-datos.md](../datos/modelo-datos.md) |
| 06 · Despliegue y operación | [operaciones/despliegue.md](../operaciones/despliegue.md) |
| 07 · Pruebas y calidad | [pruebas/estrategia.md](../pruebas/estrategia.md) |

El README de la raíz conserva instalación y configuración detalladas. `docs/README.md` es el índice de navegación. Cada componente indica responsable sugerido y cuándo actualizarlo.

## Archivos reubicados

Las rutas de esta tabla son relativas a la raíz del repositorio. La columna anterior es un registro histórico, no un enlace que deba seguir funcionando.

| Ubicación anterior | Ubicación actual |
| --- | --- |
| `docs/GUIA_DOCUMENTACION.md` | `docs/README.md` |
| `IA_MATCH_LOCAL.md` | `docs/operaciones/inicio-local-windows.md` |
| `CUENTAS_DEMO.md` | `docs/pruebas/datos-demo.md` |
| `docs/CLOUDFLARE_TUNNEL.md` | `docs/operaciones/cloudflare-tunnel.md` |
| `docs/COLA_Y_CUOTAS_GEMINI.md` | `docs/operaciones/cola-cuotas-ia.md` |
| `docs/INTEGRACION_POSTGRESQL.md` | `docs/operaciones/postgresql.md` |
| `docs/RECOMENDACIONES_CURSOS.md` | `docs/funcionalidades/recomendaciones-cursos.md` |
| `docs/PLAN_CV_OFERTAS_MATCH.md` | `docs/requisitos/diseno-cv-ofertas-match.md` |
| `docs/IMPLEMENTACION_CV_MATCH.md` | `docs/arquitectura/implementacion-cv-match.md` |
| `docs/ESTRATEGIA_TESTING.md` | `docs/pruebas/plan-integracion.md` |
| `docs/RESULTADOS_TESTING_2026-10-21.md` | `docs/pruebas/reportes/resultados-2026-10-21.md` |
| `docs/EVALUACION_GEMINI_2026-10-21.md` | `docs/pruebas/evaluaciones/gemini-2026-10-21.md` |
| `docs/COBERTURA_HABILIDADES_V6.md` | `docs/pruebas/evaluaciones/cobertura-habilidades-v6.md` |
| `docs/INTEGRACION_BENJA_MATCH_2026-10-22.md` | `docs/historial/integracion-match-2026-10-22.md` |
| `docs/REVISION_DOCUMENTACION_2026-10-22.md` | `docs/historial/revision-documental-2026-10-22.md` |
| `docs/getting_started.rst` | `docs/referencia/primeros-pasos.rst` |
| `docs/architecture.rst` | `docs/referencia/arquitectura-mvt.rst` |
| `docs/apps/index.rst` | `docs/referencia/apps/index.rst` |
| `docs/apps/ofertas.rst` | `docs/referencia/apps/ofertas.rst` |
| `docs/apps/usuarios.rst` | `docs/referencia/apps/usuarios.rst` |
| `docs/apps/moderacion.rst` | `docs/referencia/apps/moderacion.rst` |
| `docs/apps/cursos.rst` | `docs/referencia/apps/cursos.rst` |
| `docs/apps/categorias.rst` | `docs/referencia/apps/categorias.rst` |
| `docs/apps/emails.rst` | `docs/referencia/apps/emails.rst` |
| `docs/apps/ia.rst` | `docs/referencia/apps/ia.rst` |

## Publicación y enlaces

Se adaptó el índice Sphinx para incluir Markdown con MyST y enlazar referencia, guías, informes y mantenimiento. Los diagramas Mermaid conservan su fuente editable; su representación gráfica requiere un visor compatible. El PDF previo sigue siendo una exportación histórica y no se regeneró como parte de este pedido de Markdown.

## Comprobaciones

Se verificó la existencia de los siete Markdown principales y todos los enlaces locales de README y de los Markdown en docs. No se encontraron destinos faltantes. `git diff --check` no informó errores.

La compilación completa con `.venv/bin/python -m sphinx -E -b html -W --keep-going docs /private/tmp/bolsatrabajo-docs-html` terminó correctamente, sin advertencias. Los bloques Mermaid y dotenv se muestran como fuentes legibles, sin requerir un renderizador adicional. La autodocumentación conserva sus módulos originales.

No se ejecutaron pruebas funcionales: los cambios de esta entrega son documentación, rutas de documentación y configuración Sphinx. El inventario original fue de solo lectura. La limpieza posterior autorizada retiró únicamente cachés, `.DS_Store` y la carpeta residual `emails/`; el resultado está registrado en el [análisis de limpieza](analisis-limpieza.md).
