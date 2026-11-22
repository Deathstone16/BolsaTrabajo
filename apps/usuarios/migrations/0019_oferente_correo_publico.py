from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0018_responsable_obligatorio'),
    ]

    operations = [
        migrations.AddField(
            model_name='oferente',
            name='correo_publico',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Correo de contacto público'),
        ),
    ]
