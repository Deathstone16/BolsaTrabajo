from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("categorias", "0006_proteger_categorias_en_uso"),
        ("cursos", "0005_alter_curso_categoria_delete_categoria"),
    ]

    operations = [
        migrations.AlterField(
            model_name="curso",
            name="categoria",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="categorias.categoria"),
        ),
    ]
