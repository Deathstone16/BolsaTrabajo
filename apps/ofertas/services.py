from .models import Oferta, TipoOferta
from django.shortcuts import get_object_or_404

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

def obtener_ofertas_activas(busqueda='', modalidad='', experiencia=''):
    ofertas = Oferta.objects.filter(estado='activa').select_related('empresa__oferente', 'categoria').order_by('-fecha_publicacion')
    if busqueda:
        ofertas = ofertas.filter(titulo__icontains=busqueda) | ofertas.filter(nombre_puesto__icontains=busqueda)
    if modalidad:
        ofertas = ofertas.filter(modalidad=modalidad)
    if experiencia:
        ofertas = ofertas.filter(experiencia_requerida=experiencia)
    return ofertas

def actualizar_estado_oferta(oferta_id, nuevo_estado):
    oferta = obtener_oferta_por_id(oferta_id)
    if oferta:
        oferta.estado = nuevo_estado
        oferta.save()
        return True
    return False


def listar_tipos_oferta():
    return TipoOferta.objects.all()


def crear_tipo_oferta(form):
    return form.save()


def modificar_tipo_oferta(tipo_id, form):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    return form.save()


def eliminar_tipo_oferta(tipo_id):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    nombre = tipo.nombre
    tipo.delete()
    return nombre


def puede_eliminar_tipo_oferta(tipo_id):
    return not Oferta.objects.filter(tipo_oferta_id=tipo_id).exists()
