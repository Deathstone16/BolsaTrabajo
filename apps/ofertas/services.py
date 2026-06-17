from .models import Oferta

def crear_oferta_laboral(usuario_empresa, form_oferta):
    
    oferta = form_oferta.save(commit=False)
    oferta.empresa = usuario_empresa
    oferta.estado = 'pendiente'
    oferta.save()
    
    return oferta

def obtener_ofertas_por_empresa(usuario_empresa):
    return Oferta.objects.filter(empresa=usuario_empresa).order_by('-fecha_publicacion')

def obtener_oferta_por_id(id_oferta):
    try:
        return Oferta.objects.get(id=id_oferta)
    except Oferta.DoesNotExist:
        return None
    
def eliminar_oferta_por_id(oferta_id):
    oferta = obtener_oferta_por_id(oferta_id)
    if oferta:
        oferta.delete()
        return True
    return False
