# Documentación de Bolsa de Trabajo IEN

Fecha de revisión: 22/10/2026. Basada en `Guia_documentacion.pdf` y en el código local de BolsaTrabajo. Documenta el estado local revisado; algunos documentos pueden estar todavía sin confirmar en Git. Esta entrega documenta el sistema; no acredita un despliegue ni una ejecución integral de pruebas.

## Producto y alcance

Bolsa de Trabajo IEN conecta postulantes con empresas y vincula las brechas de competencias con cursos. Permite registrar cuentas, validar empresas, moderar ofertas, administrar catálogos, guardar favoritas, gestionar CV privados y consultar análisis y compatibilidad mediante un servicio externo de IA.

Los actores son visitante, postulante, empresa y personal de moderación/administración. Los perfiles Postulante y Oferente se vinculan con Usuario. Los permisos efectivos dependen de decoradores, formularios y vistas; la base no impone exclusión entre ambos perfiles.

No existe una entidad de postulación laboral ni un proceso persistido de selección/contratación en los modelos actuales. Guardar una favorita o calcular compatibilidad no registra una candidatura.

## Arquitectura de un vistazo

![Arquitectura lógica simplificada de Bolsa de Trabajo IEN](arquitectura/diagramas/arquitectura-logica.svg)

[Ver la explicación de arquitectura](arquitectura/general.md) · [Descargar PNG](arquitectura/diagramas/arquitectura-logica.png).

## Los siete componentes de la guía

Cada componente del PDF tiene su propio archivo `.md` dentro de `docs/`. Los enlaces de esta tabla son relativos al repositorio y permiten navegar en GitHub. Los diagramas de arquitectura y datos están incluidos en bloques Mermaid dentro de los Markdown.

| N.º | Componente | Entrega y evidencia | Responsable sugerido |
| --- | --- | --- | --- |
| 01 | Inicio y configuración | [Presentación e instalación](inicio/proyecto.md); `README.md` (raíz del repositorio) | Responsable técnico |
| 02 | Requisitos y aceptación | [Backlog funcional](requisitos/index.md) | Referente funcional + responsable de módulo |
| 03 | Arquitectura y decisiones | [Arquitectura](arquitectura/general.md) y ADR | Responsable técnico |
| 04 | Contratos de integración | [HTTP, callbacks y WebSocket](api/contratos.md) | Responsables Django/FastAPI |
| 05 | Modelo de datos | [Modelo y diccionario](datos/modelo-datos.md), [ER editable](datos/modelo-datos.mmd) | Responsable de datos |
| 06 | Despliegue y operación | [Procedimientos](operaciones/despliegue.md) | Infraestructura + desarrollo |
| 07 | Pruebas y calidad | [Estrategia](pruebas/estrategia.md) | Equipo de desarrollo |

## Estado y límites de la entrega

- El esquema documentado contiene 21 entidades propias; las tablas técnicas de Django y las tablas puente se aclaran por separado.
- Los contratos del servicio de IA se describen desde sus consumidores en este repositorio. La implementación FastAPI, Celery y sus OpenAPI no están disponibles en esta carpeta y deben contrastarse antes de integrar una versión nueva.
- Los procedimientos productivos son una propuesta reproducible: no se encontró configuración de hosting, unidades systemd ni un pipeline CI de pruebas en `.github`.
- La retención, los objetivos de recuperación y los responsables personales todavía requieren definición institucional. No se inventaron plazos ni resultados de pruebas.

## Mantenimiento

Actualizar README y operación al cambiar comandos o configuración; requisitos al modificar el comportamiento; arquitectura y ADR al alterar límites o protocolos; contratos ante cualquier cambio observable; modelo y migraciones ante cambios del esquema; pruebas cuando cambian riesgos o rutas críticas. Cada PR debe actualizar los componentes afectados. El backlog de esta entrega es el índice funcional inicial; los identificadores RF deben reutilizarse al vincular tareas o issues reales.

## Fuentes de implementación

Modelos y migraciones de `apps/{usuarios,categorias,ofertas,cursos,ia,matching}`; rutas y vistas; `ientrabajo/settings/base.py` y `ientrabajo/asgi.py`; contratos Pydantic de `ien_contracts/models.py`; comandos de despacho; `requirements.txt`; `package.json`; documentación técnica existente. La guía adjunta se usó como estructura de la entrega, sin ejecutar instrucciones ajenas a la solicitud del usuario.

## Documentación complementaria ordenada

| Carpeta | Contenido |
| --- | --- |
| `inicio/` | Presentación, prerrequisitos y recorrido de puesta en marcha. |
| `requisitos/` | Backlog y requisitos de diseño de CV/ofertas/matching. |
| `arquitectura/` | Arquitectura actual, implementación y decisiones ADR. |
| `api/` | Contratos HTTP, callbacks y WebSocket. |
| `datos/` | Modelo, diccionario y fuente ER Mermaid. |
| `operaciones/` | Despliegue, PostgreSQL, túnel, arranque Windows y referencia de cuotas. |
| `pruebas/` | Estrategia, plan de integración, cuentas demo, reportes y evaluaciones. |
| `funcionalidades/` | Detalles de recomendaciones de cursos. |
| `referencia/` | Referencia técnica Sphinx y páginas breves originales. |
| `historial/` | Integraciones y revisiones fechadas. |
| `mantenimiento/` | Inventario de movimientos y análisis de limpieza. |

Los informes fechados describen sus propias ejecuciones y no reemplazan las instrucciones actuales. Las notas dependientes de una rama o proveedor tienen avisos de vigencia.

## Revisión de orden y limpieza

- [Análisis de archivos sobrantes y deuda técnica](mantenimiento/analisis-limpieza.md).
- [Mapa de rutas anteriores y actuales](mantenimiento/reorganizacion-documentacion.md).

## PDF integrado

La [documentación completa en PDF](referencia/documentacion-bolsatrabajo-ien.pdf) se conserva como referencia de la entrega original. El [índice de integración](referencia/documentacion-integrada.md) vincula cada capítulo y sus páginas con los Markdown actuales e incluye la arquitectura reconstruida sin recortes.

Los Markdown de este índice son la versión editable mantenida y contienen las nuevas ubicaciones; el PDF conserva la exportación original.
