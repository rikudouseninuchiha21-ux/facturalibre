# Backend — FacturaLibre

Backend mínimo del MVP: FastAPI, SQLAlchemy, Alembic y PostgreSQL. En esta etapa **solo existe `GET /health`**; no hay lógica de negocio, tablas ni endpoints de facturación.

## Requisitos

- Python 3.12 o superior.
- `uv` instalado.
- Docker y Docker Compose (para la base de datos y el despliegue local).

## Ejecutar con Docker

Desde la raíz del repositorio:

```bash
cp .env.example .env
# Edita .env y cambia POSTGRES_PASSWORD
docker compose up --build
```

El backend queda en `http://127.0.0.1:8000` y la base de datos **no** se expone al host.

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

## Ejecutar solo el backend con uv

Necesitas una instancia de PostgreSQL accesible. La URL se lee de `DATABASE_URL` (en `.env` o en el entorno).

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Si corres fuera de Docker, `DATABASE_URL` debe apuntar a `localhost`, no al servicio `db`. El archivo `.env.example` ya trae ese ejemplo.

## Pruebas

```bash
cd backend
uv sync
uv run pytest
```

La única prueba actual es un smoke test de `GET /health`.

## Calidad

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Estructura

```text
backend/
  app/
    main.py                 # FastAPI + /health
    core/config.py          # variables de entorno con pydantic-settings
    domain/                 # reglas de negocio (vacío por ahora)
    application/            # casos de uso (vacío por ahora)
    infrastructure/         # adaptadores (vacío por ahora)
    api/v1/                 # routers de la API (vacío por ahora)
  tests/                    # smoke test de salud
  Dockerfile
  pyproject.toml
```

## Notas

- No hay `uv.lock` en esta etapa. Al ejecutar `uv sync` se genera; conviene commitearlo para builds reproducibles.
- El `Dockerfile` usa `uv` sin versión fijada todavía; antes de producción se debe fijar versión o digest.
- No se ha creado ninguna migración de Alembic.
