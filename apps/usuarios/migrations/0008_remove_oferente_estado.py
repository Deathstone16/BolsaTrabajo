from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0007_alter_oferente_id_alter_postulante_id_and_more"),
        ("usuarios", "0007_oferente_estado"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="oferente",
                    name="estado",
                ),
            ],
        ),
    ]