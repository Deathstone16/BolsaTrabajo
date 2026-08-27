Primeros Pasos
==============

Instalación
-----------

1. Clonar el repositorio:

   .. code-block:: bash

      git clone <url-del-repo>
      cd BolsaTrabajo

2. Crear entorno virtual e instalar dependencias:

   .. code-block:: bash

      python -m venv venv
      venv\Scripts\activate
      pip install -r requirements.txt

3. Crear archivo ``.env`` desde ``.env.example`` y configurar variables.

4. Aplicar migraciones:

   .. code-block:: bash

      python manage.py migrate

5. Crear superusuario:

   .. code-block:: bash

      python manage.py createsuperuser

6. Arrancar el servidor:

   .. code-block:: bash

      python manage.py runserver

Estructura del Proyecto
-----------------------

.. code-block:: text

   BolsaTrabajo/
   ├── apps/               ← Apps de Django
   │   ├── usuarios/       ← Autenticación y perfiles
   │   ├── ofertas/        ← Ofertas laborales
   │   ├── moderacion/     ← Panel de moderación
   │   ├── cursos/         ← Cursos del instituto
   │   └── categorias/     ← Categorías y habilidades
   ├── ientrabajo/         ← Configuración de Django
   ├── templates/          ← Templates HTML
   ├── static/             ← CSS, JS, imágenes
   └── docs/               ← Esta documentación

Generar Documentación
---------------------

.. code-block:: bash

   cd docs
   make html

La documentación se genera en ``docs/_build/html/index.html``.
