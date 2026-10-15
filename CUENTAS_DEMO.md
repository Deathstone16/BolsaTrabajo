# Datos de prueba locales

Ingreso: http://127.0.0.1:8000/usuarios/login/

Contraseña común: `DemoIEN2026!`

| Cuenta | Rol / escenario |
| --- | --- |
| postulante@demo.example.test | Lucía, perfil de desarrollo Python/Django |
| marketing@demo.example.test | Mateo, perfil de marketing y contenidos |
| junior@demo.example.test | Sofía, perfil administrativo inicial |
| empresa@demo.example.test | Nube Sur, empresa aprobada |
| agencia@demo.example.test | Estudio Horizonte, empresa aprobada |
| empresa-pendiente@demo.example.test | Empresa pendiente de validación |
| empresa-rechazada@demo.example.test | Empresa rechazada con un motivo |
| moderador@demo.example.test | Moderación de empresas, ofertas y cursos |
| admin@demo.example.test | Administración completa de Django |

Hay 12 ofertas (9 activas, 1 pendiente, 1 rechazada y 1 finalizada), 6 cursos
con imágenes y 27 resultados de compatibilidad ficticios para los 3 postulantes.
Cada postulante tiene un perfil estructurado listo y un análisis de ejemplo.
Los porcentajes preguardados son simulados y no consumen Groq. Las modificaciones
y nuevos análisis solicitados desde la aplicación siguen el flujo real.

Pantallas:

- Buscar ofertas: http://127.0.0.1:8000/ofertas/buscar/
- Mi perfil: http://127.0.0.1:8000/usuarios/mi-perfil/
- Empresa: http://127.0.0.1:8000/ofertas/dashboard/
- Moderación: http://127.0.0.1:8000/moderacion/empresas/
- Cursos: http://127.0.0.1:8000/moderacion/cursos/
- Administrador: http://127.0.0.1:8000/admin/

El proyecto aún no implementa registros de postulaciones a ofertas. El botón
Postularme continúa como Próximamente.

Para restaurar el escenario demo sin duplicar sus registros:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo
```

Solo funciona con `DEBUG=True`. Actualiza exclusivamente cuentas del dominio
reservado `demo.example.test` y los contenidos identificados con `DEMO`.
Restablece las contraseñas de esas cuentas. No envía correos ni llama a IA.
