from functools import wraps
from django.shortcuts import redirect


def postulante_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'postulante'):
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def oferente_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'oferente'):
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper
