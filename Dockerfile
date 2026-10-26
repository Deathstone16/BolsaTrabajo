FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=ientrabajo.settings.render

WORKDIR /app
COPY requirements.txt requirements-render.txt ./
RUN pip install -r requirements-render.txt \
    && useradd --create-home --uid 10001 app

COPY --chown=app:app . .
RUN mkdir -p staticfiles media private_uploads \
    && chown -R app:app /app

USER app
EXPOSE 10000
CMD ["sh", "deploy/render/start.sh"]
