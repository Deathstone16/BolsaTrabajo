"""Un servicio Free: servidor ASGI y despachadores, con cierre coordinado."""

import os
import signal
import subprocess
import sys
import time


def run():
    children = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        # Render Free no tiene preDeployCommand ni consola remota.
        migration_env = os.environ.copy()
        if migration_env.get('DATABASE_URL_UNPOOLED'):
            migration_env['DATABASE_URL'] = migration_env['DATABASE_URL_UNPOOLED']
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'],
                       env=migration_env, check=True)
        subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'ERROR'], check=True)
        if stopping:
            return 0
        commands = [
            [sys.executable, '-m', 'daphne', '-b', '0.0.0.0', '-p', os.environ.get('PORT', '10000'),
             '--proxy-headers', 'ientrabajo.asgi:application'],
            [sys.executable, 'manage.py', 'run_integration_dispatcher', '--kind', 'extraction', '--interval', '5'],
            [sys.executable, 'manage.py', 'run_integration_dispatcher', '--kind', 'match', '--interval', '5'],
        ]
        for command in commands:
            children.append(subprocess.Popen(command))
        while not stopping:
            if any(child.poll() is not None for child in children):
                print('Un proceso terminó; se detiene el servicio para permitir su reinicio.', flush=True)
                return 1
            time.sleep(0.5)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 8
        for child in children:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    sys.exit(run())
