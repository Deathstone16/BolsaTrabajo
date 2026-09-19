Primeros pasos
==============

Requisitos
----------

* Python 3.11 o superior.
* Las dependencias declaradas en ``requirements.txt``.
* Las variables de correo opcionales definidas en ``.env.example``.

Preparación local
-----------------

Desde la raíz del proyecto en Windows::

   .\.venv\Scripts\python.exe manage.py migrate
   .\.venv\Scripts\python.exe manage.py runserver

Comprobaciones
--------------

Antes de integrar cambios se recomienda ejecutar::

   .\.venv\Scripts\python.exe manage.py check
   .\.venv\Scripts\python.exe manage.py test

Generar esta documentación
---------------------------

La documentación HTML se genera con::

   .\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html

El punto de entrada resultante es ``docs/_build/html/index.html``.
