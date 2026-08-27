Arquitectura del Proyecto
=========================

Patrones de Diseño
------------------

Patrón State
~~~~~~~~~~~~

Cada dominio que maneja estados (ofertas, validación de empresas) usa un patrón
State. Los estados son **singletons** en un diccionario ``ESTADOS`` y se resuelven
desde el campo de BD.

.. code-block:: text

   Modelo (campo 'estado') → ESTADOS[estado] → Objeto Estado
                                                   ├── aprobar(oferta)
                                                   ├── rechazar(oferta)
                                                   └── finalizar(oferta)

**Archivos:** ``ofertas/state.py``, ``usuarios/estado_oferente.py``

Patrón Service Layer
~~~~~~~~~~~~~~~~~~~~

La lógica de negocio vive en ``services.py`` de cada app. Las views orquestan
llamando a servicios, que encapsulan queries y transacciones.

**Regla:** los services **nunca** importan views. Las views importan services.

Patrón DTO
~~~~~~~~~~

Los endpoints JSON usan Data Transfer Objects (``dataclasses``) para serializar
modelos. Cada DTO tiene un factory method ``desde_modelo()``.

**Archivo:** ``ofertas/dtos.py``

Gestión de Estado de Empresas
------------------------------

.. code-block:: text

   Oferente.estado_validacion:
     pendiente  → puede ver "validación pendiente"
     aprobado   → puede publicar ofertas
     rechazado  → ve motivo, puede corregir y reenviar

**Flujo:** Registro → pendiente → aprobado/rechazado → (si rechazado: editar → pendiente)

Transiciones de Ofertas
-----------------------

.. code-block:: text

   pendiente  → activa     (aprobar)
   pendiente  → rechazada  (rechazar)
   activa     → finalizada (finalizar)
   rechazada  → (no transiciones)
   finalizada → (no transiciones)
