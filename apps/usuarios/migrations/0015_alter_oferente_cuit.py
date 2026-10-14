import usuarios.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0014_drop_columna_estado_huerfana'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oferente',
            name='cuit',
            field=models.CharField(max_length=13, validators=[usuarios.validators.validar_cuit]),
        ),
    ]
