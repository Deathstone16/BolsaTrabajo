import re
import unicodedata

from .models import AnalisisCV, ComparacionOfertaCV


def ultimo_analisis_completado(postulante):
    """Obtiene el perfil de CV más reciente que terminó correctamente."""
    analisis = (
        AnalisisCV.objects
        .filter(
            postulante=postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta__isnull=False,
        )
    )
    if postulante.cv_fecha_carga:
        analisis = analisis.filter(creado_en__gte=postulante.cv_fecha_carga)
    return analisis.first()


def _normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return ' '.join(re.findall(r'[a-z0-9+#.]+', texto.casefold()))


def _coinciden(habilidad_cv, requisito):
    habilidad = _normalizar(habilidad_cv)
    requerido = _normalizar(requisito)
    if not habilidad or not requerido:
        return False
    if habilidad == requerido:
        return True

    tokens_habilidad = set(habilidad.split())
    tokens_requerido = set(requerido.split())
    menor, mayor = sorted((tokens_habilidad, tokens_requerido), key=len)
    return bool(menor) and menor.issubset(mayor)


def _habilidades_del_analisis(analisis):
    respuesta = analisis.respuesta or {}
    resultado = respuesta.get('result') or {}
    habilidades = resultado.get('habilidades_analizadas') or []
    if not habilidades and resultado.get('skills'):
        return [item['name'] for item in resultado['skills'] if isinstance(item, dict) and item.get('name')]
    return [
        item.get('tecnologia', '').strip()
        for item in habilidades
        if isinstance(item, dict) and item.get('tecnologia', '').strip()
    ]


def comparar_oferta_con_analisis(oferta, analisis):
    """Compara requisitos de la oferta con habilidades ya extraídas del CV."""
    requeridas = [
        habilidad.strip()
        for habilidad in (oferta.habilidades_requeridas or '').split(',')
        if habilidad.strip()
    ]
    habilidades_cv = _habilidades_del_analisis(analisis)

    coincidencias = []
    faltantes = []
    for requisito in requeridas:
        encontrada = next(
            (habilidad for habilidad in habilidades_cv if _coinciden(habilidad, requisito)),
            None,
        )
        if encontrada:
            coincidencias.append({'requisito': requisito, 'habilidad_cv': encontrada})
        else:
            faltantes.append(requisito)

    porcentaje = round(len(coincidencias) * 100 / len(requeridas)) if requeridas else 0
    return {
        'porcentaje': porcentaje,
        'coincidencias': coincidencias,
        'habilidades_faltantes': faltantes,
        'habilidades_cv': habilidades_cv,
        'total_requisitos': len(requeridas),
        'oferta_habilidades_requeridas': oferta.habilidades_requeridas or '',
    }


def guardar_comparacion(postulante, oferta, analisis):
    resultado = comparar_oferta_con_analisis(oferta, analisis)
    comparacion, _ = ComparacionOfertaCV.objects.update_or_create(
        postulante=postulante,
        oferta=oferta,
        analisis=analisis,
        defaults={
            'porcentaje': resultado['porcentaje'],
            'resultado': resultado,
        },
    )
    return comparacion
