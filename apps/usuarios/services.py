from django.contrib.auth import authenticate, login as auth_login


def autenticar_usuario(request, email, password):
    user = authenticate(request, email=email, password=password)
    if user is not None:
        auth_login(request, user)
        return True
    return False


def registrar_usuario(form):
    return form.save()


def actualizar_datos_postulante(user, form):
    postulante = form.save(commit=False)
    user.first_name = form.cleaned_data['first_name']
    user.last_name = form.cleaned_data['last_name']
    user.email = form.cleaned_data['email']
    user.save()
    postulante.save()


def actualizar_perfil_oferente(form):
    form.save()
