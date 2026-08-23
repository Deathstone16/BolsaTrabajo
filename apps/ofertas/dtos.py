"""
Data Transfer Object para serialización de Ofertas a JSON.

Define ``OfertaDTO`` como dataclass para exponer datos de una oferta
a endpoints JSON sin exponer el modelo directamente.
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class OfertaDTO:
    """Data Transfer Object para serializar una Oferta a JSON.

    Se usa en el endpoint de detalle de oferta para exponeer
    datos formateados al frontend sin exponer el modelo directamente.
    """
    """Data Transfer Object para serializar Oferta a JSON."""

    id: int
    titulo: str
    nombre_puesto: str
    categoria: Optional[int]
    tipo_oferta: Optional[int]
    tipo_oferta_nombre: str
    ubicacion: str
    modalidad: str
    modalidad_display: str
    descripcion: str
    habilidades_requeridas: str
    experiencia_requerida: int
    nivel_educativo: str
    nivel_educativo_display: str
    es_confidencial: bool
    estado: str
    estado_display: str
    fecha_cierre: str
    empresa_nombre: str
    empresa_perfil_url: str

    @classmethod
    def desde_modelo(cls, oferta):
        """Convierte una instancia de Oferta a OfertaDTO."""
        oferente = getattr(oferta.empresa, "oferente", None)
        return cls(
            id=oferta.id,
            titulo=oferta.titulo,
            nombre_puesto=oferta.nombre_puesto,
            categoria=oferta.categoria_id,
            ubicacion=oferta.ubicacion,
            modalidad=oferta.modalidad,
            modalidad_display=oferta.get_modalidad_display(),
            descripcion=oferta.descripcion,
            habilidades_requeridas=oferta.habilidades_requeridas,
            experiencia_requerida=oferta.experiencia_requerida,
            nivel_educativo=oferta.nivel_educativo,
            nivel_educativo_display=oferta.get_nivel_educativo_display(),
            es_confidencial=oferta.es_confidencial,
            estado=oferta.estado,
            estado_display=oferta.get_estado_display(),
            fecha_cierre=oferta.fecha_cierre.strftime("%Y-%m-%d")
            if oferta.fecha_cierre
            else "",
            empresa_nombre=oferente.nombre_empresa if oferente else "",
            empresa_perfil_url="#",
        )

