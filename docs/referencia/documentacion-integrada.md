# Integración del PDF y la arquitectura de referencia

Revisión: 22/10/2026. Se integra la documentación de 37 páginas suministrada por el usuario y se vincula con los Markdown actuales. El archivo coincide con la exportación previa del proyecto; su contenido principal ya estaba distribuido en los siete componentes, por lo que no se crea una segunda copia de cada capítulo en Markdown.

## PDF de referencia

[Consultar o descargar la documentación completa en PDF](documentacion-bolsatrabajo-ien.pdf).

El PDF se conserva sin alteraciones como referencia de la entrega original. Los Markdown enlazados abajo son la versión mantenida: incluyen la reorganización posterior y enlaces actuales. Las rutas de documentos que aparecen escritas dentro del PDF pueden corresponder a sus ubicaciones anteriores; consultar el [mapa de reorganización](../mantenimiento/reorganizacion-documentacion.md).

## Correspondencia entre capítulos y Markdown

La numeración corresponde a las páginas físicas del PDF, incluida la portada.

| Páginas | Contenido del PDF | Documentación editable actual |
| --- | --- | --- |
| 1–2 | Portada y contenido | [Índice de documentación](../README.md) |
| 3–4 | Guía, alcance y mantenimiento | [Guía general](../README.md) y [presentación e instalación](../inicio/proyecto.md) |
| 5–6 | Requisitos y criterios de aceptación | [Requisitos](../requisitos/index.md) |
| 7–9 | Arquitectura general | [Arquitectura actual y diagrama completo](../arquitectura/general.md) |
| 10 | Persistencia y archivos privados | [ADR-001](../arquitectura/adr/001-persistencia-y-cv.md) |
| 11 | Integración asíncrona e idempotencia | [ADR-002](../arquitectura/adr/002-integracion-asincrona.md) |
| 12–14 | Contratos HTTP y WebSocket | [Contratos de API e integración](../api/contratos.md) |
| 15–31 | Modelo, diagramas, diccionario, integridad y retención | [Modelo de datos completo](../datos/modelo-datos.md) y [fuente ER](../datos/modelo-datos.mmd) |
| 32–34 | Despliegue y operación | [Procedimientos operativos](../operaciones/despliegue.md) |
| 35–36 | Pruebas y calidad | [Estrategia de pruebas](../pruebas/estrategia.md) |
| 37 | Revisión documental | [Registro de revisión original](../historial/revision-documental-2026-10-22.md) |

## Arquitectura reconstruida

![Arquitectura lógica simplificada reconstruida, sin recortes](../arquitectura/diagramas/arquitectura-logica.svg)

Se tomó la captura como guía de composición y componentes. Se reconstruyeron texto, cajas y flechas en un archivo nuevo, sin la interfaz de chat ni recortes. El proveedor LLM se conecta al procesamiento asíncrono; PostgreSQL permanece como persistencia de Django. La [arquitectura general](../arquitectura/general.md) explica los transportes y límites con mayor detalle.

Archivos disponibles:

- [SVG escalable para GitHub](../arquitectura/diagramas/arquitectura-logica.svg).
- [PNG de 2400 × 2640 píxeles](../arquitectura/diagramas/arquitectura-logica.png).
- [Mermaid editable](../arquitectura/diagramas/arquitectura-logica.mmd).

Para regenerar SVG y PNG desde la raíz, con las dependencias Python del proyecto:

```bash
.venv/bin/python scripts/generar_diagrama_arquitectura.py
```

El script no usa la captura ni servicios externos. La fuente Mermaid describe las mismas relaciones; debe mantenerse consistente al cambiar la arquitectura. La configuración de Git permite expresamente este PDF bajo `docs/referencia/`, aunque los PDF temporales continúan ignorados por la regla general.
