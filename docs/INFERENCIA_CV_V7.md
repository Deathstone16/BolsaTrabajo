# Inferencia de CV: taxonomía y formación v7

La extracción `cv-extraction.v2-packets-soft.v7` se aplica a nuevos análisis y a
reanálisis solicitados por el usuario. No modifica en segundo plano los perfiles
ni los resultados de match históricos. Para corregir un análisis guardado con una
versión anterior, se debe volver a analizar el CV; la versión de prompt forma
parte de la clave de idempotencia.

## Habilidades

Las competencias técnicas representan herramientas, equipos, métodos y prácticas.
Un cargo, título académico o nombre de curso no constituye por sí mismo una
habilidad. La formación se conserva en estudios/cursos y las credenciales obtenidas
en su sección. La práctica descrita durante una formación sí puede respaldar una
competencia; el nombre del programa por sí solo no demuestra dominio.

Las blandas usan exclusivamente estas diez categorías:

- Pensamiento crítico
- Alfabetización en IA
- Inteligencia emocional
- Learnability
- Comunicación
- Colaboración
- Adaptabilidad al cambio
- Creatividad
- Responsabilidad
- Proactividad

No hay un mínimo ni se completan diez por defecto. Las menciones directas conservan
su origen declarado; las inferencias requieren acciones concretas y citas. Los
equivalentes inequívocos se agrupan: trabajo en equipo → Colaboración, aprendizaje
continuo → Learnability, iniciativa → Proactividad. Liderazgo, organización o
atención al detalle no se convierten automáticamente en otro rasgo. El modelo
debe justificar la correspondencia con una categoría permitida.

La validación rechaza categorías ajenas, títulos/cursos usados como nombres de
habilidad y evidencia compuesta únicamente por un nombre de curso. El reintento
de corrección existente sigue acotado a una segunda respuesta por fragmento.
La normalización no crea habilidades ni descarta silenciosamente registros
inválidos. Las evidencias se conservan internamente; las blandas no agregan un
desplegable de evidencia en la interfaz.

## Formación y títulos

El contrato de educación agrega `completion_status` y `source_quotes`, manteniendo
`completed` para compatibilidad. La API y Django deben actualizarse juntos:

| Estado | completed | Presentación |
| --- | --- | --- |
| completed | true | Finalizado |
| in_progress | false | En curso |
| incomplete | false | Incompleto |
| unknown | null | Estado no informado |

Cada estudio extraído necesita una cita literal del programa y su estado. No se
deduce graduación a partir de fechas, antigüedad o duración prevista. La cursada
completa o una tesis pendiente no otorgan un título. Cursar un doctorado conserva
el nombre del programa y el estado; no convierte a la persona en doctor.

Las citas pueden abarcar más de un programa. La validación vincula el estado al
nivel y campo correspondientes: un doctorado terminado en Historia no concede el
de Informática. Una graduación ajena tampoco valida una credencial pendiente.
Las afirmaciones académicas sin respaldo se retiran de los textos generados,
conservando los hechos estructurados y sus citas. Los datos ambiguos no conceden
un título.

Los perfiles antiguos que solo incluyen `completed=false` muestran «No finalizado»;
ese booleano no basta para afirmar que la persona sigue estudiando. Las pantallas
de perfil y resultado separan formación y cursos de las habilidades.

## Validación y límites

Las regresiones usan ejemplos sintéticos de estudios en curso, tesis pendiente,
abandono, fechas sin graduación, titulación explícita, varios grados y disciplinas
en una cita, cursos sin práctica y alias de las diez categorías. Las pruebas de
transporte verifican conservación de citas, niveles, checkpoints e identidad.
Las pruebas con respuestas simuladas no miden la calidad del modelo; el E2E con
Gemini utiliza un CV sintético con grado finalizado, doctorado en curso y curso
sin práctica declarada.

La extracción sigue siendo probabilística y las comprobaciones lingüísticas son
conservadoras. Una formulación ambigua puede quedar con estado desconocido o
requerir corrección, en lugar de conceder un título o una competencia sin respaldo.
