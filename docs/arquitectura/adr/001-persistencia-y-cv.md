# ADR-001: persistencia relacional y archivos privados

Fecha: 22/10/2026. Estado: decisión observada en la implementación.

**Contexto.** Usuarios, ofertas y resultados requieren relaciones e integridad. Un CV contiene datos personales y sus bytes no deben quedar accesibles en medios públicos.

**Decisión.** Usar ORM Django con SQLite para desarrollo y PostgreSQL obligatorio con `DEBUG=false`. Guardar metadatos/versiones de CV en BD y archivos en `private_uploads/cv/`; entregar archivos mediante vista autorizada. Usar `PROTECT` en categorías y configuraciones referenciadas; conservar snapshots y hashes para trazabilidad.

**Consecuencias.** Se necesita respaldar base y archivos de forma consistente. Una transacción SQL no revierte automáticamente un archivo ya escrito. El borrado de una fila con `FileField` no implica eliminación física garantizada. El proxy debe bloquear también árboles públicos heredados de CV.

**Alternativas.** Guardar los bytes en la BD aumenta el tamaño y costo de backup; servir CV bajo `/media/` no ofrece el control de acceso requerido. Almacenamiento de objetos privado es una evolución posible, aún no configurada aquí.

Fuentes: `ientrabajo/settings/base.py`, `ia/models.py`, `usuarios/services.py`, `usuarios/management/commands/migrar_cv_privados.py`.
