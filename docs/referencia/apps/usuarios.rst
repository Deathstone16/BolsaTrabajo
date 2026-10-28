Usuarios y perfiles
===================

Gestiona la identidad basada en correo y los perfiles separados de postulantes
y empresas oferentes. Los formularios validan el registro, los datos del perfil
y los archivos; los servicios concentran autenticación, recuperación de acceso,
validación de empresas y operaciones sobre el CV. Las vistas conectan esos
flujos con las páginas de la aplicación. Los decoradores restringen funciones
según rol y estado de validación, mientras ``estado_oferente`` representa los
estados de revisión y la posibilidad de publicar.

.. automodule:: usuarios.models

.. automodule:: usuarios.forms

.. automodule:: usuarios.services

.. automodule:: usuarios.views

.. automodule:: usuarios.decorators

.. automodule:: usuarios.estado_oferente
