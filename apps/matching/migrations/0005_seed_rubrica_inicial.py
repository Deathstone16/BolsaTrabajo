from decimal import Decimal

from django.db import migrations
from django.utils import timezone


def crear_rubrica_inicial(apps, schema_editor):
    Configuracion = apps.get_model('matching', 'ConfiguracionCompatibilidad')
    Activa = apps.get_model('matching', 'ConfiguracionActiva')
    config, _ = Configuracion.objects.get_or_create(
        version='rubrica-inicial-v1',
        defaults={
            'technical_skills': Decimal('35.00'),
            'soft_skills': Decimal('15.00'),
            'experience': Decimal('20.00'),
            'education': Decimal('10.00'),
            'languages': Decimal('5.00'),
            'logistics': Decimal('5.00'),
            'desirables': Decimal('10.00'),
            'es_borrador': False,
            'publicada_en': timezone.now(),
        },
    )
    Activa.objects.get_or_create(singleton='actual', defaults={'configuracion_id': config.pk})


class Migration(migrations.Migration):
    dependencies = [('matching', '0004_resultadocompatibilidad_evaluation_date_and_more')]

    operations = [migrations.RunPython(crear_rubrica_inicial, migrations.RunPython.noop)]
