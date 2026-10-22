#!/bin/sh
set -eu

# Espera a que el servidor PostgreSQL acepte conexiones TCP. Se usa un socket de
# Python para no depender de psql/pg_isready, que no están en la imagen runtime.
/app/.venv/bin/python - <<'PY'
import os
import socket
import sys
import time
from urllib.parse import urlparse

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    sys.exit("ERROR: DATABASE_URL no está definida")

parsed = urlparse(database_url)
host = parsed.hostname
port = parsed.port or 5432
if not host:
    sys.exit("ERROR: DATABASE_URL no contiene un host válido")

deadline = time.monotonic() + 30
while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"Postgres disponible en {host}:{port}", flush=True)
            break
    except OSError as exc:
        if time.monotonic() >= deadline:
            sys.exit(
                f"ERROR: Postgres no aceptó conexiones en 30s "
                f"({host}:{port}): {exc}"
            )
        print(f"Esperando Postgres en {host}:{port}...", flush=True)
        time.sleep(1)
PY

echo "Aplicando migraciones Alembic..."
/app/.venv/bin/alembic upgrade head
echo "Migraciones aplicadas. Iniciando la aplicación..."
exec "$@"
