from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

def oferente_validado_required(view_func):
    @wraps(view_func)
    @oferente_required
    def wrapper(request, *args, **kwargs):
        if request.user.oferente.estado_validacion != 'aprobado':
            return redirect('validacion_pendiente')
        return view_func(request, *args, **kwargs)
    return wrapper

def oferente_required(view_func):
    """
    Decorator: solo permite acceso a usuarios con perfil de Oferente.
    Si no está logueado → redirect a login.
    Si está logueado pero no es oferente → redirect a home.
    """
    @wraps(view_func) 
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            
            return redirect('login')
        
        if not hasattr(request.user, 'oferente'):
            
            return redirect('home')
        return view_func(request, *args, **kwargs)
    
    return _wrapped


def postulante_required(view_func):
    """
    Decorator: solo permite acceso a usuarios con perfil de Postulante.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not hasattr(request.user, 'postulante'):
            return redirect('home')
        
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
            return redirect('login')
        
        if not hasattr(request.user, 'oferente') and not hasattr(request.user, 'postulante'):
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped
