from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ia', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='analisiscv',
            constraint=models.UniqueConstraint(
                condition=models.Q(estado='pendiente'),
                fields=('postulante',),
                name='ia_unico_analisis_pendiente_por_postulante',
            ),
        ),
    ]
