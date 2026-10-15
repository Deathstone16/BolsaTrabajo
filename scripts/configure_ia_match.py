"""Sincroniza secretos de servicio locales sin imprimirlos ni tocar claves de proveedor."""
from pathlib import Path
import secrets
from dotenv import dotenv_values, set_key

root = Path(__file__).resolve().parents[3]
bolsa = Path(__file__).resolve().parents[1]
api = root / 'api' / 'ia_api' / 'backend'


def update(path, values):
    path.touch(exist_ok=True)
    for key, value in values.items():
        set_key(str(path), key, str(value))


django_env = bolsa / '.env'
values = dotenv_values(django_env)
service = values.get('IA_API_TOKEN') or secrets.token_urlsafe(48)
hmac = values.get('IA_CALLBACK_HMAC_SECRET') or values.get('IA_CALLBACK_TOKEN') or secrets.token_urlsafe(48)
api_values = dotenv_values(api / '.env')
model = api_values.get('MATCH_GROQ_MODEL') or api_values.get('CV_MODEL') or 'llama-3.3-70b-versatile'
update(django_env, {
    'DEBUG': 'true', 'ALLOWED_HOSTS': '127.0.0.1,localhost',
    'IA_API_URL': 'http://127.0.0.1:8001/api/v1/cv-analyses',
    'IA_OFFER_API_URL': 'http://127.0.0.1:8001/api/v1/offer-analyses',
    'IA_API_TOKEN': service, 'IA_CALLBACK_HMAC_SECRET': hmac,
    'MATCH_API_TOKEN': service, 'CHANNEL_REDIS_URL': 'redis://127.0.0.1:6379/3',
    'MATCH_API_URL': 'ws://127.0.0.1:8001/api/v1/ws/v1/matches',
    'MATCH_API_HTTP_URL': 'http://127.0.0.1:8001/api/v1',
    'MATCH_MODEL_VERSION': f'groq:{model}',
})
update(api / '.env', {
    'LLM_PROVIDER': 'groq',
    'SERVICE_API_TOKEN': service, 'CV_RESULT_CALLBACK_HMAC_SECRET': hmac,
    'CV_RESULT_CALLBACK_URL': 'http://127.0.0.1:8000/ia/llegue/',
    'CHANNEL_REDIS_URL': 'redis://127.0.0.1:6379/3',
    'MATCH_GROQ_MODEL': model,
})
print('API única en 8001 configurada. Groq configurado:', bool(api_values.get('GROQ_API_KEY')))
