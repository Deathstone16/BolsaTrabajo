FROM python:3.12-slim-bookworm AS source
ARG IA_API_COMMIT=50794f0d4e732f0b57ed9a557d4776bd22558536
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && git init /source \
    && git -C /source remote add origin https://github.com/IENbolsa2026/ia_api.git \
    && git -C /source fetch --depth 1 origin "$IA_API_COMMIT" \
    && git -C /source checkout --detach FETCH_HEAD \
    && test "$(git -C /source rev-parse HEAD)" = "$IA_API_COMMIT"

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends clamav clamav-freshclam libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=source /source/backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY --from=source --chown=app:app /source/backend/app ./app
COPY --from=source --chown=app:app /source/backend/ien_contracts ./ien_contracts
COPY deploy/ia/start.py ./start.py
COPY deploy/ia/freshclam.conf ./freshclam.conf
COPY deploy/ia/scan-cv /usr/local/bin/scan-cv
RUN chmod 755 /usr/local/bin/scan-cv \
    && mkdir -p /data/clamav /data/cv && chown -R app:app /data
USER app
EXPOSE 8001
CMD ["python", "start.py"]
