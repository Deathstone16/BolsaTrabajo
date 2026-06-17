from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout


def autenticar_usuario(request, email, password):
    user = authenticate(request, email=email, password=password)
    if user is not None:
        auth_login(request, user)
        return True
    return False


def actualizar_datos_postulante(user, form):
    postulante = form.save(commit=False)
    user.first_name = form.cleaned_data['first_name']
    user.last_name = form.cleaned_data['last_name']
    user.email = form.cleaned_data['email']
    user.save()
    postulante.save()


def es_oferente(user):
    return hasattr(user, 'oferente')


def es_postulante(user):
    return hasattr(user, 'postulante')
