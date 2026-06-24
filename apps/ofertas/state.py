from abc import ABC, abstractmethod

class EstadoOferta(ABC):
    @abstractmethod
    def aprobar(self, oferta): ...
    @abstractmethod
    def rechazar(self, oferta): ...
    @abstractmethod
    def finalizar(self, oferta): ...
    @abstractmethod
    def puede_editarse(self): ...

class Pendiente(EstadoOferta):
    def aprobar(self, oferta):
        oferta.estado = 'activa'; oferta.save()
    def rechazar(self, oferta):
        oferta.estado = 'rechazada'; oferta.save()
    def finalizar(self, oferta):
        raise ValueError("No se puede finalizar una oferta pendiente")
    def puede_editarse(self): return True

class Activa(EstadoOferta):
    def aprobar(self, oferta):
        raise ValueError("Ya está activa")
    def rechazar(self, oferta):
        raise ValueError("No se puede rechazar una oferta activa")
    def finalizar(self, oferta):
        oferta.estado = 'finalizada'; oferta.save()
    def puede_editarse(self): return False

class Finalizada(EstadoOferta):
    def aprobar(self, oferta):
        raise ValueError("Ya está finalizada")
    def rechazar(self, oferta):
        raise ValueError("Ya está finalizada")
    def finalizar(self, oferta):
        raise ValueError("Ya está finalizada")
    def puede_editarse(self): return False

class Rechazada(EstadoOferta):
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