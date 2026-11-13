# Cursos recomendados por brechas del match

El detalle privado de un match completado muestra cursos activos del catálogo para requisitos con resultado `not_met`, `partial` o `unknown`. Los requisitos cumplidos no generan recomendaciones. `unknown` se presenta como una sugerencia opcional por falta de información en el CV; no confirma que la persona carezca de la competencia.

## Prioridad y cobertura

Para cada requisito se busca, en este orden:

1. La habilidad en el título del curso: por ejemplo, «Excel para el trabajo» para «Manejo de Excel».
2. Una habilidad vinculada explícitamente al curso. Permite relacionar «Administración práctica» con Excel aunque su título sea general.
3. Una mención pertinente en la descripción, excluyendo negaciones y prerrequisitos reconocibles.
4. Si no existe ninguna opción específica, un curso general de la misma área actual de la oferta. Se etiqueta como opción relacionada y pide revisar su temario; no asegura que enseñe esa habilidad.

Se normalizan acentos, mayúsculas y términos genéricos, y se respetan límites de palabras: Java no equivale a JavaScript ni R a React. La coincidencia es verificable por texto o por relaciones del catálogo, no una evaluación semántica de temarios completos.

Hay hasta tres referencias por requisito y seis cursos únicos en total. Un curso que sirve para varias brechas aparece una vez con sus motivos. No se recomiendan cursos como sustituto de años de experiencia, horarios, ubicación, títulos formales o licencias. Los cursos desactivados desaparecen de las recomendaciones al actualizar la página.

## Configurar cursos generales

Al crear o editar un curso, el personal puede completar **Habilidades que desarrolla**. En el administrador Django también se puede gestionar esta relación. La selección es opcional: los cursos existentes continúan funcionando por nombre y descripción.

Si un curso de Administración realmente desarrolla Excel, se vincula con la habilidad Excel. No basta con que una habilidad y un curso compartan categoría: el catálogo puede registrar la misma habilidad en distintas áreas, y esa relación por sí sola no demuestra cobertura.

## Datos y operación

Aplicar `python manage.py migrate` antes de reiniciar Django. La migración `cursos.0007_curso_habilidades` añade una tabla de relaciones y no cambia los cursos existentes.

Las brechas se toman de los requisitos congelados en el match. La disponibilidad de cursos y el área usada únicamente para sugerencias generales pertenecen al catálogo actual. Consultar recomendaciones no modifica el puntaje, no crea otra solicitud de match y no consume llamadas ni tokens de IA. La vista mantiene el control de acceso por postulante.

Las pruebas de reglas están en `apps/matching/test_course_recommendations.py`; las de presentación y permisos, en `apps/matching/test_course_recommendation_views.py`. El E2E usa un requisito de Excel, un curso específico y otro general vinculado, además de verificar el acceso al detalle y al curso.

## Comprobar el funcionamiento local en Windows

La recomendación se calcula al abrir **Ver detalles del match**, en
`/matching/resultado/<request_id>/`. No se genera al consultar únicamente el
porcentaje ni en el listado público de cursos. Usa el match guardado y el
catálogo actual: puede comprobarse sin iniciar la API, Celery o los
despachadores de análisis.

Desde la raíz de BolsaTrabajo, con `.env` y las dependencias locales preparados:

```powershell
# Si Docker Desktop está detenido:
docker desktop start

# Contenedores del entorno de integración local existente.
# Con otra instalación, iniciar sus servicios PostgreSQL y Redis.
docker start ien-postgres-integracion backend-redis-1

# Respaldar la base antes de aplicar las migraciones.
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 ientrabajo.asgi:application
```

Revisar `DB_ENGINE`, `DB_HOST` y `DB_PORT` en el `.env` local. El entorno de
integración usa PostgreSQL en `127.0.0.1:5433`; un `db.sqlite3` antiguo no
representa esa base. Este arranque mantiene la configuración de proveedores
existente y no inicia procesos que consuman la cola de análisis.

Para la comprobación manual, iniciar sesión como postulante, abrir una oferta
con un match completado y entrar en sus detalles. Verificar los motivos y el
enlace **Ver curso**. Si el curso tiene un nombre general, revisar en moderación
**Habilidades que desarrolla** y asociar únicamente contenidos comprobados de
su temario; compartir una categoría no acredita una habilidad.

### Prueba de navegador con datos sintéticos, sin IA

Con Django iniciado en otra terminal, ejecutar desde la raíz del repositorio:

```powershell
$env:PYTHONUTF8 = '1'
$env:E2E_BASE_URL = 'http://127.0.0.1:8000'
$env:E2E_PYTHON = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$env:E2E_RUN_DIR = Join-Path (Get-Location) ('.test-artifacts\recomendaciones\e2e-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$env:E2E_STATE_FILE = Join-Path $env:E2E_RUN_DIR 'state.json'

$browserExit = 1
$cleanupExit = 1
try {
    & $env:E2E_PYTHON scripts\e2e_fixture.py seed --state $env:E2E_STATE_FILE
    if ($LASTEXITCODE -ne 0) { throw 'Falló la preparación de datos sintéticos.' }
    node node_modules\@playwright\test\cli.js test --grep 'match completado se renderiza'
    $browserExit = $LASTEXITCODE
} finally {
    if (Test-Path -LiteralPath $env:E2E_STATE_FILE) {
        & $env:E2E_PYTHON scripts\e2e_fixture.py cleanup --state $env:E2E_STATE_FILE
        $cleanupExit = $LASTEXITCODE
    }
    Write-Output ('Reporte: ' + (Join-Path $env:E2E_RUN_DIR 'html\index.html'))
}
if ($browserExit -ne 0 -or $cleanupExit -ne 0) {
    throw 'La validación o la limpieza fallaron; revisar el reporte y el estado privado.'
}
```

Este caso verifica el resultado guardado de 0%, dos cursos en el orden esperado,
la presentación móvil, el enlace al curso, la redirección del visitante anónimo
y el rechazo de otro postulante con HTTP 404. Al terminar se eliminan sus
usuarios, ofertas, cursos, habilidad, archivo y sesiones sintéticos. Los
reportes y el estado con credenciales de prueba permanecen en
`.test-artifacts/`, excluido de Git. Si la limpieza falla, repetir `cleanup`
con el mismo archivo de estado.

### Diagnóstico de resultados vacíos

| Situación | Comprobación |
| --- | --- |
| PostgreSQL no responde | Iniciar Docker o el servicio correspondiente y verificar host y puerto del `.env`. |
| Falta `cursos_curso_habilidades` | Aplicar las migraciones; la relación se incorpora en `cursos.0007_curso_habilidades`. |
| No aparece la sección de cursos | El match debe estar completado y tener brechas entrenables clasificadas. Los requisitos cumplidos o históricos sin categoría pueden no generar sugerencias. |
| Aparece la sección sin cursos | Revisar que haya cursos activos con coincidencia en título, habilidades o descripción. |
| Un curso general no aparece | Vincular las habilidades que realmente desarrolla. El fallback general exige además el nombre general del área; no incluye cualquier curso de su categoría. |

No modificar resultados históricos para inventar categorías o brechas. Para
comprobar el flujo actual, utilizar un match v2 existente o la prueba sintética.

## Verificación local del 13/11/2026

Se comprobó la implementación existente desde `origin/develop` (`bfd743f`), en
la rama `feature/recomendacion-cursos`, sin modificar sus reglas ni contratos.
Docker estaba detenido; al iniciarlo volvió a estar disponible PostgreSQL en
el puerto 5433. La migración de habilidades de cursos ya estaba aplicada. Tras
crear un respaldo privado se aplicaron las dos migraciones pendientes:
`ia.0009_alter_eventosalida_tipo` y
`matching.0007_alter_resultadocompatibilidad_estado`.

El catálogo tenía seis cursos activos y ninguno con habilidades vinculadas.
Las coincidencias por texto ya permitían recomendar cursos en siete matches
guardados. No se añadieron asociaciones a los cursos reales sin comprobar sus
temarios.

La suite Django sobre PostgreSQL ejecutó 171 pruebas: 170 aprobadas y una
omitida. `check` y `makemigrations --check --dry-run` finalizaron correctamente.
El caso Chromium anterior pasó, con limpieza confirmada de sus cuatro
usuarios, tres ofertas, tres cursos, una habilidad, un archivo y dos sesiones;
no creó eventos de análisis ni consumió IA. La API basada en `origin/main`
(`17ab6d0`) aprobó sus 269 pruebas. Estos resultados acreditan el entorno local
de esta fecha, no el estado de otro despliegue.

Validación del 22/10/2026: suite Django completa de 153 pruebas aprobadas y una omitida por requerir macOS; API con 176 pruebas aprobadas; seis E2E con IA real aprobados en 1,4 minutos. Ejecución `2026-10-22T04-41-47-022Z-052c8016`, con limpieza confirmada de sus cuatro usuarios, cuatro ofertas, tres cursos, una habilidad y cuatro archivos sintéticos. Las habilidades E2E llevan un identificador propio para no depender de los cursos reales del catálogo.
