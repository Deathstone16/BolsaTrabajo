# Requisitos de diseño para CV, ofertas y compatibilidad

Este documento conserva los requisitos técnicos que guían los flujos de CV y matching. El comportamiento implementado y su verificación se describen en [Implementación de CV y compatibilidad](IMPLEMENTACION_CV_MATCH.md).

## 1. Archivos y privacidad

- Admitir PDF, DOCX, ODT y TXT; habilitar DOC y RTF solo cuando el conversor aislado esté disponible.
- Limitar tamaño, dimensiones, expansión de archivos comprimidos y volumen de texto extraído. Detectar el formato por contenido además de la extensión.
- Rechazar archivos cifrados, corruptos, con extensión falsa o que excedan límites. Un error de escaneo nunca se interpreta como aprobación.
- Guardar los CV en almacenamiento privado y entregar cada archivo solo a su propietario autenticado. No incluir CV ni datos personales en logs.
- Procesar imágenes con límites de bytes y píxeles, normalizar el formato y remover metadatos.

## 2. Versiones y consistencia

Cada CV aceptado genera una versión inmutable identificada por hash. Los análisis, perfiles y resultados de match guardan una referencia a esa versión. Reemplazar el CV invalida la vigencia del perfil anterior, aunque el análisis histórico permanezca disponible. Una respuesta asíncrona tardía no debe publicar resultados de una versión que ya dejó de ser actual.

Los callbacks y reintentos deben ser idempotentes. Los workers adquieren un lease y vuelven a comprobar propietario y versión antes de escribir. Una pérdida de lease impide que el worker antiguo modifique el estado.

## 3. Perfil de habilidades

Cada habilidad debe conservar evidencia y procedencia. Las habilidades técnicas y blandas se clasifican según el tipo explícito del contrato. En perfiles legacy sin tipo, una lista conocida puede apoyar la presentación; no debe prevalecer sobre una categoría explícita. Si falta evidencia suficiente, la habilidad o su nivel debe mantenerse como desconocido. Las correcciones de la persona se guardan sin borrar el análisis histórico.

La extracción debe funcionar con perfiles de distintas profesiones. Las habilidades blandas se infieren desde tareas, decisiones, interacciones y logros descritos; no se fuerzan cuotas ni se deducen rasgos por títulos, sectores o listas de herramientas.

## 4. Requisitos de una oferta

El formulario separa requisitos obligatorios y deseables y permite categorizar cada requisito obligatorio. Experiencia y educación pueden marcarse como obligatorias, deseables o no solicitadas. El contrato estructurado conserva un identificador estable, categoría, origen, texto y condición obligatoria.

El modelo no decide por sí solo que un requisito es excluyente. No debe transformar un deseable en obligatorio, inferir licencias ni convertir la ausencia de información en evidencia negativa. Los datos ambiguos se exponen para revisión.

## 5. Evaluación de compatibilidad

La configuración define pesos para competencias técnicas, habilidades blandas, experiencia, educación, idiomas, logística/modalidad y deseables. Los borradores pueden quedar incompletos; para publicar, la suma debe ser exactamente 100%. La API valida los valores y el hash de configuración independientemente del navegador.

Un resultado guarda los pesos usados, la fecha, las versiones de perfil y el desglose por dimensión y requisito. El porcentaje, la cobertura de evidencia y la confianza son señales distintas. El cumplimiento obligatorio se informa por separado (`all_met`, `not_met`, `unknown`); un peso cero no elimina el estado obligatorio. Las dimensiones sin requisitos aplicables se identifican como tales.

## 6. Interfaz y lenguaje

La carga, análisis y evaluación muestran estados comprensibles y recuperables tras recarga o desconexión. El resultado debe indicar cuándo el perfil quedó obsoleto y permitir revisar la evidencia. Todo texto visible se presenta en español, aunque el CV o la oferta estén en otro idioma.

La explicación deja claro que un porcentaje de compatibilidad no representa una probabilidad de contratación. No se debe bloquear una postulación automáticamente por el porcentaje; cualquier regla de elegibilidad debe estar explícita en el requisito correspondiente.

## 7. Criterios de aceptación

- Un CV que supere el límite se rechaza antes de reemplazar la versión anterior.
- Un usuario anónimo o una cuenta distinta no puede descargar el CV ni leer o reemplazar el perfil de otra persona.
- Al reemplazar CV A por B, un callback tardío de A no publica A como perfil vigente ni habilita un match basado en A.
- Los callbacks repetidos no duplican análisis, perfiles o resultados.
- Un requisito deseable no se presenta como obligatorio y un obligatorio con peso cero sigue visible en el estado de cumplimiento.
- La suma inválida de pesos se rechaza en backend; un resultado histórico conserva la configuración de su evaluación.
- Los tests automáticos usan datos sintéticos y respuestas controladas. La calidad de inferencia requiere evaluación aparte con un conjunto de referencia revisado.

## 8. Operación y cambios de esquema

Las migraciones deben ser aditivas y preservar relaciones históricas. Antes de activar escritores nuevos, desplegar lectores compatibles y aplicar el esquema. Los cambios reversibles se desactivan mediante configuración; no se eliminan perfiles, archivos ni resultados históricos para revertir una versión. Las dependencias del conversor, escáner y base de datos deben fijarse y verificarse en cada entorno de despliegue.
