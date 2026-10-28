"""Sincroniza secretos de servicio locales sin imprimirlos ni tocar claves de proveedor."""
from pathlib import Path
import secrets
import sys
from dotenv import dotenv_values, set_key


PROVIDER_KEYS = {
    'groq': 'GROQ_API_KEY',
    'gemini': 'GEMINI_API_KEY',
    'openai': 'OPENAI_API_KEY',
}


def resolve_provider_model(api_values):
    """Return the CV extraction provider and model without changing config."""
    provider = (api_values.get('LLM_PROVIDER') or 'groq').strip().lower()
    if provider not in PROVIDER_KEYS:
        raise ValueError(f'LLM_PROVIDER no soportado: {provider!r}')

    if provider == 'gemini':
        model = api_values.get('GEMINI_MODEL') or 'gemini-3.5-flash-lite'
    elif provider == 'openai':
        model = api_values.get('OPENAI_MODEL') or 'gpt-4o-mini'
    else:
        model = (
            api_values.get('MATCH_GROQ_MODEL')
            or api_values.get('CV_MODEL')
            or 'llama-3.3-70b-versatile'
        )
    return provider, model


def resolve_match_provider_model(api_values):
    """Keep match routing independent from the CV extraction provider."""
    provider = (api_values.get('MATCH_PROVIDER') or 'groq').strip().lower()
    if provider not in {'groq', 'gemini'}:
        raise ValueError(f'MATCH_PROVIDER no soportado: {provider!r}')
    if provider == 'gemini':
        return provider, api_values.get('GEMINI_MODEL') or 'gemini-3.5-flash-lite'
    return provider, api_values.get('MATCH_GROQ_MODEL') or api_values.get('CV_MODEL') or 'qwen/qwen3.8-27b'


def api_env_updates(provider, model, service, hmac):
    """Build API env updates while preserving provider and unrelated model settings."""
    updates = {
        'SERVICE_API_TOKEN': service,
        'CV_RESULT_CALLBACK_HMAC_SECRET': hmac,
        'CV_RESULT_CALLBACK_URL': 'http://127.0.0.1:8000/ia/llegue/',
        'CHANNEL_REDIS_URL': 'redis://127.0.0.1:6379/3',
    }
    return updates


def update(path, values):
    path.touch(exist_ok=True)
    for key, value in values.items():
        set_key(str(path), key, str(value))


def main():
    root = Path(__file__).resolve().parents[3]
    bolsa = Path(__file__).resolve().parents[1]
    api_candidates = (root / 'api' / 'ia_api' / 'backend', root / 'ia_api' / 'backend')
    api = next((candidate for candidate in api_candidates if (candidate / 'app').is_dir()), None)
    if api is None:
        raise FileNotFoundError('No se encontró el backend de ia_api junto al proyecto.')

    django_env = bolsa / '.env'
    values = dotenv_values(django_env)
    service = values.get('IA_API_TOKEN') or secrets.token_urlsafe(48)
    hmac = values.get('IA_CALLBACK_HMAC_SECRET') or values.get('IA_CALLBACK_TOKEN') or secrets.token_urlsafe(48)
    api_values = dotenv_values(api / '.env')
    provider, model = resolve_provider_model(api_values)
    match_provider, match_model = resolve_match_provider_model(api_values)
    provider_key_configured = bool(api_values.get(PROVIDER_KEYS[provider]))

    update(django_env, {
        'DEBUG': values.get('DEBUG') or 'true',
        'ALLOWED_HOSTS': values.get('ALLOWED_HOSTS') or '127.0.0.1,localhost',
        'IA_API_URL': 'http://127.0.0.1:8001/api/v1/cv-analyses',
        'IA_OFFER_API_URL': 'http://127.0.0.1:8001/api/v1/offer-analyses',
        'IA_API_TOKEN': service, 'IA_CALLBACK_HMAC_SECRET': hmac,
        'MATCH_API_TOKEN': service, 'CHANNEL_REDIS_URL': 'redis://127.0.0.1:6379/3',
        'MATCH_API_URL': 'ws://127.0.0.1:8001/api/v1/ws/v1/matches',
        'MATCH_API_HTTP_URL': 'http://127.0.0.1:8001/api/v1',
        'MATCH_MODEL_VERSION': f'{match_provider}:{match_model}:strict-low' if match_provider == 'groq' else f'{match_provider}:{match_model}',
    })
    updates = api_env_updates(provider, model, service, hmac)
    update(api / '.env', updates)
    print(f'API única en 8001 configurada. CV={provider}; match={match_provider}; clave CV configurada={provider_key_configured}')


if __name__ == '__main__':
    main()
