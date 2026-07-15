from abc import ABC, abstractmethod

class EstadoValidacion(ABC):
    @abstractmethod
    def badge_css(self): ...
    @abstractmethod
    def badge_icon(self): ...
    @abstractmethod
    def badge_text(self): ...
    @abstractmethod
    def puede_publicar(self): ...

class Pendiente(EstadoValidacion):
    def badge_css(self): return "bg-yellow-50 border-yellow-200 text-yellow-800"
    def badge_icon(self): return "clock"
    def badge_text(self): return "Pendiente de Validación"
    def puede_publicar(self): return False

class Aprobado(EstadoValidacion):
    def badge_css(self): return "bg-green-50 border-green-200 text-green-800"
    def badge_icon(self): return "check-circle"
    def badge_text(self): return "Empresa Validada"
    def puede_publicar(self): return True

class Rechazado(EstadoValidacion):
    def badge_css(self): return "bg-red-50 border-red-200 text-red-800"
    def badge_icon(self): return "alert-circle"
    def badge_text(self): return "Perfil Rechazado"
    def puede_publicar(self): return False

ESTADOS = {
    'pendiente': Pendiente(),
    'aprobado': Aprobado(),
    'rechazado': Rechazado(),
}