from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ofertas', '0015_oferta_educacion_clasificacion_and_more')]
    operations = [migrations.AlterField(
        model_name='oferta', name='estado',
        field=models.CharField(max_length=20, default='pendiente', choices=[
            ('pendiente', 'Sin publicar'), ('activa', 'Publicada'),
            ('rechazada', 'No publicada'), ('finalizada', 'Finalizada'),
        ]),
    )]
