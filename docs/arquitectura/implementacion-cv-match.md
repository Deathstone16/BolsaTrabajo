# CV privado, requisitos de ofertas y matching

Este documento resume el comportamiento implementado en Django y la API para la carga de CV, la extracción de perfiles y la evaluación de compatibilidad.

## Archivos de usuarios

Los CV admitidos son PDF, DOCX, ODT y TXT. DOC y RTF dependen de que el conversor aislado esté habilitado en el despliegue. Las cargas tienen un límite de 5 MiB y se validan por contenido, estructura y límites de extracción; los archivos rechazados no sustituyen la versión vigente. El escaneo falla de forma cerrada si no puede completarse.

Los DOCX pueden conservar hipervínculos y plantillas de Word vinculadas, incluso si la plantilla apunta a Internet, a un archivo local o a una carpeta de red. La validación y el análisis leen únicamente el texto XML incluido en el DOCX: no descargan ni abren esas referencias. Se mantienen los rechazos de macros, objetos activos, otros recursos externos, XML inválido y archivos que exceden los límites. Esta excepción corresponde a DOCX; no cambia el tratamiento de recursos externos en ODT ni el conversor aislado de DOC/RTF.

Fotos de perfil, logos y banners se validan y normalizan según límites de tamaño y dimensiones. Se eliminan metadatos de las imágenes procesadas.

Los archivos de CV se almacenan fuera de los medios públicos. Cada carga crea un `CVVersion` inmutable con hash, formato, tamaño y nombre original. `Postulante.cv_version_actual` apunta a la versión vigente. La descarga requiere autenticación y verifica que la versión pertenezca al postulante; no se genera una URL pública. El comando `migrar_cv_privados` traslada los archivos heredados conservando sus referencias y evita sobrescribir versiones existentes.

## Perfiles y extracción

El perfil se guarda junto con la versión de CV que lo originó. La vista y el matching descartan un perfil cuya versión ya no coincide con el CV vigente. Las habilidades conservan nombre, evidencia, citas, nivel, origen y tipo. Los tipos `technical` y `soft` prevalecen; la compatibilidad con perfiles anteriores clasifica por nombre únicamente cuando falta el tipo o figura como `unknown`.

La API recibe los trabajos de extracción y normalización mediante contratos versionados. Django conserva snapshots de entrada, estado y errores controlados. La capa asíncrona usa una outbox, claves de idempotencia y leases para recuperar entregas sin duplicar resultados. Los workers vuelven a leer y bloquear las entidades propietarias antes de publicar, por lo que una tarea antigua no puede sobrescribir un perfil más nuevo.

## Requisitos de ofertas

Cada oferta guarda requisitos obligatorios y deseables por separado. Los requisitos estructurados incluyen identificador, categoría, origen y estado obligatorio. La experiencia y la educación admiten clasificación explícita como obligatorias, deseables o no solicitadas. La edición de ofertas heredadas permite revisar y confirmar su clasificación antes de generar el perfil actualizado.

La salida del modelo no convierte un requisito deseable en obligatorio. Si la evidencia es insuficiente o hay contradicciones, estas se conservan como desconocidas o para revisión en lugar de inventar credenciales, niveles o experiencia.

## Evaluación de compatibilidad

La configuración contiene siete dimensiones: competencias técnicas, habilidades blandas, experiencia, educación, idiomas, logística y modalidad, y requisitos deseables. Los valores iniciales son 35/15/20/10/5/5/10. Los borradores pueden editarse; una configuración publicada debe sumar exactamente 100% y queda inmutable.

Cada resultado guarda el hash y snapshot de pesos usados, versiones y hashes de ambos perfiles, fecha de evaluación, desglose por dimensión y juicio por requisito. La cobertura y confianza se presentan separadas del porcentaje. El estado de cumplimiento obligatorio se informa aparte: `all_met`, `not_met` o `unknown`. Un peso cero no elimina un requisito obligatorio. La caché identifica la configuración, versiones de perfiles y fecha para evitar reutilizar una evaluación obsoleta.

Los endpoints de cálculo y estado verifican la identidad del postulante y su relación con el trabajo. Las actualizaciones protegidas por lease impiden escrituras tardías de workers que perdieron el bloqueo. WebSocket y polling permiten recuperar el estado si una conexión se interrumpe.

## Configuración y verificación

En producción, seleccionar PostgreSQL mediante `DB_ENGINE=postgresql`, definir las variables requeridas y habilitar verificación TLS con certificados del entorno. SQLite se mantiene para desarrollo y pruebas. Aplicar migraciones antes de iniciar los workers.

Las pruebas cubren límites y formatos de archivo, almacenamiento y descargas privadas, reemplazo de versiones, callbacks e idempotencia, concurrencia, requisitos obligatorios/deseables, publicación de pesos y pertenencia de los resultados. Las pruebas de integración usan datos sintéticos; una ejecución satisfactoria del circuito no mide la precisión estadística del modelo para todos los rubros.
