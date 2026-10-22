"""Create, inspect, and remove isolated synthetic data for browser E2E runs.

Usage: ``python scripts/e2e_fixture.py seed [--live-ai]`` followed by
``status`` and ``cleanup``. The state file contains login credentials and must
remain private; it is created with owner-only permissions where supported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ientrabajo.settings.base")

import django  # noqa: E402

django.setup()

from django.contrib.sessions.models import Session  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.db import transaction  # noqa: E402
from django.db.models import Q  # noqa: E402
from django.db.models.deletion import ProtectedError  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from categorias.models import Categoria  # noqa: E402
from categorias.models import Habilidad  # noqa: E402
from cursos.models import Curso  # noqa: E402
from ia.models import (  # noqa: E402
    AnalisisCV,
    CVVersion,
    EstadoPerfil,
    EventoRecepcion,
    EventoSalida,
    PerfilCV,
    PerfilOferta,
    TrabajoExtraccion,
)
from matching.configuration import scoring_hash  # noqa: E402
from matching.models import ConfiguracionActiva, ResultadoCompatibilidad  # noqa: E402
from ofertas.models import Oferta  # noqa: E402
from usuarios.models import Oferente, Postulante, Usuario  # noqa: E402


DEFAULT_STATE = ROOT / ".test-artifacts" / "e2e" / "state.json"
TERMINAL_JOBS = {
    TrabajoExtraccion.Estado.COMPLETADO,
    TrabajoExtraccion.Estado.ERROR,
}


def read_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("Fixture state file was not found.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("run_id"), str):
        raise RuntimeError("Fixture state file is invalid.")
    return data


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    fd, tmp_name = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chmod(tmp_name, 0o600)
        except OSError:
            pass
        os.replace(tmp_name, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def generated_cuit() -> str:
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    while True:
        first_ten = "30" + f"{secrets.randbelow(100_000_000):08d}"
        check = 11 - sum(int(digit) * weight for digit, weight in zip(first_ten, weights)) % 11
        if check != 10:
            return first_ten + str(0 if check == 11 else check)


def create_user(state: dict, role: str, password: str, path: Path) -> Usuario:
    email = f"e2e-{role}-{state['run_id']}@example.invalid"
    user = Usuario.objects.create_user(email=email, password=password, first_name="E2E", last_name=role)
    state["users"][role] = {"id": user.pk, "email": email}
    write_state(path, state)
    return user


def make_offer(
    company: Usuario,
    category: Categoria,
    run_id: str,
    *,
    active: bool,
    legacy: bool = False,
) -> Oferta:
    label = "legacy" if legacy else ("activa" if active else "pendiente")
    requirements = [{
        "id": "req-python",
        "category": "technical_skills",
        "source": "requisitos_obligatorios",
        "name": "Python",
        "mandatory": True,
        "exclusionary": False,
    }]
    return Oferta.objects.create(
        empresa=company,
        categoria=category,
        titulo=f"E2E {label} {run_id[:8]}",
        nombre_puesto="Desarrollador Python",
        ubicacion="Remoto",
        modalidad="remoto",
        descripcion="Oferta sintetica para pruebas automatizadas.",
        habilidades_duras="Python",
        habilidades_blandas="Comunicacion",
        habilidades_requeridas="Python",
        requisitos_obligatorios="Python",
        requisitos_deseables="Django",
        requisitos_estructurados=requirements,
        requiere_revision_requisitos=legacy,
        nivel_educativo="universitario",
        estado="activa" if active else "pendiente",
        fecha_cierre=timezone.now() + timedelta(days=7),
    )


def seed(path: Path, live_ai: bool) -> dict:
    if path.exists():
        raise RuntimeError("State file already exists; inspect or clean that run first.")
    run_id = uuid4().hex
    state = {
        "run_id": run_id,
        "password": secrets.token_urlsafe(24),
        "users": {},
        "category_id": None,
        "course_category_id": None,
        "pending_offer_id": None,
        "live_offer_id": None,
        "sessions": [],
    }
    write_state(path, state)
    try:
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            with transaction.atomic():
                candidate = create_user(state, "candidate", state["password"], path)
                other = create_user(state, "other", state["password"], path)
                company = create_user(state, "company", state["password"], path)
                other_company = create_user(state, "other_company", state["password"], path)
                Postulante.objects.create(usuario=candidate)
                Postulante.objects.create(usuario=other)
                Oferente.objects.create(
                    usuario=company, estado_validacion=Oferente.EstadoValidacion.APROBADO,
                    nombre_empresa=f"E2E Empresa {run_id[:8]}", cuit=generated_cuit(),
                )
                Oferente.objects.create(
                    usuario=other_company, estado_validacion=Oferente.EstadoValidacion.APROBADO,
                    nombre_empresa=f"E2E Empresa alternativa {run_id[:8]}", cuit=generated_cuit(),
                )
                category = Categoria.objects.create(nombre=f"E2E {run_id}")
                state["category_id"] = category.pk
                state["course_category_id"] = category.pk
                write_state(path, state)
                pending = make_offer(company, category, run_id, active=False)
                state["pending_offer_id"] = pending.pk
                write_state(path, state)
                legacy = make_offer(company, category, run_id, active=True, legacy=True)
                state["legacy_offer_id"] = legacy.pk
                write_state(path, state)
                PerfilOferta.objects.create(
                    oferta=legacy,
                    contenido={"schema_version": "job-offer.v1", "requirements": legacy.requisitos_estructurados},
                    schema_version="job-offer.v1",
                    estado=EstadoPerfil.LISTO,
                )
                ui_offer = make_offer(company, category, run_id, active=True)
                excel_topic = f"Excel sintético {run_id[:8]}"
                state["course_skill_name"] = excel_topic
                excel_requirement = {
                    "id": "req-excel", "category": "technical_skills",
                    "source": "requisitos_obligatorios", "name": excel_topic,
                    "mandatory": True, "exclusionary": False,
                }
                ui_offer.requisitos_estructurados = [excel_requirement]
                ui_offer.habilidades_duras = excel_topic
                ui_offer.habilidades_requeridas = excel_topic
                ui_offer.requisitos_obligatorios = excel_topic
                ui_offer.save(update_fields=[
                    "requisitos_estructurados", "habilidades_duras", "habilidades_requeridas", "requisitos_obligatorios",
                ])
                state["ui_completed_offer_id"] = ui_offer.pk
                write_state(path, state)
                state["ui_offer_title"] = ui_offer.titulo
                ui_offer_content = {
                    "schema_version": "job-offer.v2",
                    "requirements": ui_offer.requisitos_estructurados,
                }
                offer_hash = hashlib.sha256(
                    json.dumps(ui_offer_content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                PerfilOferta.objects.create(
                    oferta=ui_offer, contenido=ui_offer_content, version=1,
                    source_hash=offer_hash, schema_version="job-offer.v2", estado=EstadoPerfil.LISTO,
                )
                skill_category = Categoria.objects.create(nombre=f"E2E Habilidades {run_id}")
                state["course_skill_category_id"] = skill_category.pk
                write_state(path, state)
                excel_skill = Habilidad.objects.create(categoria=skill_category, nombre=excel_topic, tipo_habilidad="D")
                state["course_excel_skill_id"] = excel_skill.pk
                write_state(path, state)
                excel_course = Curso.objects.create(
                    nombre=f"{excel_topic} — práctica para el trabajo",
                    categoria=category, imagen="", descripcion="Curso sintético para practicar Excel.",
                    duracion="8 horas", horario="A coordinar", tipo=Curso.VIRTUAL, activo=True,
                )
                state["course_excel_id"] = excel_course.pk
                state["course_excel_name"] = excel_course.nombre
                write_state(path, state)
                admin_course = Curso.objects.create(
                    nombre=f"Administración general E2E {run_id[:8]}",
                    categoria=category, imagen="", descripcion="Curso sintético de administración general.",
                    duracion="12 horas", horario="A coordinar", tipo=Curso.VIRTUAL, activo=True,
                )
                admin_course.habilidades.add(excel_skill)
                state["course_admin_id"] = admin_course.pk
                state["course_admin_name"] = admin_course.nombre
                write_state(path, state)
                inactive_course = Curso.objects.create(
                    nombre=f"Curso inactivo E2E {run_id[:8]}",
                    categoria=category, imagen="", descripcion="Curso sintético inactivo.",
                    duracion="4 horas", horario="A coordinar", tipo=Curso.VIRTUAL, activo=False,
                )
                state["course_inactive_id"] = inactive_course.pk
                state["course_inactive_name"] = inactive_course.nombre
                write_state(path, state)
                ui_postulante = Postulante.objects.get(usuario=other)
                ui_cv_bytes = b"CV sintetico E2E, sin datos personales."
                ui_cv_hash = hashlib.sha256(ui_cv_bytes).hexdigest()
                ui_cv = CVVersion.objects.create(
                    postulante=ui_postulante, numero=1, nombre_original="cv-e2e-ui.txt",
                    sha256=ui_cv_hash, formato="txt", tamano=len(ui_cv_bytes),
                )
                ui_cv.archivo.save(f"e2e-{run_id}-ui-candidate.txt", ContentFile(ui_cv_bytes), save=True)
                ui_postulante.cv_version_actual = ui_cv
                ui_postulante.save(update_fields=["cv_version_actual"])
                ui_profile_content = {
                    "schema_version": "candidate-profile.v2", "skills": [],
                    "technical_skills": [], "soft_skills": [], "experience": [],
                    "education": [], "languages": [],
                }
                ui_profile_hash = hashlib.sha256(
                    json.dumps(ui_profile_content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                ui_profile = PerfilCV.objects.create(
                    postulante=ui_postulante, cv_version=ui_cv, contenido=ui_profile_content,
                    version=1, source_hash=ui_profile_hash, schema_version="candidate-profile.v2",
                    estado=EstadoPerfil.LISTO, origen="e2e",
                )
                active_config = ConfiguracionActiva.objects.select_related("configuracion").filter(
                    singleton="actual", configuracion__es_borrador=False,
                ).first()
                config = active_config.configuracion if active_config else None
                result = ResultadoCompatibilidad.objects.create(
                    postulante=ui_postulante, oferta=ui_offer,
                    cache_key=uuid4().hex,
                    estado=ResultadoCompatibilidad.Estado.COMPLETADO,
                    perfil_cv_version=ui_profile.version,
                    perfil_oferta_version=1,
                    perfil_cv_hash=ui_profile.source_hash,
                    perfil_oferta_hash=offer_hash,
                    provider_model_config=settings.MATCH_MODEL_VERSION,
                    configuracion=config,
                    scoring_config_hash=scoring_hash(config) if config else "",
                    scoring_weights=config.pesos_basis_points() if config else {},
                    evaluation_date=timezone.localdate(),
                    resultado={
                        "schema_version": "match-result.v2", "breakdown": {},
                        "assessments": [{
                            "requirement_id": "req-excel", "category": "technical_skills",
                            "source": "requisitos_obligatorios", "name": excel_topic, "score": 0,
                            "status": "not_met", "mandatory": True,
                            "explanation": "El perfil sintético no incluye evidencia de Excel.",
                            "evidence_refs": [],
                        }],
                        "mandatory_status": "not_met", "summary": "Brecha sintética de Excel.",
                    },
                    match_percentage=0, coverage_percentage=0,
                )
                state["ui_match_request_id"] = str(result.request_id)
                write_state(path, state)
                if live_ai:
                    active = make_offer(company, category, run_id, active=True)
                    state["live_offer_id"] = active.pk
                    write_state(path, state)
                    from ia.workflow import request_offer_extraction

                    request_offer_extraction(active)
        return state
    except Exception:
        state["seed_status"] = "failed"
        write_state(path, state)
        raise


def validate_users(state: dict) -> dict[str, Usuario]:
    users = {}
    run_id = state["run_id"]
    for role, ref in (state.get("users") or {}).items():
        if role not in {"candidate", "other", "company", "other_company"}:
            raise RuntimeError("Fixture state contains an unknown user role.")
        email = f"e2e-{role}-{run_id}@example.invalid"
        if not isinstance(ref, dict) or ref.get("email") != email:
            raise RuntimeError("Fixture identity check failed.")
        user = Usuario.objects.filter(pk=ref.get("id"), email=email).first()
        if user:
            users[role] = user
    return users


def validate_offer(state: dict, key: str, users: dict[str, Usuario]) -> Oferta | None:
    offer_id = state.get(key)
    if offer_id is None:
        return None
    company_id = users.get("company").pk if users.get("company") else None
    offer = Oferta.objects.filter(pk=offer_id, empresa_id=company_id).first()
    if not offer:
        raise RuntimeError("Fixture offer ownership check failed.")
    return offer


def validate_course_fixture(state: dict) -> tuple[dict[str, Curso], Habilidad | None, Categoria | None]:
    run_id = state["run_id"]
    category = None
    category_id = state.get("course_category_id")
    if category_id is not None:
        category = Categoria.objects.filter(pk=category_id, nombre=f"E2E {run_id}").first()
        if category is None:
            raise RuntimeError("Fixture course category ownership check failed.")
    skill_category = None
    skill_category_id = state.get("course_skill_category_id")
    if skill_category_id is not None:
        skill_category = Categoria.objects.filter(pk=skill_category_id, nombre=f"E2E Habilidades {run_id}").first()
        if skill_category is None:
            raise RuntimeError("Fixture skill category ownership check failed.")
    skill = None
    skill_id = state.get("course_excel_skill_id")
    if skill_id is not None:
        skill = Habilidad.objects.filter(pk=skill_id, categoria=skill_category, nombre=state.get("course_skill_name", "Excel")).first()
        if skill is None:
            raise RuntimeError("Fixture skill ownership check failed.")

    courses = {}
    for id_key, name_key, active in (
        ("course_excel_id", "course_excel_name", True),
        ("course_admin_id", "course_admin_name", True),
        ("course_inactive_id", "course_inactive_name", False),
    ):
        course_id = state.get(id_key)
        if course_id is None:
            continue
        course = Curso.objects.filter(
            pk=course_id, categoria=category, nombre=state.get(name_key), activo=active,
        ).first()
        if course is None:
            raise RuntimeError("Fixture course ownership check failed.")
        courses[id_key] = course
    admin = courses.get("course_admin_id")
    if admin is not None and skill is not None and not admin.habilidades.filter(pk=skill.pk).exists():
        raise RuntimeError("Fixture course skill ownership check failed.")
    return courses, skill, skill_category


def schema(content):
    return content.get("schema_version") if isinstance(content, dict) else None


def status(path: Path) -> dict:
    state = read_state(path)
    users = validate_users(state)
    candidate = users.get("candidate")
    post = Postulante.objects.filter(usuario=candidate).first() if candidate else None
    version = CVVersion.objects.filter(pk=post.cv_version_actual_id).first() if post and post.cv_version_actual_id else None
    analysis = AnalisisCV.objects.filter(postulante=post).order_by("-creado_en", "-pk").first() if post else None
    cv_profile = PerfilCV.objects.filter(postulante=post).first() if post else None
    pending = validate_offer(state, "pending_offer_id", users)
    live = validate_offer(state, "live_offer_id", users)
    offer_for_status = live or pending
    offer_profile = PerfilOferta.objects.filter(oferta=offer_for_status).first() if offer_for_status else None
    jobs = TrabajoExtraccion.objects.filter(oferta=live).order_by("-creado_en") if live else TrabajoExtraccion.objects.none()
    job = jobs.first()
    matches = ResultadoCompatibilidad.objects.filter(postulante=post).order_by("-creado_en") if post else ResultadoCompatibilidad.objects.none()
    last_match = matches.first()
    content = cv_profile.contenido if cv_profile and isinstance(cv_profile.contenido, dict) else {}
    skills = content.get("skills", [])
    soft_count = sum(1 for item in skills if isinstance(item, dict) and str(item.get("kind", "")).casefold() == "soft") if isinstance(skills, list) else 0
    return {
        "state_file": str(path.resolve()),
        "run_id": state["run_id"],
        "cv_version_id": version.pk if version else None,
        "analysis_id": analysis.pk if analysis else None,
        "analysis_state": analysis.estado if analysis else None,
        "new_analysis_count": AnalisisCV.objects.filter(postulante=post).count() if post else 0,
        "cv_profile_state": cv_profile.estado if cv_profile else None,
        "cv_profile_schema": cv_profile.schema_version if cv_profile else None,
        "offer_profile_state": offer_profile.estado if offer_profile else None,
        "offer_profile_schema": offer_profile.schema_version if offer_profile else None,
        "offer_job_state": job.estado if job else None,
        "match_count": matches.count(),
        "last_match_state": last_match.estado if last_match else None,
        "last_match_schema": schema(last_match.resultado) if last_match else None,
        "offer_title": pending.titulo if pending else None,
        "requirements": pending.requisitos_estructurados if pending else [],
        "soft_count": soft_count,
        "soft_names": [item['name'] for item in skills if item.get('kind') == 'soft'],
        "skill_names": [item['name'] for item in skills],
        "education": content.get('education', []),
        "profile_headline": content.get('headline'),
        "profile_summary": content.get('summary'),
    }


def _collect_file(field, files: set[tuple[object, str]]) -> None:
    if field and getattr(field, "name", None):
        files.add((field.storage, field.name))


def cleanup(path: Path) -> dict:
    state = read_state(path)
    if (state.get("cleanup") or {}).get("status") == "cleaned":
        return state["cleanup"]
    users = validate_users(state)
    pending = validate_offer(state, "pending_offer_id", users)
    live = validate_offer(state, "live_offer_id", users)
    owned_courses, owned_skill, owned_skill_category = validate_course_fixture(state)
    user_ids = [user.pk for user in users.values()]
    company_ids = [user.pk for role, user in users.items() if role in {"company", "other_company"}]
    offer_ids = list(Oferta.objects.filter(empresa_id__in=company_ids).values_list("pk", flat=True))
    fixture_offers = Oferta.objects.filter(pk__in=offer_ids)
    jobs = TrabajoExtraccion.objects.filter(
        Q(oferta_id__in=offer_ids)
        | Q(analisis_cv__postulante__usuario_id__in=user_ids)
        | Q(source_cv_version__postulante__usuario_id__in=user_ids)
    ).distinct()
    active = list(jobs.exclude(estado__in=TERMINAL_JOBS).values_list("estado", flat=True))
    match_qs = ResultadoCompatibilidad.objects.filter(
        Q(postulante__usuario_id__in=user_ids) | Q(oferta_id__in=offer_ids)
    )
    active_matches = match_qs.exclude(estado__in={
        ResultadoCompatibilidad.Estado.COMPLETADO,
        ResultadoCompatibilidad.Estado.ERROR,
    }).count()
    if active or active_matches:
        result = {
            "state_file": str(path.resolve()), "status": "waiting_for_jobs",
            "active_job_count": len(active), "active_match_count": active_matches,
        }
        state["cleanup"] = result
        write_state(path, state)
        return result

    files: set[tuple[object, str]] = set()
    for version in CVVersion.objects.filter(postulante__usuario_id__in=user_ids):
        _collect_file(version.archivo, files)
    for job in jobs:
        _collect_file(job.cv_snapshot, files)
    for field_name in ("cv", "foto"):
        for profile in Postulante.objects.filter(usuario_id__in=user_ids):
            _collect_file(getattr(profile, field_name), files)
    for company in Oferente.objects.filter(usuario_id__in=user_ids):
        _collect_file(company.logo, files)
        _collect_file(company.banner, files)

    job_ids = list(jobs.values_list("pk", flat=True))
    match_ids = list(match_qs.values_list("pk", flat=True))
    event_filter = Q(payload__job_id__in=job_ids) | Q(payload__match_id__in=match_ids)
    event_ids = list(EventoSalida.objects.filter(event_filter).values_list("pk", flat=True))
    remote_ids = [job.remote_job_id for job in jobs if job.remote_job_id]
    for remote_id in remote_ids:
        EventoRecepcion.objects.filter(event_id=f"extraction-{remote_id}").delete()

    counts = {
        "users": len(users), "offers": len(offer_ids), "courses": len(owned_courses),
        "skills": int(owned_skill is not None), "files": len(files), "outbox_events": len(event_ids),
    }
    try:
        with transaction.atomic():
            EventoSalida.objects.filter(pk__in=event_ids).delete()
            # Course.category and Habilidad.categoria use PROTECT; remove only
            # the run-owned courses and skill before their run-owned categories.
            Curso.objects.filter(pk__in=[course.pk for course in owned_courses.values()]).delete()
            if owned_skill is not None:
                owned_skill.delete()
            if owned_skill_category is not None:
                owned_skill_category.delete()
            # The two fixture users are verified by exact id and synthetic email above.
            Usuario.objects.filter(pk__in=user_ids).delete()
            category_id = state.get("category_id")
            if category_id is not None:
                category = Categoria.objects.filter(pk=category_id, nombre=f"E2E {state['run_id']}").first()
                if category:
                    try:
                        category.delete()
                    except ProtectedError:
                        counts["category_retained_references"] = 1
    except Exception:
        state["cleanup"] = {"status": "failed", "counts": counts}
        write_state(path, state)
        raise

    removed_files = 0
    failed_file_deletes = 0
    for storage, name in files:
        try:
            storage.delete(name)
            removed_files += 1
        except Exception:
            failed_file_deletes += 1
    session_keys = [key for key in state.get("sessions", []) if isinstance(key, str) and len(key) <= 64]
    session_count, _ = Session.objects.filter(session_key__in=session_keys).delete() if session_keys else (0, {})
    counts["files_removed"] = removed_files
    counts["file_delete_failures"] = failed_file_deletes
    counts["sessions"] = session_count
    result = {
        "state_file": str(path.resolve()),
        "status": "cleaned" if not failed_file_deletes else "incomplete",
        "counts": counts,
    }
    state["password"] = None
    state["cleanup"] = result
    write_state(path, state)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("seed", "status", "cleanup"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--state", type=Path, default=DEFAULT_STATE)
        if command == "seed":
            sub.add_argument("--live-ai", action="store_true", help="Queue one synthetic active-offer extraction.")
    args = parser.parse_args()
    try:
        if args.command == "seed":
            seed(args.state, args.live_ai)
            print(json.dumps({
                "state_file": str(args.state.resolve()),
                "status": "seeded",
                    "counts": {
                        "users": 4, "offers": 4 if args.live_ai else 3,
                        "courses": 3, "course_skills": 1, "live_ai": int(args.live_ai),
                    },
            }))
        elif args.command == "status":
            print(json.dumps(status(args.state), ensure_ascii=False))
        else:
            result = cleanup(args.state)
            print(json.dumps(result, ensure_ascii=False))
            if result.get("status") not in {"cleaned", "waiting_for_jobs"}:
                return 1
        return 0
    except Exception as exc:
        # Avoid echoing exception messages that could contain local paths or data.
        print(json.dumps({"state_file": str(args.state.resolve()), "status": "error", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
