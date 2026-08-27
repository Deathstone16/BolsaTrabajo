"""
Patrón State para ofertas laborales.

Define los estados posibles de una oferta (pendiente, activa,
rechazada, finalizada) y las transiciones válidas entre ellos.
"""

from abc import ABC, abstractmethod

class EstadoOferta(ABC):
    """Interfaz abstracta para estados de oferta laboral.

    Cada estado concreto implementa las transiciones válidas
    y lanza ValueError si la transición no es permitida.
    """
    @abstractmethod
    def aprobar(self, oferta): ...
    @abstractmethod
    def rechazar(self, oferta): ...
    @abstractmethod
    def finalizar(self, oferta): ...
    @abstractmethod
    def puede_editarse(self): ...

class Pendiente(EstadoOferta):
    """Estado de oferta pendiente de aprobación. Puede aprobarse o rechazarse."""
    def aprobar(self, oferta):
        oferta.estado = 'activa'; oferta.save()
    def rechazar(self, oferta):
        oferta.estado = 'rechazada'; oferta.save()
    def finalizar(self, oferta):
        raise ValueError("No se puede finalizar una oferta pendiente")
    def puede_editarse(self): return True

class Activa(EstadoOferta):
    """Estado de oferta activa. Solo puede finalizarse."""
    def aprobar(self, oferta):
        raise ValueError("Ya está activa")
    def rechazar(self, oferta):
        raise ValueError("No se puede rechazar una oferta activa")
    def finalizar(self, oferta):
        oferta.estado = 'finalizada'; oferta.save()
    def puede_editarse(self): return False

class Finalizada(EstadoOferta):
    """Estado de oferta finalizada. Estado terminal, sin transiciones."""
    def aprobar(self, oferta):
        raise ValueError("Ya está finalizada")
    def rechazar(self, oferta):
        raise ValueError("Ya está finalizada")
    def finalizar(self, oferta):
        raise ValueError("Ya está finalizada")
    def puede_editarse(self): return False

class Rechazada(EstadoOferta):
    """Estado de oferta rechazada. Estado terminal, sin transiciones."""
    def aprobar(self, oferta):
        raise ValueError("No se puede aprobar una oferta rechazada")
    def rechazar(self, oferta):
        raise ValueError("Ya está rechazada")
    def finalizar(self, oferta):
        raise ValueError("Ya está finalizada")
    def puede_editarse(self): return False

ESTADOS = {
    'pendiente': Pendiente(),
    'activa': Activa(),
    'finalizada': Finalizada(),
    'rechazada': Rechazada(),
}