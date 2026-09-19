"""Configuración de Sphinx para la documentación técnica de IEN Trabajo."""

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPS_ROOT = PROJECT_ROOT / "apps"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(APPS_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ientrabajo.settings.base")

import django

django.setup()

project = "IEN Trabajo"
author = "Equipo IEN Trabajo"
language = "es"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
