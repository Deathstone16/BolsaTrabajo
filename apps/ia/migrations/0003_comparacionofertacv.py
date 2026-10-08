from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('ia', '0002_unico_analisis_pendiente'),
        ('ofertas', '0013_proteger_categoria_en_uso'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComparacionOfertaCV',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('porcentaje', models.PositiveSmallIntegerField(default=0)),
                ('resultado', models.JSONField(default=dict)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('analisis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparaciones_ofertas', to='ia.analisiscv')),
                ('oferta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparaciones_cv', to='ofertas.oferta')),
                ('postulante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparaciones_ofertas', to='usuarios.postulante')),
            ],
            options={
                'ordering': ['-actualizado_en'],
                'constraints': [models.UniqueConstraint(fields=('postulante', 'oferta', 'analisis'), name='ia_comparacion_unica_por_oferta_y_analisis')],
            },
        ),
    ]
