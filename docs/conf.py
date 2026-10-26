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
from pygments.lexers.special import TextLexer
from sphinx.highlighting import lexers

django.setup()

# Keep editable diagram/environment sources readable without an extra renderer.
lexers["mermaid"] = TextLexer()
lexers["dotenv"] = TextLexer()

project = "IEN Trabajo"
author = "Equipo IEN Trabajo"
language = "es"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "member-order": "bysource",
}
# El inventario de Django no se importa aquí: evitar vínculos rotos a clases
# base y anotaciones de dependencias externas en el HTML generado.
autodoc_typehints = "none"
nitpick_ignore = [("py:class", "optional")]
