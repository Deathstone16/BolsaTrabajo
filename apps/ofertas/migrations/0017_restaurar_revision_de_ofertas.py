from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ofertas', '0016_actualizar_etiquetas_publicacion')]
    operations = [migrations.AlterField(
        model_name='oferta', name='estado',
        field=models.CharField(max_length=20, default='pendiente', choices=[
            ('pendiente', 'Pendiente de aprobación'), ('activa', 'Publicada'),
            ('rechazada', 'Rechazada'), ('finalizada', 'Finalizada'),
        ]),
    )]
