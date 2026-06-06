from .models import Oferta

def crear_oferta_laboral(usuario_empresa, form_oferta):
    
    oferta = form_oferta.save(commit=False)
    oferta.empresa = usuario_empresa
    oferta.estado = 'pendiente'
    oferta.save()
    
    return oferta