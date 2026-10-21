import re

from django.core.exceptions import ValidationError


def normalizar_cuit(valor):
    """Devuelve el CUIT con el formato XX-XXXXXXXX-X."""
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) != 11:
        return valor
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"


def validar_cuit(valor):
    """Valida longitud y dígito verificador de un CUIT argentino."""
    texto = (valor or "").strip()
    if not re.fullmatch(r"(?:\d{11}|\d{2}-\d{8}-\d)", texto):
        raise ValidationError("El CUIT debe tener 11 números. Podés escribirlo con o sin guiones.")

    digitos = re.sub(r"\D", "", texto)
    if len(digitos) != 11:
        raise ValidationError("El CUIT debe tener 11 números. Revisá que esté completo.")

    if digitos[:2] not in {'20', '23', '24', '27', '30', '33', '34'}:
        raise ValidationError("Revisá los primeros dos números del CUIT. Deben coincidir con tu constancia de inscripción.")

    multiplicadores = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    suma = sum(int(digito) * factor for digito, factor in zip(digitos[:10], multiplicadores))
    verificador = 11 - (suma % 11)
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        raise ValidationError("Revisá el CUIT ingresado, incluido el último número. Debe coincidir con tu constancia de inscripción.")

    if verificador != int(digitos[-1]):
        raise ValidationError("Revisá el CUIT ingresado, incluido el último número. Debe coincidir con tu constancia de inscripción.")
