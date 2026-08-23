import os
import sys

# Paths necesarios
sys.path.insert(0, os.path.abspath('..'))        # raíz del proyecto (ientrabajo/)
sys.path.insert(0, os.path.abspath('../apps'))   # apps/ (cursos, ofertas, etc.)

# Configurar Django antes de importar cualquier modelo
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ientrabajo.settings.base')
import django
django.setup()

# --- Información del proyecto ---
project = 'IEN Bolsa de Trabajo'
copyright = '2026, IEN'
author = 'IEN'
release = '1.0.0'

# --- Extensiones ---
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'myst_parser',
]

# --- Mock solo de PIL (no de Django, ya está configurado) ---
autodoc_mock_imports = [
    'PIL',
]

# --- Configuración de autodoc ---
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_class_content = 'class'

# --- Soporte Markdown ---
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# --- Tema ---
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# --- Idioma español ---
language = 'es'

# --- Napoleon (Google style) ---
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# --- Intersphinx ---
intersphinx_mapping = {
    'django': ('https://docs.djangoproject.com/es/6.0/', None),
}
