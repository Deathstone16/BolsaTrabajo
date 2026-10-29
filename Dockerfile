FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_DOTENV_DISABLED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=ientrabajo.settings.render \
    PORT=10000

WORKDIR /app
COPY requirements.txt requirements-deploy.txt ./
RUN python -m pip install --no-cache-dir -r requirements-deploy.txt \
    && useradd --create-home --uid 10001 app

COPY --chown=app:app apps ./apps
COPY --chown=app:app ientrabajo ./ientrabajo
COPY --chown=app:app ien_contracts ./ien_contracts
COPY --chown=app:app templates ./templates
COPY --chown=app:app static ./static
COPY --chown=app:app manage.py ./manage.py
COPY --chown=app:app deploy/start.py ./deploy/start.py
RUN DJANGO_SETTINGS_MODULE=ientrabajo.settings.build python manage.py collectstatic --noinput \
    && chown -R app:app /app

USER app
EXPOSE 10000
CMD ["python", "deploy/start.py"]
