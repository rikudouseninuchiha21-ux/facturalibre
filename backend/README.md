# Backend — FacturaLibre

Backend del MVP: FastAPI, SQLAlchemy 2, Alembic y PostgreSQL 16. En esta etapa
existe `GET /health`, el esquema de datos inicial y sus migraciones. **Todavía no
hay endpoints de negocio ni lógica de facturación.**

## Requisitos

- Python 3.12 o superior.
- `uv` instalado.
- Docker y Docker Compose (para la base de datos y el despliegue local).
- PostgreSQL 16 para ejecutar migraciones y pruebas de esquema.

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

Para aplicar las migraciones dentro del contenedor:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

## Ejecutar solo el backend con uv

Necesitas una instancia de PostgreSQL accesible. La URL se lee de `DATABASE_URL`
(en `.env` o en el entorno). Alembic usa la misma variable; no hay credenciales
hardcodeadas en `alembic.ini`.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Si corres fuera de Docker, `DATABASE_URL` debe apuntar a `localhost`, no al
servicio `db`. El archivo `.env.example` ya trae ese ejemplo.

## Migraciones

Ejecuta siempre desde `backend/`:

```bash
cd backend
uv run alembic upgrade head          # aplica todas las migraciones pendientes
uv run alembic current               # muestra la revisión aplicada
uv run alembic history --verbose     # historial de revisiones
```

Para crear una migración nueva después de cambiar los modelos:

```bash
uv run alembic revision --autogenerate -m "descripcion breve"
```

Revisa siempre el archivo generado antes de aplicarlo. Para revertir:

```bash
uv run alembic downgrade -1          # revierte la última migración
uv run alembic downgrade base        # vuelve a un esquema vacío
uv run alembic upgrade head          # vuelve a aplicar todo
```

La migración inicial crea las tablas `contacts`, `items`, `taxes`, `invoices`,
`invoice_lines`, `payments`, `number_sequences` e `idempotency_keys`, además de
los tipos ENUM de estado de factura.

### Base de datos de test

`tests/test_schema.py` requiere una base PostgreSQL real y **separada** de la de
desarrollo. La variable `TEST_DATABASE_URL` no se lee de `.env`: se pasa por el
entorno. Un ejemplo con un contenedor temporal, sin tocar `docker-compose.yml`:

```bash
docker run --rm -d --name facturalibre-test-db \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=facturalibre_test \
  -p 127.0.0.1:55432:5432 \
  postgres:16-alpine

cd backend
export TEST_DATABASE_URL=postgresql+psycopg://test:test@127.0.0.1:55432/facturalibre_test
export DATABASE_URL="$TEST_DATABASE_URL"
uv run alembic upgrade head
uv run pytest
uv run pytest tests/test_schema.py

docker stop facturalibre-test-db
```

Si `TEST_DATABASE_URL` no está definida, las pruebas de esquema se omiten. Las
pruebas de `/health` no necesitan base de datos.

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
  alembic.ini                  # configuración de Alembic; la URL viene de DATABASE_URL
  app/
    main.py                    # FastAPI + /health
    core/config.py             # variables de entorno con pydantic-settings
    domain/models/             # Contact, Item, Tax, Invoice, InvoiceLine, Payment,
                               # NumberSequence e IdempotencyKey
    application/               # casos de uso (vacío por ahora)
    infrastructure/
      database.py              # engine, SessionLocal, Base y get_db()
      migrations/              # env.py, plantilla y versiones de Alembic
    api/v1/                    # routers de la API (vacío por ahora)
  tests/
    test_health.py             # smoke test de /health
    test_schema.py             # tablas, estados y tipos NUMERIC contra PostgreSQL
  Dockerfile
  pyproject.toml
```

## Notas

- No hay `uv.lock` en esta etapa. Al ejecutar `uv sync` se genera; conviene
  commitearlo para builds reproducibles.
- El `Dockerfile` usa `uv` sin versión fijada todavía; antes de producción se
  debe fijar versión o digest.
- Las migraciones no se ejecutan automáticamente al arrancar el contenedor:
  se aplican explícitamente con `alembic upgrade head`.
- El esquema es de una sola instancia/tenant en esta fase. La multi-tenencia y
  la emisión electrónica DIAN (CUFE/CUDE/firma) quedan fuera de este paso.
