Arquitectura
============

La aplicación utiliza el patrón MVT de Django:

* **Model**: representa usuarios, perfiles, ofertas, cursos y categorías.
* **View**: recibe solicitudes HTTP, delega reglas a servicios y construye
  respuestas HTML, redirecciones o JSON.
* **Template**: presenta la interfaz y contiene la integración mínima con
  JavaScript necesaria para formularios y modales.

Capas del proyecto
------------------

``models.py``
   Persistencia y reglas propias de cada entidad.

``forms.py``
   Conversión, validación y limpieza de datos ingresados por usuarios.

``services.py``
   Casos de uso y consultas que no pertenecen a la capa HTTP.

``views.py``
   Coordinación de solicitudes, permisos y respuestas.

``dtos.py``
   Estructuras explícitas para serializar información destinada a JavaScript.

``state.py`` y ``estado_oferente.py``
   Implementaciones del patrón State para controlar transiciones válidas.
