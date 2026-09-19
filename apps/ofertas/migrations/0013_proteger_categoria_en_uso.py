from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("categorias", "0006_proteger_categorias_en_uso"),
        ("ofertas", "0012_backfill_habilidades_duras"),
    ]

    operations = [
        migrations.AlterField(
            model_name="oferta",
            name="categoria",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="categorias.categoria"),
        ),
    ]
