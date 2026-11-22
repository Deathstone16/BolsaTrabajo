from datetime import timedelta
from django.conf import settings
from django.db import migrations
from django.utils import timezone


def registrar_pendientes(apps, schema_editor):
    Oferente = apps.get_model('usuarios', 'Oferente')
    Solicitud = apps.get_model('moderacion', 'SolicitudEmpresa')
    now = timezone.now()
    alias = schema_editor.connection.alias
    for empresa in Oferente.objects.using(alias).filter(estado_validacion='pendiente').iterator():
        Solicitud.objects.using(alias).get_or_create(
            empresa_id=empresa.pk, resuelta_en__isnull=True,
            defaults={'creada_en': now, 'recordar_desde': now + timedelta(hours=settings.IEN_COMPANY_REMINDER_HOURS)},
        )


class Migration(migrations.Migration):
    dependencies = [('moderacion', '0003_solicitudes_empresa_recordatorios')]
    operations = [migrations.RunPython(registrar_pendientes, migrations.RunPython.noop)]
