"""Valida los .env de la VPS sin imprimir secretos ni modificar datos."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit

def check_config(web: dict, api: dict) -> list[str]:
    errors = []

    def require(values, key, service):
        value = values.get(key) or ''
        if not value or '<' in value or '>' in value:
            errors.append(f'{service}: completar {key}.')
        return value

    if str(web.get('DEBUG', '')).lower() not in {'false', '0', 'no', 'off'}:
        errors.append('Django: DEBUG debe ser false.')
    if api.get('MODE') != 'production':
        errors.append('API: MODE debe ser production.')
    if web.get('DB_ENGINE') != 'postgresql':
        errors.append('Django: usar DB_ENGINE=postgresql.')
    for key in ('SECRET_KEY', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS'):
        require(web, key, 'Django')
    hosts = {host.strip() for host in (web.get('ALLOWED_HOSTS') or '').split(',')}
    if '*' in hosts or '127.0.0.1' not in hosts:
        errors.append('Django: ALLOWED_HOSTS debe incluir 127.0.0.1 y el dominio exacto, sin comodín.')
    for origin in (web.get('CSRF_TRUSTED_ORIGINS') or '').split(','):
        parsed = urlsplit(origin.strip())
        if parsed.scheme != 'https' or parsed.hostname not in hosts:
            errors.append('Django: cada origen CSRF debe usar HTTPS y un host permitido.')
    if web.get('DB_HOST', '').startswith('/'):
        if web.get('DB_SSLMODE') != 'disable':
            errors.append('Django: para socket Unix usar DB_SSLMODE=disable.')
    elif web.get('DB_SSLMODE') not in {'require', 'verify-ca', 'verify-full'}:
        errors.append('Django: configurar DB_SSLMODE con TLS para PostgreSQL TCP.')
    for web_key, api_key in (('IA_API_TOKEN', 'SERVICE_API_TOKEN'), ('MATCH_API_TOKEN', 'SERVICE_API_TOKEN'), ('IA_CALLBACK_HMAC_SECRET', 'CV_RESULT_CALLBACK_HMAC_SECRET')):
        left = require(web, web_key, 'Django')
        right = require(api, api_key, 'API')
        if left and right and left != right:
            errors.append(f'No coinciden {web_key} y {api_key}.')
    if web.get('CHANNEL_REDIS_URL') != api.get('CHANNEL_REDIS_URL') or not web.get('CHANNEL_REDIS_URL'):
        errors.append('Los dos servicios deben compartir CHANNEL_REDIS_URL.')
    expected = {
        'IA_API_URL': 'http://127.0.0.1:8001/api/v1/cv-analyses',
        'IA_OFFER_API_URL': 'http://127.0.0.1:8001/api/v1/offer-analyses',
        'MATCH_API_URL': 'ws://127.0.0.1:8001/api/v1/ws/v1/matches',
        'MATCH_API_HTTP_URL': 'http://127.0.0.1:8001/api/v1',
    }
    for key, value in expected.items():
        if web.get(key) != value:
            errors.append(f'Django: {key} no coincide con los puertos de deploy/systemd.')
    if api.get('CV_RESULT_CALLBACK_URL') != 'http://127.0.0.1:8080/ia/llegue/':
        errors.append('API: el callback debe apuntar a http://127.0.0.1:8080/ia/llegue/.')
    for flag in ('TRUST_PROXY_HEADERS', 'SECURE_SSL_REDIRECT'):
        if str(web.get(flag, '')).lower() not in {'true', '1', 'yes', 'on'}:
            errors.append(f'Django: activar {flag} detrás de Caddy.')
    provider_keys = {'groq': 'GROQ_API_KEY', 'gemini': 'GEMINI_API_KEY', 'openai': 'OPENAI_API_KEY'}
    for provider in ('LLM_PROVIDER', 'MATCH_PROVIDER'):
        name = api.get(provider, 'groq')
        if name not in provider_keys or (provider == 'MATCH_PROVIDER' and name == 'openai'):
            errors.append(f'API: proveedor no admitido en {provider}.')
        else:
            require(api, provider_keys[name], 'API')
    if web.get('EMAIL_BACKEND', '').endswith('smtp.EmailBackend'):
        for key in ('EMAIL_HOST', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD'):
            require(web, key, 'SMTP')
    return errors


def main():
    from dotenv import dotenv_values

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--django-root', type=Path, default=Path('/srv/ien/BolsaTrabajo'))
    parser.add_argument('--api-root', type=Path, default=Path('/srv/ien/ia_api/backend'))
    args = parser.parse_args()
    paths = [args.django_root / '.env', args.api_root / '.env']
    if not all(path.is_file() for path in paths):
        raise SystemExit('Faltan los archivos .env de Django o de la API.')
    errors = check_config(*(dotenv_values(path, interpolate=False) for path in paths))
    if errors:
        for error in errors:
            print(f'ERROR: {error}')
        raise SystemExit(1)
    print('Configuración consistente. Verificar después BD, migraciones, servicios, SMTP y acceso público en la VPS.')


if __name__ == '__main__':
    main()
