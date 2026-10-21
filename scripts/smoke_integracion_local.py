"""Smoke HTTP de integración local con identidades y contenido sintéticos.

Requiere el servidor Django y los dispatchers de IA/matching ya iniciados.
Usa Groq mediante esos flujos reales; exige --real-ia para evitar consumo
accidental. Nunca imprime credenciales ni contenido del CV.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import timedelta
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ientrabajo.settings.base")

import django  # noqa: E402

django.setup()

from django.test import override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.contrib.sessions.models import Session  # noqa: E402

from categorias.models import Categoria  # noqa: E402
from ia.models import (  # noqa: E402
    AnalisisCV,
    CVVersion,
    EventoRecepcion,
    EventoSalida,
    PerfilCV,
    PerfilOferta,
    TrabajoExtraccion,
)
from ia.workflow import request_offer_extraction  # noqa: E402
from matching.models import ResultadoCompatibilidad  # noqa: E402
from ofertas.models import Oferta  # noqa: E402
from usuarios.models import Oferente, Postulante, Usuario  # noqa: E402


CV_TEXT = (
    "Curriculum sintetico para prueba de integracion.\n"
    "Desarrollador backend con experiencia en Python y Django.\n"
    "Trabajo con PostgreSQL, APIs REST, pruebas automatizadas y Git.\n"
    "Experiencia laboral sintetica: desarrollo de servicios web durante cuatro anos.\n"
    "Educacion: carrera universitaria relacionada con sistemas.\n"
)


class CsrfInputParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "csrfmiddlewaretoken":
            self.token = attrs.get("value")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def phase(name: str, status: str, **safe_details) -> None:
    details = " ".join(f"{key}={value}" for key, value in safe_details.items())
    print(f"[{name}] {status}" + (f" {details}" if details else ""), flush=True)


def csrf_token(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=20)
    response.raise_for_status()
    parser = CsrfInputParser()
    parser.feed(response.text)
    token = parser.token or session.cookies.get("csrftoken")
    require(bool(token), "No se obtuvo token CSRF desde el formulario HTTP.")
    return token


def poll_http(session, url, timeout_seconds, terminal_states, state_key):
    deadline = time.monotonic() + timeout_seconds
    last_state = "unknown"
    while time.monotonic() < deadline:
        response = session.get(url, timeout=20)
        require(response.status_code == 200, f"El endpoint de estado respondió HTTP {response.status_code}.")
        body = response.json()
        state = body.get(state_key, "unknown")
        if state != last_state:
            phase("poll", "estado", state=state)
            last_state = state
        if state in terminal_states:
            return body
        time.sleep(2)
    raise TimeoutError(f"Se agotó el tiempo esperando estado {state_key}; último estado: {last_state}.")


def poll_db(model, lookup, timeout_seconds, expected_state):
    deadline = time.monotonic() + timeout_seconds
    last_state = None
    while time.monotonic() < deadline:
        state = model.objects.filter(**lookup).values_list("estado", flat=True).first()
        if state != last_state:
            phase("poll-db", "estado", state=state or "missing")
            last_state = state
        if state == expected_state:
            return
        if state in {"error", "failed"}:
            raise RuntimeError(f"El flujo terminó en estado {state}.")
        time.sleep(2)
    raise TimeoutError(f"Se agotó el tiempo esperando el estado de base {expected_state}.")


def login(session, base_url, email, password):
    login_url = urljoin(base_url, "/usuarios/login/")
    token = csrf_token(session, login_url)
    response = session.post(
        login_url,
        data={"email": email, "password": password, "csrfmiddlewaretoken": token},
        headers={"Referer": login_url, "X-CSRFToken": token},
        allow_redirects=True,
        timeout=20,
    )
    require(response.status_code == 200 and session.cookies.get("sessionid"), "El login HTTP no creó una sesión.")
    profile_url = urljoin(base_url, "/usuarios/mi-perfil/")
    token = csrf_token(session, profile_url)
    return token


def run(args):
    base_url = args.base_url.rstrip("/") + "/"
    require(urlparse(base_url).hostname in {"127.0.0.1", "localhost", "::1"}, "La prueba admite únicamente el servidor local.")
    run_id = uuid4().hex
    synthetic_email = f"smoke-{run_id}@example.invalid"
    other_email = f"smoke-other-{run_id}@example.invalid"
    company_email = f"smoke-company-{run_id}@example.invalid"
    password = secrets.token_urlsafe(24)
    made = {"users": [], "categories": [], "offers": [], "cv_versions": [], "analyses": [],
            "extraction_jobs": [], "outbox_events": [], "matches": [], "files": []}
    sessions = []
    output = {"run_id": run_id, "base_url": base_url, "phases": {}, "cleanup": {}}
    ok = False

    try:
        require(args.real_ia, "Este flujo consume IA real; volvé a ejecutarlo con --real-ia.")
        require(args.analysis_timeout > 0 and args.match_timeout > 0, "Los timeouts deben ser positivos.")
        require(args.offer_timeout > 0, "El timeout de extracción de oferta debe ser positivo.")

        candidate_user = Usuario.objects.create_user(
            email=synthetic_email, password=password, first_name="Prueba integración", last_name=run_id[:8]
        )
        made["users"].append(candidate_user.pk)
        candidate = Postulante.objects.create(usuario=candidate_user)
        other_user = Usuario.objects.create_user(email=other_email, password=secrets.token_urlsafe(24))
        made["users"].append(other_user.pk)
        Postulante.objects.create(usuario=other_user)
        company_user = Usuario.objects.create_user(email=company_email, password=secrets.token_urlsafe(24))
        made["users"].append(company_user.pk)
        cuit_base = '30' + f'{secrets.randbelow(100_000_000):08d}'
        cuit_digit = 11 - sum(int(n) * w for n, w in zip(cuit_base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
        cuit_digit = 0 if cuit_digit == 11 else 9 if cuit_digit == 10 else cuit_digit
        Oferente.objects.create(
            usuario=company_user, nombre_empresa=f"Prueba integración {run_id[:8]}", cuit=cuit_base + str(cuit_digit),
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
        )
        category = Categoria.objects.create(nombre=f"Smoke integración {run_id}")
        made["categories"].append(category.pk)
        phase("fixtures", "creados", synthetic=True)

        applicant_session = requests.Session()
        other_session = requests.Session()
        sessions.extend([applicant_session, other_session])
        candidate_csrf = login(applicant_session, base_url, synthetic_email, password)
        phase("login-postulante", "ok")

        upload_url = urljoin(base_url, "/usuarios/mi-perfil/")
        upload = applicant_session.post(
            upload_url,
            data={"csrfmiddlewaretoken": candidate_csrf},
            files={"cv": (f"smoke-{run_id}.txt", BytesIO(CV_TEXT.encode("utf-8")), "text/plain")},
            headers={"Referer": upload_url, "X-CSRFToken": candidate_csrf, "X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        )
        require(upload.status_code == 200, f"La carga HTTP del CV respondió {upload.status_code}.")
        upload_body = upload.json()
        require(upload_body.get("success") is True, "La vista no aceptó el CV sintético.")
        cv_version_id = int(upload_body["version_cv_id"])
        made["cv_versions"].append(cv_version_id)
        cv_version = CVVersion.objects.get(pk=cv_version_id, postulante=candidate)
        made["files"].append((cv_version.archivo.storage, cv_version.archivo.name))
        require(not AnalisisCV.objects.filter(postulante=candidate).exists(), "La carga inició un análisis sin solicitarlo.")
        phase("carga-cv", "ok", version=cv_version_id)

        own_download = applicant_session.get(urljoin(base_url, f"/usuarios/cv/{cv_version_id}/descargar/"), timeout=20)
        require(own_download.status_code == 200, "El propietario no pudo descargar su CV privado.")
        require(own_download.content == CV_TEXT.encode('utf-8'), "La descarga no conserva el contenido del CV cargado.")
        own_download.close()
        # Se autentica la segunda cuenta con su propia contraseña efímera creada para esta ejecución.
        # La contraseña queda solo en memoria y nunca se incluye en el resultado.
        # Setearla al crear el usuario es necesario para validar el control de propiedad por HTTP.
        # Se reemplaza con una credencial temporal inmediatamente antes del login.
        temp_password = secrets.token_urlsafe(24)
        other = Usuario.objects.get(email=other_email)
        other.set_password(temp_password)
        other.save(update_fields=["password"])
        login(other_session, base_url, other_email, temp_password)
        other_download = other_session.get(urljoin(base_url, f"/usuarios/cv/{cv_version_id}/descargar/"), allow_redirects=False, timeout=20)
        require(other_download.status_code == 404, "Otra cuenta pudo leer el CV privado (se esperaba 404).")
        anonymous = requests.Session()
        sessions.append(anonymous)
        anonymous_response = anonymous.get(urljoin(base_url, f"/usuarios/cv/{cv_version_id}/descargar/"), allow_redirects=False, timeout=20)
        require(anonymous_response.status_code == 302, "La descarga anónima no redirigió al login.")
        direct_path = Path(cv_version.archivo.name).name
        direct = anonymous.get(urljoin(base_url, f"/media/postulantes/cv/{direct_path}"), allow_redirects=False, timeout=20)
        require(direct.status_code == 404, "La ruta directa de media privada no respondió 404.")
        phase("privacidad-cv", "ok", owner=200, other=404, anonymous=302, direct=404)

        csrf = csrf_token(applicant_session, upload_url)
        submit_url = urljoin(base_url, "/ia/solicitar-analisis/")
        analysis_response = applicant_session.post(
            submit_url, data={"csrfmiddlewaretoken": csrf},
            headers={"Referer": upload_url, "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        )
        require(analysis_response.status_code == 202, f"La solicitud de análisis respondió {analysis_response.status_code}.")
        analysis_id = int(analysis_response.json()["analisis_id"])
        made["analyses"].append(analysis_id)
        analysis = AnalisisCV.objects.get(pk=analysis_id, postulante=candidate)
        extraction = TrabajoExtraccion.objects.get(analisis_cv=analysis)
        made["extraction_jobs"].append(extraction.pk)
        event = EventoSalida.objects.filter(payload__job_id=extraction.pk).first()
        if event:
            made["outbox_events"].append(event.pk)
        if extraction.cv_snapshot:
            made["files"].append((extraction.cv_snapshot.storage, extraction.cv_snapshot.name))
        phase("solicitud-analisis", "aceptada", analysis=analysis_id)

        analysis_body = poll_http(
            applicant_session,
            urljoin(base_url, f"/ia/analisis/{analysis_id}/estado/"),
            args.analysis_timeout,
            {"completado", "error"},
            "estado",
        )
        require(analysis_body["estado"] == "completado", "El análisis real del CV terminó con error.")
        poll_db(PerfilCV, {"postulante_id": candidate.pk}, args.analysis_timeout, "ready")
        profile_cv = PerfilCV.objects.get(postulante=candidate)
        require(profile_cv.schema_version == "candidate-profile.v2", "El perfil del CV no usa candidate-profile.v2.")
        phase("analisis-cv", "completado", profile_version=profile_cv.version)

        requirements = [{"id": "req-python", "category": "technical_skills", "source": "requisitos_obligatorios",
                         "name": "Python", "mandatory": True, "exclusionary": False}]
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            offer = Oferta.objects.create(
                empresa=company_user, categoria=category, titulo="Desarrollador backend sintético",
                nombre_puesto="Desarrollador Python", ubicacion="Remoto", modalidad="remoto",
                descripcion="Oferta sintética para validar extracción y matching local.",
                habilidades_duras="Python, Django, PostgreSQL", habilidades_requeridas="Python",
                requisitos_obligatorios="Python", requisitos_estructurados=requirements,
                requiere_revision_requisitos=False, nivel_educativo="universitario",
                fecha_cierre=timezone.now() + timedelta(days=7), estado="activa",
            )
            made["offers"].append(offer.pk)
            job, _ = request_offer_extraction(offer)
            made["extraction_jobs"].append(job.pk)
            event = EventoSalida.objects.filter(payload__job_id=job.pk).first()
            if event:
                made["outbox_events"].append(event.pk)
        phase("solicitud-oferta", "aceptada", offer=offer.pk)
        poll_db(TrabajoExtraccion, {"pk": job.pk}, args.offer_timeout, "completed")
        poll_db(PerfilOferta, {"oferta_id": offer.pk}, args.offer_timeout, "ready")
        profile_offer = PerfilOferta.objects.get(oferta=offer)
        require(profile_offer.schema_version == "job-offer.v2", "El perfil de oferta no usa job-offer.v2.")
        phase("analisis-oferta", "completado", profile_version=profile_offer.version)

        csrf = csrf_token(applicant_session, upload_url)
        match_url = urljoin(base_url, f"/matching/ofertas/{offer.pk}/calcular/")
        match_response = applicant_session.post(
            match_url, data={"csrfmiddlewaretoken": csrf},
            headers={"Referer": upload_url, "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        )
        require(match_response.status_code in {200, 202}, f"El cálculo de matching respondió {match_response.status_code}.")
        match_body = match_response.json()
        request_id = match_body["request_id"]
        match_row = ResultadoCompatibilidad.objects.get(request_id=request_id, postulante=candidate, oferta=offer)
        made["matches"].append(match_row.pk)
        match_event = EventoSalida.objects.filter(payload__match_id=match_row.pk).first()
        if match_event:
            made["outbox_events"].append(match_event.pk)
        phase("solicitud-matching", "aceptada", request_id=request_id)
        final_match = poll_http(
            applicant_session, urljoin(base_url, f"/matching/estado/{request_id}/"),
            args.match_timeout, {"completed", "error", "failed"}, "status",
        )
        require(final_match["status"] == "completed", "El matching real terminó con error.")
        require(final_match['result']['schema_version'] == 'match-result.v2', 'El resultado no usa match-result.v2.')
        require(0 <= final_match['match_percentage'] <= 100, 'Porcentaje fuera de rango.')
        duplicate = applicant_session.post(
            match_url, data={'csrfmiddlewaretoken': csrf},
            headers={'Referer': upload_url, 'X-CSRFToken': csrf}, timeout=20,
        )
        require(duplicate.status_code == 200 and duplicate.json()['request_id'] == request_id, 'La consulta repetida no reutiliza el resultado.')
        denied = other_session.get(urljoin(base_url, f'/matching/estado/{request_id}/'), timeout=20)
        require(denied.status_code == 404, 'Otra cuenta pudo consultar el match privado.')
        phase('matching', 'completado', percentage=final_match['match_percentage'])
        # A replacement CV must invalidate the current profile without silently consuming IA.
        new_cv = CV_TEXT + 'Actualizacion sintetica: disponibilidad remota.\n'
        replaced = applicant_session.post(
            upload_url, data={'csrfmiddlewaretoken': csrf},
            files={'cv': (f'smoke-replacement-{run_id}.txt', new_cv.encode('utf-8'), 'text/plain')},
            headers={'Referer': upload_url, 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest'}, timeout=30,
        )
        require(replaced.status_code == 200 and replaced.json().get('success'), 'No se pudo reemplazar el CV.')
        new_version_id = replaced.json()['version_cv_id']
        require(new_version_id != cv_version_id, 'Reemplazar el CV no creó una versión nueva.')
        made['cv_versions'].append(new_version_id)
        new_version = CVVersion.objects.get(pk=new_version_id, postulante=candidate)
        made['files'].append((new_version.archivo.storage, new_version.archivo.name))
        old_status = applicant_session.get(urljoin(base_url, f'/ia/analisis/{analysis_id}/estado/'), timeout=20).json()
        require(old_status['es_version_actual'] is False, 'Un análisis anterior se presenta como actual.')
        stale = applicant_session.post(match_url, data={'csrfmiddlewaretoken': csrf}, headers={'Referer': upload_url, 'X-CSRFToken': csrf}, timeout=20)
        require(stale.status_code == 409, 'Se permitió calcular con el perfil de un CV anterior.')
        require(AnalisisCV.objects.filter(postulante=candidate).count() == 1, 'Reemplazar el CV inició un análisis automático.')
        phase('versionado-cv', 'ok', stale_match=409)
        output["phases"] = {
            "cv_upload": "ok", "private_cv_access": "ok", "cv_analysis": "completed",
            "offer_analysis": "completed", "matching": "completed",
            "match_idempotency": "ok", "match_privacy": "ok", "cv_replacement": "ok",
        }
        output["result"] = {
            "analysis_id": analysis_id,
            "offer_id": offer.pk,
            "match_request_id": request_id,
            "match_percentage": final_match.get("match_percentage"),
            "coverage_percentage": final_match.get("coverage_percentage"),
            "confidence_percentage": final_match.get("confidence_percentage"),
        }
        ok = True
    except Exception as exc:
        output["error"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
        phase("smoke", "fallo", error=type(exc).__name__)
        raise
    finally:
        remote_ids = TrabajoExtraccion.objects.filter(pk__in=made['extraction_jobs']).values_list('remote_job_id', flat=True)
        EventoRecepcion.objects.filter(event_id__in=[f'extraction-{job_id}' for job_id in remote_ids if job_id]).delete()
        session_keys = [s.cookies.get('sessionid') for s in sessions if s.cookies.get('sessionid')]
        if session_keys:
            Session.objects.filter(session_key__in=session_keys).delete()
        for session in sessions:
            try:
                session.close()
            except Exception:
                pass
        cleanup_errors = []
        for storage, name in reversed(made["files"]):
            try:
                if storage.exists(name):
                    storage.delete(name)
            except Exception as exc:
                cleanup_errors.append(f"file:{type(exc).__name__}")
        for model, field, ids in (
            (ResultadoCompatibilidad, "pk", made["matches"]),
            (EventoSalida, "pk", made["outbox_events"]),
            (TrabajoExtraccion, "pk", made["extraction_jobs"]),
            (AnalisisCV, "pk", made["analyses"]),
            (CVVersion, "pk", made["cv_versions"]),
            (Oferta, "pk", made["offers"]),
            (Usuario, "pk", made["users"]),
            (Categoria, "pk", made["categories"]),
        ):
            if ids:
                try:
                    model.objects.filter(**{f"{field}__in": ids}).delete()
                except Exception as exc:
                    cleanup_errors.append(f"{model.__name__}:{type(exc).__name__}:{ids}")
        output["cleanup"] = {"status": "ok" if not cleanup_errors else "incomplete",
                              "errors": cleanup_errors}
        if cleanup_errors:
            phase("cleanup", "incompleto", details=";".join(cleanup_errors))
        else:
            phase("cleanup", "ok")
        output["status"] = "completed" if ok else "failed"
        if args.output:
            path = Path(args.output).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            phase("resumen", "guardado", path=path)
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--real-ia", action="store_true", help="autoriza el consumo real de los flujos IA/Groq")
    parser.add_argument("--analysis-timeout", type=int, default=240)
    parser.add_argument("--offer-timeout", type=int, default=240)
    parser.add_argument("--match-timeout", type=int, default=240)
    parser.add_argument("--output", help="opcional: archivo JSON de resumen sin datos personales")
    args = parser.parse_args()
    try:
        run(args)
    except Exception:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
