from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0013_alter_oferente_estado_validacion"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE usuarios_oferente DROP COLUMN estado;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[],
        ),
    ]