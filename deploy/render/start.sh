#!/bin/sh
set -eu

python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec python -m daphne -b 0.0.0.0 -p "${PORT:-10000}" ientrabajo.asgi:application
