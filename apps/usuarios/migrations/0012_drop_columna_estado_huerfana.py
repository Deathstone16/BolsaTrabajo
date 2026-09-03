from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0011_oferente_motivo_rechazo"),
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