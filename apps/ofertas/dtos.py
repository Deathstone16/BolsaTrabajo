from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class OfertaDTO:
    """Data Transfer Object para serializar Oferta a JSON."""
    titulo: str
    nombre_puesto: str
    categoria: Optional[int]
    ubicacion: str
    modalidad: str
    descripcion: str
    habilidades_requeridas: str
    experiencia_requerida: int
    nivel_educativo: str
    es_confidencial: bool
    fecha_cierre: str

    @classmethod
    def desde_modelo(cls, oferta):
        """Convierte una instancia de Oferta a OfertaDTO."""
        return cls(
            titulo=oferta.titulo,
            nombre_puesto=oferta.nombre_puesto,
            categoria=oferta.categoria_id,
            ubicacion=oferta.ubicacion,
            modalidad=oferta.modalidad,
            descripcion=oferta.descripcion,
            habilidades_requeridas=oferta.habilidades_requeridas,
            experiencia_requerida=oferta.experiencia_requerida,
            nivel_educativo=oferta.nivel_educativo,
            es_confidencial=oferta.es_confidencial,
            fecha_cierre=oferta.fecha_cierre.strftime('%Y-%m-%d') if oferta.fecha_cierre else '',
        )