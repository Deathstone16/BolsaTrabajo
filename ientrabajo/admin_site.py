"""Technical administration is separate from the institute's staff dashboard."""
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError


class TechnicalAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError(self.error_messages['invalid_login'], code='invalid_login', params={'username': self.username_field.verbose_name})


class TechnicalAdminSite(AdminSite):
    site_header = 'Administración técnica de IEN Trabajo'
    site_title = 'Administración técnica'
    login_form = TechnicalAdminAuthenticationForm

    def has_permission(self, request):
        return super().has_permission(request) and request.user.is_superuser
