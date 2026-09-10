"""Elimina la columna huerfana `estado` de usuarios_oferente.

La migracion 0007_oferente_estado agrego el campo `estado` (NOT NULL, sin
default a nivel base). Al resolver el merge con la otra rama 0007, la
migracion 0008 lo quito usando SeparateDatabaseAndState con SOLO
state_operations: Django dejo de conocer el campo, pero la columna quedo
viva en la tabla. Todo INSERT en usuarios_oferente fallaba con
"NOT NULL constraint failed: usuarios_oferente.estado", rompiendo el
registro de oferentes por completo.

makemigrations no lo detectaba porque el modelo y el estado si coincidian;
el desfasaje era entre el estado y la base real.

El drop es condicional a proposito. En SQLite un AlterField reconstruye la
tabla a partir del estado del modelo, asi que la 0012 (que altera
estado_validacion) ya se lleva puesta la columna huerfana en una base
creada desde cero. En una base que venia de antes, en cambio, la columna
puede seguir ahi. La migracion tiene que servir para los dos casos.

El campo vigente es `estado_validacion`.
"""

from django.db import migrations

TABLA = "usuarios_oferente"
COLUMNA = "estado"


def drop_columna_si_existe(apps, schema_editor):
    conexion = schema_editor.connection
    with conexion.cursor() as cursor:
        columnas = [
            c.name for c in conexion.introspection.get_table_description(cursor, TABLA)
        ]
        if COLUMNA in columnas:
            cursor.execute(f'ALTER TABLE {TABLA} DROP COLUMN "{COLUMNA}";')


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0013_alter_oferente_estado_validacion"),
    ]

    operations = [
        migrations.RunPython(drop_columna_si_existe, migrations.RunPython.noop),
    ]
