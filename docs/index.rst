IEN Trabajo
===========

Documentación de Bolsa de Trabajo IEN organizada según los siete componentes
mínimos de la guía. Los planes, evaluaciones y reportes históricos se conservan
separados de los procedimientos actuales.

.. toctree::
   :maxdepth: 1
   :caption: Guía y siete componentes

   README
   inicio/proyecto
   requisitos/index
   arquitectura/general
   api/contratos
   datos/modelo-datos
   operaciones/despliegue
   pruebas/estrategia

.. toctree::
   :maxdepth: 1
   :caption: Guías complementarias

   requisitos/diseno-cv-ofertas-match
   arquitectura/implementacion-cv-match
   arquitectura/adr/001-persistencia-y-cv
   arquitectura/adr/002-integracion-asincrona
   operaciones/inicio-local-windows
   operaciones/postgresql
   operaciones/cloudflare-tunnel
   operaciones/cola-cuotas-ia
   funcionalidades/recomendaciones-cursos
   pruebas/plan-integracion
   pruebas/datos-demo

.. toctree::
   :maxdepth: 1
   :caption: Evaluaciones e historial

   pruebas/evaluaciones/gemini-2026-10-21
   pruebas/evaluaciones/cobertura-habilidades-v6
   pruebas/reportes/resultados-2026-10-21
   historial/integracion-match-2026-10-22
   historial/revision-documental-2026-10-22

Esta documentación combina una introducción al proyecto, referencias generadas
desde los módulos Django y guías operativas en Markdown. Para poner en marcha
el entorno local, consultar :doc:`referencia/primeros-pasos`; para preparar una
instalación en servidor, seguir la guía de despliegue.

.. toctree::
   :maxdepth: 2
   :caption: Referencia y mantenimiento

   referencia/primeros-pasos
   referencia/arquitectura-mvt
   referencia/documentacion-integrada
   referencia/apps/index
   mantenimiento/analisis-limpieza
   mantenimiento/reorganizacion-documentacion
   DESPLIEGUE_VPS
   IMPLEMENTACION_VPS_2026-10-29
   INFERENCIA_CV_V7

Índices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
