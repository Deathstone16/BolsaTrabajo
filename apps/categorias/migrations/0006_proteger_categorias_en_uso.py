from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("categorias", "0005_alter_habilidad_unique_together_habilidad_categoria_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="habilidad",
            name="categoria",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="categorias.categoria"),
        ),
    ]
