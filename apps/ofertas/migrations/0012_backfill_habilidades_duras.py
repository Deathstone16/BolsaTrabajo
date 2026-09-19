from django.db import migrations
from django.db.models import F


def copiar_habilidades_heredadas(apps, schema_editor):
    Oferta = apps.get_model("ofertas", "Oferta")
    (
        Oferta.objects.filter(habilidades_duras="", habilidades_blandas="")
        .exclude(habilidades_requeridas="")
        .update(habilidades_duras=F("habilidades_requeridas"))
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ofertas", "0011_add_habilidades_duras_blandas"),
    ]

    operations = [
        migrations.RunPython(
            copiar_habilidades_heredadas,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
