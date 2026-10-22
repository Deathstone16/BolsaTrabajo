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

Validación del 22/10/2026: suite Django completa de 153 pruebas aprobadas y una omitida por requerir macOS; API con 176 pruebas aprobadas; seis E2E con IA real aprobados en 1,4 minutos. Ejecución `2026-10-22T04-41-47-022Z-052c8016`, con limpieza confirmada de sus cuatro usuarios, cuatro ofertas, tres cursos, una habilidad y cuatro archivos sintéticos. Las habilidades E2E llevan un identificador propio para no depender de los cursos reales del catálogo.
