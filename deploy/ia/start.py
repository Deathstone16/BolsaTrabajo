"""Antivirus actualizado antes de aceptar archivos; API y worker supervisados."""

import os
import signal
import subprocess
import sys
import time


def run():
    required = ('SERVICE_API_TOKEN', 'CV_RESULT_CALLBACK_URL', 'CV_RESULT_CALLBACK_HMAC_SECRET', 'GROQ_API_KEY')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError('Faltan variables de la IA: ' + ', '.join(missing))
    subprocess.run(['freshclam', '--config-file=/app/freshclam.conf'], check=True)
    children = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        for command in (
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8001'],
            [sys.executable, '-m', 'celery', '-A', 'app.core.celery_app:celery_app', 'worker',
             '--pool=solo', '--concurrency=1', '--loglevel=INFO'],
        ):
            children.append(subprocess.Popen(command))
        while not stopping:
            if any(child.poll() is not None for child in children):
                return 1
            time.sleep(0.5)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 15
        for child in children:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    sys.exit(run())
