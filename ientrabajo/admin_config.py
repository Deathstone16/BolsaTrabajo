"""Configure the technical admin without changing application registrations."""
from django.contrib.admin.apps import AdminConfig


class TechnicalAdminConfig(AdminConfig):
    default_site = 'ientrabajo.admin_site.TechnicalAdminSite'
