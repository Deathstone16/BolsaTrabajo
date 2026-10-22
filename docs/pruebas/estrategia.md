# Pruebas y calidad

Componente 07 de la guía. Responsable sugerido: equipo de desarrollo y responsable de calidad. Actualizar cuando cambien rutas críticas, estrategia de pruebas o pipeline.

Revisión: 22/10/2026. Complementa la [estrategia existente](plan-integracion.md). Estos son comandos y criterios de aceptación, no una declaración de que toda la suite pasó durante la documentación.

## Capas y comandos

Desde la raíz, usando el entorno instalado y configuración de pruebas:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python -m unittest ientrabajo.test_database_settings ientrabajo.test_proxy_settings
.venv/bin/python manage.py test usuarios categorias ofertas cursos ia matching moderacion emails
npm run test:js
npm run test:e2e
```

Django crea una base de pruebas; con PostgreSQL la cuenta debe tener permiso para crearla. Revisar la configuración antes de ejecutar: los E2E usan el stack real local y sus fixtures, no la misma base temporal de los unitarios. Los scripts de `.cjs` adicionales no están todos incluidos en `npm run test:js`; incorporarlos explícitamente al plan si se validan sus flujos.

El comando `npm run test:e2e:live` habilita IA real y consumo de cuota; debe ejecutarse deliberadamente. La suite FastAPI se corre en su repositorio; no inventar aquí sus comandos.

## Casos críticos y trazabilidad

| Requisitos | Casos mínimos | Evidencia principal |
| --- | --- | --- |
| RF-01/02/03/14 | Registro/email, permisos, empresa pendiente, propiedad de oferta, transiciones, categorías protegidas. | `usuarios/tests.py`, `usuarios/test_integracion.py`, `ofertas/tests.py`, `moderacion/tests.py`, `categorias/tests.py`. |
| RF-05/06 | Favoritas únicas, tamaño/formato de CV, versión, descarga ajena/anónima, bloqueo público, migración privada. | Tests de usuarios/ofertas y escenarios E2E. |
| RF-07/08/13 | Callback firmado y repetido, entrega/reintento, reemplazo de CV, resultado tardío, normalización concurrente, canales privados. | `ia/tests.py`, `ia/test_recovery.py`, `ia/test_profile_skills.py`, tests de integración. |
| RF-09/10/11 | Snapshot y hashes, pesos 100%, perfiles vigentes, cancelación, reintento, aislamiento por UUID. | `matching/tests.py`, `usuarios/test_process_limits.py`. |
| RF-12 | Cursos según habilidades y brechas, exclusión de recomendaciones no aptas, sin llamada LLM extra. | `matching/test_course_recommendations.py`, `matching/test_course_recommendation_views.py`, `cursos/test_course_skills.py`. |

Los archivos se citan como suites relacionadas; comprobar el caso exacto y ampliar cobertura al cambiar el comportamiento. No inferir cobertura total solo por el nombre de una suite.

## Dobles, fixtures y datos

En pruebas de integración controladas simular Requests/WebSocket/Redis/LLM según la frontera del caso. Fijar respuestas válidas/erróneas, timeout, rate limit, evento duplicado y callback atrasado. Usar contratos Pydantic reales y fixtures sintéticos sin documentos personales. Las pruebas de precisión de IA son distintas de las que verifican transporte y puntuación.

`seed_demo` genera datos locales; revisar sus opciones y no ejecutarlo contra producción. Playwright dispone de `scripts/e2e_fixture.py` y `scripts/run_e2e.cjs`; los artefactos privados quedan en `.test-artifacts/` según la estrategia existente. Conservar fallos reproducibles y confirmar limpieza de identidades/archivos sintéticos.

## Criterio para integrar

Aprobar cuando no hay fallos P0, migraciones y modelos coinciden, contratos son compatibles y pasan las pruebas del área cambiada. Para cambios de integración, ejecutar suite Django, configuración, JS y E2E aplicable. Registrar versión, ambiente, comandos, resultados y omisiones. Un mock o caso omitido no equivale a integración real aprobada.

En `.github` solo se encontró CODEOWNERS; no hay un workflow de CI de pruebas declarado. Pendiente: automatizar las comprobaciones sin secretos de producción, separar integración con infraestructura de unitarios y publicar reportes. Defectos: registrar RF afectado, reproducción, resultado esperado/actual, severidad y evidencia en el backlog o issue real del repositorio.

## Validación de esta entrega

Ver [registro de revisión documental](../historial/revision-documental-2026-10-22.md), generado al terminar. Los reportes previos de testing en `docs/` son evidencia histórica de sus propias fechas; no certifican automáticamente los cambios locales actuales.
