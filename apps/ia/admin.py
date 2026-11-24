from django.contrib import admin
from django.db.models import Count
from django.http import JsonResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import AnalisisCV, TrabajoExtraccion
from .queue_monitor import remote_status


admin.site.register(AnalisisCV)


@admin.register(TrabajoExtraccion)
class CVQueueAdmin(admin.ModelAdmin):
    change_list_template = 'admin/ia/cv_queue.html'
    list_display = ('id', 'analysis_number', 'local_state', 'live_state', 'intentos', 'creado_en', 'actualizado_en')
    list_filter = ('estado', 'creado_en')
    search_fields = ('=id', '=analisis_cv__id', 'remote_job_id')
    list_per_page = 20
    actions = None
    readonly_fields = ('id', 'analisis_cv', 'estado', 'remote_job_id', 'intentos', 'creado_en', 'actualizado_en')
    fields = readonly_fields

    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo=TrabajoExtraccion.Tipo.CV)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    @admin.display(description='Análisis')
    def analysis_number(self, obj):
        return obj.analisis_cv_id or '—'

    @admin.display(description='Estado en la plataforma')
    def local_state(self, obj):
        return LOCAL_LABELS.get(obj.estado, obj.estado)

    @admin.display(description='Estado en IA')
    def live_state(self, obj):
        if obj.estado == TrabajoExtraccion.Estado.COMPLETADO:
            return 'Completado y recibido'
        if obj.estado == TrabajoExtraccion.Estado.ERROR:
            return 'Error registrado'
        if not obj.remote_job_id:
            return 'Pendiente de envío'
        return format_html('<span class="cv-live-status" data-url="{}">Consultando…</span>',
                           reverse('admin:ia_cv_queue_status', args=[obj.pk]))

    def get_urls(self):
        return [path('<int:job_id>/estado-ia/', self.admin_site.admin_view(self.status_view),
                     name='ia_cv_queue_status')] + super().get_urls()

    def status_view(self, request, job_id):
        if not self.has_view_permission(request):
            return JsonResponse({'message': 'Sin permiso.'}, status=403)
        job = self.get_queryset(request).filter(pk=job_id).first()
        if job is None:
            return JsonResponse({'message': 'Trabajo no encontrado.'}, status=404)
        response = JsonResponse(remote_status(job))
        response['Cache-Control'] = 'no-store'
        return response

    def changelist_view(self, request, extra_context=None):
        counts = dict(self.get_queryset(request).values('estado').annotate(total=Count('id')).values_list('estado', 'total'))
        pending = sum(n for state, n in counts.items() if state not in ('completed', 'error'))
        context = {'title': 'Cola de CV', 'queue_pending': pending,
                   'queue_completed': counts.get('completed', 0), 'queue_failed': counts.get('error', 0)}
        context.update(extra_context or {})
        return super().changelist_view(request, extra_context=context)


LOCAL_LABELS = {
    'pending': 'Pendiente de envío', 'sending': 'Enviando', 'accepted': 'Aceptado por IA',
    'processing': 'Procesando', 'completed': 'Completado', 'error': 'Error',
    'delivery_unknown': 'Envío por confirmar',
}
