"""
Decoradores de autorización por perfil de usuario.

Cada decorator verifica si el usuario autenticado tiene el perfil
requerido (Oferente, Postulante o ambos) y redirige a login/home
en caso contrario.
"""

from functools import wraps

from django.shortcuts import redirect


def oferente_required(view_func):
    """
    Decorator: solo permite acceso a usuarios con perfil de Oferente.
    Si no está logueado → redirect a login.
    Si está logueado pero no es oferente → redirect a home.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not hasattr(request.user, "oferente"):
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped


def postulante_required(view_func):
    """
    Decorator: solo permite acceso a usuarios con perfil de Postulante.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not hasattr(request.user, "postulante"):
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped


def oferente_o_postulante_required(view_func):
    """
    Decorator: permite acceso a oferentes Y postulantes.
    Cualquier usuario autenticado que tenga uno de los dos perfiles.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not hasattr(request.user, "oferente") and not hasattr(
            request.user, "postulante"
        ):
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped


def oferente_validado_required(view_func):
    """
    Decorator: solo oferentes cuya empresa fue aprobada por moderación.
    Suma el chequeo de estado_validacion sobre oferente_required.
    """

    @oferente_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.oferente.estado_obj.puede_publicar():
            return redirect("validacion_pendiente")
        return view_func(request, *args, **kwargs)

    return _wrapped
