"""Lee la conexión de Neon sin registrar ni modificar sus credenciales."""

from urllib.parse import parse_qs, unquote, urlsplit


def postgres_url_values(value):
    try:
        url = urlsplit(value)
        port = url.port or 5432
    except ValueError:
        raise RuntimeError('DATABASE_URL de PostgreSQL no es válida.') from None
    if url.scheme not in {'postgres', 'postgresql'} or not url.hostname:
        raise RuntimeError('DATABASE_URL debe ser una conexión postgres:// o postgresql://.')
    query = parse_qs(url.query)
    return {
        'DB_NAME': unquote(url.path.lstrip('/')),
        'DB_USER': unquote(url.username or ''),
        'DB_PASSWORD': unquote(url.password or ''),
        'DB_HOST': url.hostname,
        'DB_PORT': str(port),
        'DB_SSLMODE': query.get('sslmode', [''])[0],
        'DB_CHANNEL_BINDING': query.get('channel_binding', [''])[0],
    }
