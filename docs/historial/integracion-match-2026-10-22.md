# Integración local del detalle del match

Se incorporaron los cambios del PR #60 de Benja, fijados al commit `a524714`, sobre `fix/correcciones_ia`. Se mantuvieron las correcciones locales de requisitos pendientes y de versiones de perfil. El PR remoto continúa independiente; esta integración no modifica GitHub.

## Comportamiento

- La pantalla privada `/matching/resultado/<request_id>/` muestra el desglose, los requisitos y sus explicaciones. Conserva el escape de HTML y el control por propietario.
- Un resultado guardado se renderiza completo desde Django: porcentaje, arco y enlace. La recarga no inicia otro cálculo ni anima el contador desde cero.
- Sin resultado se muestra «Sin calcular»; durante el trabajo, «Calculando». No se presenta 0% como progreso ficticio. Un resultado real de 0% se muestra correctamente.
- Los trabajos pendientes reanudan polling/WebSocket al cargar la oferta o recuperarla desde la caché de navegación. Una respuesta pendiente retrasada no reemplaza un resultado ya completado.
- Se incorporó el supervisor de memoria del parser PDF para macOS. La ruta Windows conserva su límite existente; el supervisor macOS no se ejecutó en este equipo.

## Validación

`manage.py test ia matching usuarios.test_process_limits --noinput`: 61 pruebas aprobadas y una omitida por requerir macOS, usando una base de pruebas nueva.

`npm run test:e2e:live`: seis E2E aprobados en 1,6 minutos. Incluyen resultado 0% sin JavaScript, privacidad del detalle, análisis/callback y matching reales, recarga durante el trabajo, recarga de un resultado terminado sin estados transitorios ni POST de recálculo, vigencia del CV y vista móvil. Ejecución `2026-10-22T04-18-30-367Z-9b29d146`; limpieza final de cuatro usuarios, cuatro ofertas y cuatro archivos sintéticos confirmada.

Los cambios están activos localmente. No se crearon commits ni se subieron modificaciones en esta tarea.
