# Backend — FacturaLibre

Backend del MVP: FastAPI, SQLAlchemy 2, Alembic y PostgreSQL 16. En esta etapa
existe `GET /health`, el esquema de datos inicial y los CRUD de catálogos maestros
(`contacts`, `items`, `taxes`). **Todavía no hay facturas, pagos ni numeración.**

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

## Endpoints de catálogos

Base local: `http://127.0.0.1:8000/api/v1`.

Los listados aceptan `?limit=20&offset=0`; `limit` debe estar entre 1 y 100. Las
respuestas de listado son un arreglo JSON. Los `DELETE` son *soft delete*: la fila
permanece en la base con `deleted_at`, pero deja de aparecer y responde `404`.
Las actualizaciones usan `PATCH` y requieren la `version` actual; si no coincide,
responden `409`. Los errores de validación responden `422`. En los ejemplos,
reemplaza `$CONTACT_ID`, `$ITEM_ID` y `$TAX_ID` por los ids devueltos al crear.

### Contactos

```bash
BASE=http://127.0.0.1:8000/api/v1

# Crear
curl -s -X POST "$BASE/contacts" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Cliente Uno","email":"cliente1@example.com","tax_id":"900123456"}'

# Listar con paginación
curl -s "$BASE/contacts?limit=20&offset=0"

# Obtener uno (reemplaza CONTACT_ID por el id devuelto al crear)
curl -s "$BASE/contacts/$CONTACT_ID"

# Actualizar; version debe ser la versión actual
curl -s -X PATCH "$BASE/contacts/$CONTACT_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Cliente Actualizado","version":1}'

# Soft delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/contacts/$CONTACT_ID"
```

### Ítems

```bash
# Crear; tax_id es opcional. Usa el id de un impuesto si quieres asociarlo.
curl -s -X POST "$BASE/items" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Producto Uno","description":"Producto de prueba","unit_price":"1250.50","tax_id":null}'

# Listar
curl -s "$BASE/items?limit=20&offset=0"

# Obtener
curl -s "$BASE/items/$ITEM_ID"

# Actualizar
curl -s -X PATCH "$BASE/items/$ITEM_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Producto Actualizado","unit_price":"999.99","version":1}'

# Soft delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/items/$ITEM_ID"
```

### Impuestos

```bash
# Crear; rate es un porcentaje entre 0 y 100 con hasta 4 decimales
curl -s -X POST "$BASE/taxes" \
  -H 'Content-Type: application/json' \
  -d '{"name":"IVA 19 %","rate":"19.0000"}'

# Listar
curl -s "$BASE/taxes?limit=20&offset=0"

# Obtener
curl -s "$BASE/taxes/$TAX_ID"

# Actualizar
curl -s -X PATCH "$BASE/taxes/$TAX_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"IVA actualizado","rate":"19.5000","version":1}'

# Soft delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/taxes/$TAX_ID"
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

`tests/test_schema.py` y los tests CRUD requieren una base PostgreSQL real y
**separada** de la de desarrollo. La variable `TEST_DATABASE_URL` no se lee de
`.env`: se pasa por el entorno. Un ejemplo con un contenedor temporal, sin tocar
`docker-compose.yml`:

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

Si `TEST_DATABASE_URL` no está definida, las pruebas que necesitan PostgreSQL se
omiten. Las pruebas de `/health` no necesitan base de datos. Cada test CRUD corre
en una transacción externa que se revierte al terminar, sin dejar datos de prueba.

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
    domain/
      models/                  # Contact, Item, Tax, Invoice, InvoiceLine, Payment,
                               # NumberSequence e IdempotencyKey
      *_repository.py           # consultas y updates con SQLAlchemy 2
      exceptions.py            # errores de recurso ausente y versión obsoleta
    application/
      *_schemas.py             # schemas Pydantic v2 de contactos, ítems e impuestos
    infrastructure/
      database.py              # engine, SessionLocal, Base y get_db()
      migrations/              # env.py, plantilla y versiones de Alembic
    api/v1/
      contacts.py              # CRUD de contactos
      items.py                 # CRUD de ítems
      taxes.py                 # CRUD de impuestos
  tests/
    conftest.py                # PostgreSQL de test y sesión transaccional
    test_health.py             # smoke test de /health
    test_schema.py             # tablas, estados y tipos NUMERIC contra PostgreSQL
    test_contacts.py           # CRUD y optimistic locking de contactos
    test_items.py              # CRUD y optimistic locking de ítems
    test_taxes.py              # CRUD y optimistic locking de impuestos
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
