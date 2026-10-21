"""Campos compartidos por los formularios del flujo principal."""
from django import forms


class DescripcionField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'Descripción')
        kwargs.setdefault('max_length', 2000)
        kwargs.setdefault('widget', forms.Textarea(attrs={'class': 'input-ien', 'rows': 5}))
        kwargs.setdefault('error_messages', {'max_length': 'La descripción admite hasta %(limit_value)s caracteres. Acortá el texto para continuar.'})
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        # Permitimos escribir de más para mostrar el exceso y corregirlo; el servidor lo rechaza.
        attrs.pop('maxlength', None)
        attrs['data-character-limit'] = str(self.max_length)
        return attrs
