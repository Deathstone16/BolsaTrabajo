"""
Servicios de gestión de ofertas laborales.

CRUD de ofertas, búsqueda con filtros, cambio de estados
y funciones de utilidad para el dominio de ofertas.
"""

from .models import Oferta

from django.shortcuts import get_object_or_404

from categorias.models import TipoOferta, Habilidad


def crear_oferta_laboral(usuario_empresa, form_oferta):
    """Crea una oferta laboral asociada a una empresa.

    Args:
        usuario_empresa: Instancia de Usuario (la empresa).
        form_oferta: Formulario con datos de la oferta.

    Returns:
        Oferta: Instancia de la oferta creada.
    """
    
    oferta = form_oferta.save(commit=False)
    oferta.empresa = usuario_empresa
    oferta.estado = 'pendiente'
    oferta.save()
    
    return oferta


def obtener_ofertas_por_empresa(usuario_empresa):
    """Devuelve todas las ofertas de una empresa ordenadas por fecha."""
    return Oferta.objects.filter(empresa=usuario_empresa).order_by('-fecha_publicacion')


def obtener_oferta_por_id(id_oferta):
    """Busca una oferta por ID.

    Returns:
        Oferta si existe, None si no.
    """
    try:
        return Oferta.objects.get(id=id_oferta)
    except Oferta.DoesNotExist:
        return None
    

def eliminar_oferta_por_id(oferta_id):
    """Elimina una oferta por ID.

    Returns:
        True si se eliminó, False si no existía.
    """
    oferta = obtener_oferta_por_id(oferta_id)
    if oferta:
        oferta.delete()
        return True
    return False


def obtener_ofertas_activas(busqueda='', modalidad='', experiencia=''):
    """Busca ofertas activas con filtros opcionales.

    Args:
        busqueda (str): Filtro por título o nombre de puesto.
        modalidad (str): Filtro exacto por modalidad.
        experiencia (str): Filtro exacto por experiencia requerida.

    Returns:
        QuerySet de ofertas activas filtradas.
    """
    ofertas = Oferta.objects.filter(estado='activa').select_related('empresa__oferente', 'categoria').order_by('-fecha_publicacion')
    if busqueda:
        ofertas = ofertas.filter(titulo__icontains=busqueda) | ofertas.filter(nombre_puesto__icontains=busqueda)
    if modalidad:
        ofertas = ofertas.filter(modalidad=modalidad)
    if experiencia:
        ofertas = ofertas.filter(experiencia_requerida=experiencia)
    return ofertas


def actualizar_estado_oferta(oferta_id, nuevo_estado):
    """Cambia el estado de una oferta.

    Returns:
        True si se actualizó, False si no existía.
    """
    oferta = obtener_oferta_por_id(oferta_id)
    if oferta:
        oferta.estado = nuevo_estado
        oferta.save()
        return True
    return False




def listar_tipos_oferta():
    return TipoOferta.objects.all()
#
def crear_tipo_oferta(form):
    return form.save()
#
def modificar_tipo_oferta(tipo_id, form):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    return form.save()
#
def eliminar_tipo_oferta(tipo_id):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    nombre = tipo.nombre
    tipo.delete()
    return nombre


def puede_eliminar_tipo_oferta(tipo_id):
    return not Oferta.objects.filter(tipo_oferta_id=tipo_id).exists()
#
def listar_habilidades_por_tipo(tipo_id):
    return Habilidad.objects.filter(tipo_oferta_id=tipo_id)
#
def crear_habilidad(form):
    return form.save()
#
def modificar_habilidad(habilidad_id, form):
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    return form.save()
#
def eliminar_habilidad(habilidad_id):
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    nombre = habilidad.nombre
    habilidad.delete()
    return nombre
#
def puede_eliminar_habilidad(habilidad_id):
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    if Oferta.objects.filter(habilidades_requeridas__icontains=habilidad.nombre).exists():
        return False
    return True